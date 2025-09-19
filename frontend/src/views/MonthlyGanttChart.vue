<template>
  <div class="monthly-gantt-chart-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><TrendCharts /></el-icon>
        月度排产甘特图
      </h1>
      <div class="header-actions">
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 筛选器 -->
    <div class="filter-bar">
      <el-form :inline="true" :model="filterOptions">
        <el-form-item label="排产任务ID">
          <el-input
            v-model="filterOptions.task_id"
            placeholder="输入任务ID"
            clearable
            style="width: 200px"
            @change="fetchMonthlyWorkOrders"
          />
        </el-form-item>
        <el-form-item label="机台">
          <el-select
            v-model="filterOptions.machine_code"
            placeholder="选择机台"
            clearable
            filterable
            style="width: 180px"
            @change="fetchMonthlyWorkOrders"
          >
            <el-option label="全部" value="" />
            <el-option
              v-for="machine in machineOptions"
              :key="machine.machine_code"
              :label="`${machine.machine_code} - ${machine.machine_name}`"
              :value="machine.machine_code"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 统计信息 -->
    <div class="statistics-bar" v-if="!loading && workOrders.length > 0">
      <div class="stat-item">
        <el-icon><Box /></el-icon>
        <span>总工单数: {{ workOrders.length }}</span>
      </div>
      <div class="stat-item">
        <el-icon><Timer /></el-icon>
        <span>机台数: {{ uniqueMachineCount }}</span>
      </div>
      <div class="stat-item">
        <el-icon><CircleCheck /></el-icon>
        <span>时间范围: {{ timeRangeText }}</span>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <div class="gantt-container">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="error" class="error-state">
          <el-alert :title="error" type="error" show-icon />
        </div>

        <!-- 无数据状态 -->
        <div v-else-if="workOrders.length === 0" class="empty-state">
          <el-empty description="暂无月度排产工单数据" />
        </div>

        <!-- 自定义甘特图布局：左侧机台 + 右侧甘特图 -->
        <div v-else class="custom-gantt-layout">
          <!-- 左侧机台标签列 -->
          <div class="machine-labels-column">
            <div class="machine-labels-header">机台</div>
            <div 
              v-for="(row, index) in ganttRows" 
              :key="row.machine"
              class="machine-label-item"
            >
              {{ row.machine }}
            </div>
          </div>
          
          <!-- 右侧甘特图区域 -->
          <div class="gantt-chart-area">
            <g-gantt-chart
              :chart-start="chartTimeRange.start"
              :chart-end="chartTimeRange.end"
              precision="day"
              :width="'100%'"
              :height="chartHeight"
              bar-start="startTime"
              bar-end="endTime"
              date-format="YYYY-MM-DD HH:mm"
              color-scheme="default"
              :push-on-overlap="false"
              :grid="true"
              :row-height="60"
              :row-label-width="0"
              font="Inter, sans-serif"
              @click-bar="onBarClick"
              @mouseenter-bar="onBarMouseenter"
              @mouseleave-bar="onBarMouseleave"
            >
              <g-gantt-row
                v-for="(row, index) in ganttRows"
                :key="row.machine"
                label=""
                :bars="row.bars"
                :highlight-on-hover="true"
              >
                <!-- 自定义条形标签 -->
                <template #bar-label="{ bar }">
                  <div class="bar-label">
                    <span class="bar-product">{{ bar.product }}</span>
                    <span class="bar-quantity">{{ bar.quantity }}箱</span>
                  </div>
                </template>
              </g-gantt-row>
            </g-gantt-chart>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Loading, Clock, Timer, CircleCheck, Box, TrendCharts } from '@element-plus/icons-vue'
import { MonthlyWorkOrderAPI, MachineConfigAPI } from '@/services/api'
import type { MonthlyWorkOrder } from '@/services/api'

// 路由信息
const route = useRoute()

// 响应式数据
const loading = ref(false)
const error = ref<string | null>(null)
const workOrders = ref<MonthlyWorkOrder[]>([])
const machineOptions = ref<Array<{ machine_code: string; machine_name: string }>>([])

// 筛选条件
const filterOptions = ref({
  task_id: '',
  machine_code: ''
})

// 计算属性
const uniqueMachineCount = computed(() => {
  const machines = new Set(workOrders.value.map(order => order.machine_code || 'UNKNOWN'))
  return machines.size
})

const timeRangeText = computed(() => {
  if (workOrders.value.length === 0) return '无数据'
  
  const times = workOrders.value
    .filter(order => order.planned_start_time && order.planned_end_time)
    .map(order => ({
      start: new Date(order.planned_start_time!),
      end: new Date(order.planned_end_time!)
    }))
  
  if (times.length === 0) return '无时间数据'
  
  const minStart = new Date(Math.min(...times.map(t => t.start.getTime())))
  const maxEnd = new Date(Math.max(...times.map(t => t.end.getTime())))
  
  return `${formatDate(minStart)} ~ ${formatDate(maxEnd)}`
})

const chartTimeRange = computed(() => {
  if (workOrders.value.length === 0) {
    const now = new Date()
    return {
      start: formatDateTime(now),
      end: formatDateTime(new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000))
    }
  }

  const times = workOrders.value
    .filter(order => order.planned_start_time && order.planned_end_time)
    .map(order => ({
      start: new Date(order.planned_start_time!),
      end: new Date(order.planned_end_time!)
    }))

  if (times.length === 0) {
    const now = new Date()
    return {
      start: formatDateTime(now),
      end: formatDateTime(new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000))
    }
  }

  const minStart = new Date(Math.min(...times.map(t => t.start.getTime())))
  const maxEnd = new Date(Math.max(...times.map(t => t.end.getTime())))

  // 前后各加一天的缓冲
  const bufferStart = new Date(minStart.getTime() - 24 * 60 * 60 * 1000)
  const bufferEnd = new Date(maxEnd.getTime() + 24 * 60 * 60 * 1000)

  return {
    start: formatDateTime(bufferStart),
    end: formatDateTime(bufferEnd)
  }
})

const chartHeight = computed(() => {
  return Math.max(400, ganttRows.value.length * 60) + 'px'
})

// 转换月度工单数据为甘特图行数据
const ganttRows = computed(() => {
  if (workOrders.value.length === 0) return []

  const machineGroups: Record<string, MonthlyWorkOrder[]> = {}

  // 按机台分组
  workOrders.value.forEach(order => {
    let machineKey = ''

    // 构建机台组合名称
    if (order.maker_code && order.feeder_code) {
      machineKey = `${order.maker_code} + ${order.feeder_code}\n(卷包机 + 喂丝机)`
    } else if (order.maker_code) {
      machineKey = `${order.maker_code}\n(卷包机)`
    } else if (order.feeder_code) {
      machineKey = `${order.feeder_code}\n(喂丝机)`
    } else {
      machineKey = order.machine_code || 'UNKNOWN'
    }

    if (!machineGroups[machineKey]) {
      machineGroups[machineKey] = []
    }
    machineGroups[machineKey].push(order)
  })

  // 转换为甘特图行格式
  return Object.entries(machineGroups).map(([machine, orders]) => ({
    machine,
    bars: orders.map(order => {
      // 确保时间格式正确
      const startTime = order.planned_start_time
        ? formatDateTime(new Date(order.planned_start_time))
        : formatDateTime(new Date())
      const endTime = order.planned_end_time
        ? formatDateTime(new Date(order.planned_end_time))
        : formatDateTime(new Date(Date.now() + 8 * 60 * 60 * 1000))

      return {
        startTime,
        endTime,
        ganttBarConfig: {
          id: order.work_order_nr,
          label: `${order.work_order_nr} - ${order.product_code}`,
          style: {
            background: getBarColor(order),
            color: '#ffffff',
            borderRadius: '6px',
            fontSize: '12px',
            border: '1px solid rgba(255,255,255,0.2)',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          },
          hasHandles: false
        },
        // 附加数据用于显示
        workOrder: order.work_order_nr,
        product: order.product_code,
        quantity: order.plan_quantity,
        status: order.work_order_status
      }
    })
  }))
})

// 获取条形颜色
function getBarColor(order: MonthlyWorkOrder): string {
  // 根据工单状态设置颜色
  switch (order.work_order_status) {
    case 'COMPLETED':
      return 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)'
    case 'RUNNING':
      return 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)'
    case 'PENDING':
      return 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)'
    case 'CANCELLED':
      return 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)'
    default:
      return 'linear-gradient(135deg, #d9d9d9 0%, #f0f0f0 100%)'
  }
}

// 工具方法
function formatDateTime(date: Date): string {
  return date.toISOString().slice(0, 19).replace('T', ' ')
}

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

// 事件处理
function onBarClick(bar: any) {
  console.log('点击条形:', bar)
  ElMessage.info(`工单: ${bar.workOrder}`)
}

function onBarMouseenter(bar: any) {
  console.log('悬停条形:', bar)
}

function onBarMouseleave(bar: any) {
  console.log('离开条形:', bar)
}

// 获取机台选项
async function fetchMachineOptions() {
  try {
    const response = await MachineConfigAPI.getMachines()
    if (response.code === 200 && response.data) {
      machineOptions.value = response.data.items || []
    }
  } catch (err) {
    console.error('获取机台选项失败:', err)
  }
}

// 获取月度工单数据
async function fetchMonthlyWorkOrders() {
  loading.value = true
  error.value = null

  try {
    console.log('🔍 获取月度工单数据，查询参数:', filterOptions.value)

    // 检查是否有月度批次ID
    const monthlyBatchId = route.query.monthly_batch_id as string
    if (!monthlyBatchId) {
      error.value = '缺少月度批次ID参数'
      return
    }

    const params: any = {
      monthly_batch_id: monthlyBatchId
    }

    // 添加任务ID参数（如果存在）
    const taskId = route.query.task_id as string
    if (taskId) {
      params.task_id = taskId
      console.log('📋 使用任务ID:', taskId)
    }

    // 添加机台筛选
    if (filterOptions.value.machine_code) {
      params.machine_code = filterOptions.value.machine_code
      console.log('📍 使用机台筛选:', filterOptions.value.machine_code)
    }

    const response = await MonthlyWorkOrderAPI.getMonthlyWorkOrders(params)
    console.log('✅ API响应:', {
      code: response.code,
      message: response.message,
      dataExists: !!response.data
    })

    if (response.code === 200 && response.data) {
      // 后端返回的数据结构包含gantt_data，我们需要从中提取工单数据
      const scheduleData = response.data
      const extractedWorkOrders: MonthlyWorkOrder[] = []

      // 从gantt_data.schedule_blocks中提取工单
      if (scheduleData.gantt_data?.schedule_blocks) {
        scheduleData.gantt_data.schedule_blocks.forEach((workOrder: any) => {
          extractedWorkOrders.push({
            work_order_nr: workOrder.work_order_nr,
            work_order_type: 'HJB', // 月度工单类型
            machine_type: '卷包机',
            machine_code: workOrder.machine_code,
            maker_code: workOrder.machine_code,
            feeder_code: undefined,
            product_code: workOrder.article_name,
            plan_quantity: Math.round(workOrder.duration * 10) || 100, // 根据duration估算产量
            work_order_status: workOrder.status || 'SCHEDULED',
            planned_start_time: workOrder.start_time,
            planned_end_time: workOrder.end_time,
            monthly_batch_id: monthlyBatchId
          })
        })
      }

      workOrders.value = extractedWorkOrders
      console.log('📦 转换后的月度工单数据样本:', workOrders.value.slice(0, 2))
    } else {
      error.value = response.message || '获取月度工单数据失败'
    }
  } catch (err: any) {
    console.error('❌ 获取月度工单数据失败:', err)
    
    // 提供更详细的错误信息
    if (err.response?.status === 404) {
      error.value = '未找到月度排产结果，请先执行月度排产'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = '获取月度工单数据失败'
    }
  } finally {
    loading.value = false
  }
}

// 刷新数据
async function refreshData() {
  await Promise.all([
    fetchMachineOptions(),
    fetchMonthlyWorkOrders()
  ])

  // 数据刷新后更新中文日期
  updateChineseDates()
}

// 处理中文日期显示
function updateChineseDates() {
  setTimeout(() => {
    // 查找并替换月份 - 使用正确的Vue Ganttastic类名
    const monthElements = document.querySelectorAll('.g-upper-timeunit')
    monthElements.forEach(el => {
      let text = el.textContent
      if (text?.includes('October')) {
        text = text.replace('October', '十月')
      } else if (text?.includes('November')) {
        text = text.replace('November', '十一月')
      } else if (text?.includes('December')) {
        text = text.replace('December', '十二月')
      } else if (text?.includes('September')) {
        text = text.replace('September', '九月')
      } else if (text?.includes('January')) {
        text = text.replace('January', '一月')
      } else if (text?.includes('February')) {
        text = text.replace('February', '二月')
      } else if (text?.includes('March')) {
        text = text.replace('March', '三月')
      } else if (text?.includes('April')) {
        text = text.replace('April', '四月')
      } else if (text?.includes('May')) {
        text = text.replace('May', '五月')
      } else if (text?.includes('June')) {
        text = text.replace('June', '六月')
      } else if (text?.includes('July')) {
        text = text.replace('July', '七月')
      } else if (text?.includes('August')) {
        text = text.replace('August', '八月')
      }
      if (el.textContent !== text) {
        el.textContent = text
      }
    })

    // 查找并替换日期
    const dayElements = document.querySelectorAll('.g-timeunit')
    dayElements.forEach(el => {
      const text = el.textContent
      if (text?.includes('.Oct')) {
        el.textContent = text.replace('.Oct', '日')
      } else if (text?.includes('.Nov')) {
        el.textContent = text.replace('.Nov', '日')
      } else if (text?.includes('.Dec')) {
        el.textContent = text.replace('.Dec', '日')
      } else if (text?.includes('.Sep')) {
        el.textContent = text.replace('.Sep', '日')
      } else if (text?.includes('.Jan')) {
        el.textContent = text.replace('.Jan', '日')
      } else if (text?.includes('.Feb')) {
        el.textContent = text.replace('.Feb', '日')
      } else if (text?.includes('.Mar')) {
        el.textContent = text.replace('.Mar', '日')
      } else if (text?.includes('.Apr')) {
        el.textContent = text.replace('.Apr', '日')
      } else if (text?.includes('.May')) {
        el.textContent = text.replace('.May', '日')
      } else if (text?.includes('.Jun')) {
        el.textContent = text.replace('.Jun', '日')
      } else if (text?.includes('.Jul')) {
        el.textContent = text.replace('.Jul', '日')
      } else if (text?.includes('.Aug')) {
        el.textContent = text.replace('.Aug', '日')
      }
    })
  }, 1500) // 增加延迟确保Vue Ganttastic渲染完成
}

// 初始化
onMounted(async () => {
  console.log('📊 月度甘特图页面已挂载')
  console.log('🔍 路由查询参数:', route.query)

  // 从路由获取任务ID
  if (route.query.task_id) {
    filterOptions.value.task_id = route.query.task_id as string
  }

  await refreshData()

  // 更新中文日期显示
  updateChineseDates()
})

// 监听筛选条件变化
watch(() => filterOptions.value, (newFilters) => {
  console.log('📝 筛选条件变化:', newFilters)
}, { deep: true })
</script>

<style scoped>
.monthly-gantt-chart-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-bottom: 1px solid #e8eaed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8eaed;
}

.statistics-bar {
  display: flex;
  gap: 24px;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8eaed;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow: hidden;
}

.gantt-container {
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.loading-state,
.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  gap: 16px;
}

.custom-gantt-layout {
  display: flex;
  height: 100%;
}

.machine-labels-column {
  width: 200px;
  border-right: 1px solid #e8eaed;
  background: #f8f9fa;
  flex-shrink: 0;
}

.machine-labels-header {
  padding: 12px 16px;
  font-weight: 600;
  background: #e9ecef;
  border-bottom: 1px solid #e8eaed;
  text-align: center;
}

.machine-label-item {
  height: 60px;
  padding: 8px 16px;
  border-bottom: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #495057;
  white-space: pre-line;
  line-height: 1.3;
}

.gantt-chart-area {
  flex: 1;
  overflow: auto;
}

.bar-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  padding: 2px 6px;
}

.bar-product {
  font-weight: 600;
}

.bar-quantity {
  opacity: 0.9;
}

/* Vue Ganttastic 样式覆盖 */
:deep(.g-gantt-chart) {
  font-family: Inter, sans-serif;
}

:deep(.g-upper-timeunit) {
  font-weight: 600;
  font-size: 13px;
}

:deep(.g-timeunit) {
  font-size: 12px;
}

:deep(.g-gantt-row-bars-container) {
  border-bottom: 1px solid #e8eaed;
}

:deep(.g-gantt-bar) {
  transition: all 0.2s ease;
}

:deep(.g-gantt-bar:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}
</style>
