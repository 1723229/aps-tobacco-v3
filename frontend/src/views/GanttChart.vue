<template>
  <div class="gantt-chart-page">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <h1>生产甘特图</h1>
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
        <el-form-item label="任务ID">
          <el-input
            v-model="filterOptions.task_id"
            placeholder="输入任务ID"
            clearable
            @change="fetchWorkOrders"
          />
        </el-form-item>
        <el-form-item label="机台">
          <el-select
            v-model="filterOptions.machine_code"
            placeholder="选择机台"
            clearable
            filterable
            style="width: 180px"
            @change="fetchWorkOrders"
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
      <div class="statistics-cards">
        <!-- 工单数 -->
        <div class="stat-card completed">
          <div class="card-header">
            <div class="icon-container">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-content">
              <div class="stat-value">{{ workOrders.length }}</div>
              <div class="stat-label">工单数</div>
            </div>
          </div>
        </div>

        <!-- 总计划产量 -->
        <div class="stat-card total">
          <div class="card-header">
            <div class="icon-container">
              <el-icon><Box /></el-icon>
            </div>
            <div class="card-content">
              <div class="stat-value">{{ formattedTotalQuantity }}</div>
              <div class="stat-label">总计划产量（箱）</div>
            </div>
          </div>
        </div>
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
          <el-empty description="暂无工单数据" />
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
import { Refresh, Loading, Clock, Timer, CircleCheck, Box } from '@element-plus/icons-vue'
import { WorkOrderAPI, MachineConfigAPI } from '@/services/api'
import type { WorkOrder } from '@/services/api'

// 路由信息
const route = useRoute()

// 响应式数据
const loading = ref(false)
const error = ref<string | null>(null)
const workOrders = ref<WorkOrder[]>([])
const machineOptions = ref<Array<{ machine_code: string; machine_name: string }>>([])

// 筛选条件
const filterOptions = ref({
  task_id: '',
  machine_code: ''
})

// 甘特图配置
const chartHeight = ref(600)

// 计算属性
const totalQuantity = computed(() => {
  return workOrders.value.reduce((sum, order) => sum + (order.plan_quantity || 0), 0)
})

// 格式化总数量显示
const formattedTotalQuantity = computed(() => {
  const total = totalQuantity.value
  if (total >= 10000) {
    return (total / 10000).toFixed(1) + '万'
  } else if (total >= 1000) {
    return (total / 1000).toFixed(1) + '千'
  }
  return total.toLocaleString()
})

// 格式化日期为 YYYY-MM-DD HH:mm 格式
function formatDateTime(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

// 格式化中文日期显示
function formatChineseDate(date: Date): string {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  return `${year}年${month}月${day}日`
}

// 计算时间范围
const chartTimeRange = computed(() => {
  if (workOrders.value.length === 0) {
    const now = new Date()
    return {
      start: formatDateTime(new Date(now.getTime() - 24 * 60 * 60 * 1000)),
      end: formatDateTime(new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000))
    }
  }

  const startTimes = workOrders.value
    .map(order => order.planned_start_time)
    .filter(Boolean)
    .map(time => new Date(time!))

  const endTimes = workOrders.value
    .map(order => order.planned_end_time)
    .filter(Boolean)
    .map(time => new Date(time!))

  const minTime = startTimes.length > 0 ? new Date(Math.min(...startTimes.map(d => d.getTime()))) : new Date()
  const maxTime = endTimes.length > 0 ? new Date(Math.max(...endTimes.map(d => d.getTime()))) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)

  // 添加缓冲时间
  const bufferHours = 12
  const chartStart = new Date(minTime.getTime() - bufferHours * 60 * 60 * 1000)
  const chartEnd = new Date(maxTime.getTime() + bufferHours * 60 * 60 * 1000)

  return {
    start: formatDateTime(chartStart),
    end: formatDateTime(chartEnd)
  }
})

// 转换工单数据为甘特图行数据
const ganttRows = computed(() => {
  if (workOrders.value.length === 0) return []

  const machineGroups: Record<string, WorkOrder[]> = {}

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
function getBarColor(order: WorkOrder): string {
  const status = order.work_order_status || 'PLANNED'

  // 基于产品类型的渐变色
  const productType = order.product_code

  if (productType?.includes('利群(软蓝)')) {
    return 'linear-gradient(135deg, #409eff, #337ecc)' // 蓝色渐变
  } else if (productType?.includes('利群(新版)')) {
    return 'linear-gradient(135deg, #67c23a, #529b2e)' // 绿色渐变
  } else if (productType?.includes('利群(硬)')) {
    return 'linear-gradient(135deg, #e6a23c, #b88230)' // 橙色渐变
  } else if (productType?.includes('利群(长嘴)')) {
    return 'linear-gradient(135deg, #f56c6c, #c45656)' // 红色渐变
  } else if (productType?.includes('利群(阳光)')) {
    return 'linear-gradient(135deg, #ffba00, #cc9500)' // 金色渐变
  } else if (productType?.includes('利群(西子阳光)')) {
    return 'linear-gradient(135deg, #ff8c00, #cc7000)' // 橙红渐变
  } else if (productType?.includes('休闲细支')) {
    return 'linear-gradient(135deg, #9c27b0, #7b1fa2)' // 紫色渐变
  } else if (productType?.includes('利群(西湖恋)')) {
    return 'linear-gradient(135deg, #00bcd4, #0097a7)' // 青色渐变
  } else if (productType?.includes('利群(江南韵)')) {
    return 'linear-gradient(135deg, #4caf50, #388e3c)' // 深绿渐变
  } else {
    // 基于状态的颜色
    switch (status) {
      case 'COMPLETED':
        return 'linear-gradient(135deg, #67c23a, #529b2e)' // 绿色渐变
      case 'IN_PROGRESS':
        return 'linear-gradient(135deg, #409eff, #337ecc)' // 蓝色渐变
      case 'PLANNED':
        return 'linear-gradient(135deg, #e6a23c, #b88230)' // 橙色渐变
      case 'PAUSED':
        return 'linear-gradient(135deg, #f56c6c, #c45656)' // 红色渐变
      default:
        return 'linear-gradient(135deg, #909399, #73767a)' // 灰色渐变
    }
  }
}

// 事件处理
function onBarClick(event: any) {
  const bar = event.bar
  ElMessage.info(`工单详情: ${bar.workOrder} - ${bar.product} (${bar.quantity}箱)`)
}

function onBarMouseenter(event: any) {
  // 可以添加鼠标悬停效果
}

function onBarMouseleave(event: any) {
  // 可以添加鼠标离开效果
}

// 获取机台列表
async function fetchMachineOptions() {
  try {
    console.log('🔍 获取机台列表...')

    let allMachines: Array<{ machine_code: string; machine_name: string }> = []
    let page = 1
    const pageSize = 100

    while (true) {
      const response = await MachineConfigAPI.getMachines({ page, page_size: pageSize })
      console.log(`📄 第${page}页API响应:`, {
        dataExists: !!response.data,
        itemsExists: !!response.data?.items,
        itemsLength: response.data?.items?.length
      })

      if (response.data?.items) {
        const machines = response.data.items.map((machine: any) => ({
          machine_code: machine.machine_code,
          machine_name: machine.machine_name || machine.machine_code
        }))

        allMachines.push(...machines)

        // 检查是否还有更多数据
        const hasMore = response.data.items.length === pageSize
        if (!hasMore) {
          console.log(`✅ 第${page}页是最后一页，共获取${allMachines.length}台机台`)
          break
        }

        page++
      } else {
        console.error('❌ 获取机台配置失败:', response)
        break
      }
    }

    machineOptions.value = allMachines
    console.log('✅ 机台列表加载完成:', allMachines.length, '台机台')
  } catch (err) {
    console.error('❌ 获取机台列表失败:', err)
    error.value = '获取机台列表失败'
  }
}

// 获取工单数据
async function fetchWorkOrders() {
  loading.value = true
  error.value = null

  try {
    console.log('🔍 获取工单数据，查询参数:', filterOptions.value)

    const params: any = {
      page: 1,
      page_size: 1000
    }

    // 添加任务ID筛选
    if (filterOptions.value.task_id) {
      params.task_id = filterOptions.value.task_id
      console.log('📍 使用任务ID筛选:', filterOptions.value.task_id)
    }

    // 添加机台筛选
    if (filterOptions.value.machine_code) {
      params.machine_code = filterOptions.value.machine_code
      console.log('📍 使用机台筛选:', filterOptions.value.machine_code)
    }

    const response = await WorkOrderAPI.getWorkOrders(params)
    console.log('✅ API响应:', {
      code: response.code,
      message: response.message,
      dataExists: !!response.data
    })

    if (response.code === 200 && response.data) {
      workOrders.value = response.data.work_orders
      console.log('📦 工单数据样本:', workOrders.value.slice(0, 2))
    } else {
      error.value = response.message || '获取工单数据失败'
    }
  } catch (err) {
    console.error('❌ 获取工单数据失败:', err)
    error.value = '获取工单数据失败'
  } finally {
    loading.value = false
  }
}

// 刷新数据
async function refreshData() {
  await Promise.all([
    fetchMachineOptions(),
    fetchWorkOrders()
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

      // 统一格式化为 "2024年10月" 格式
      if (text) {
        // 将 "十月 2024" 转换为 "2024年十月"，然后再转换为数字月份
        if (text.includes('月') && text.includes('2024')) {
          // 匹配 "十月 2024" 或 "October 2024" 等格式
          text = text.replace(/(\S+月)\s+(\d{4})/, '$2年$1')

          // 转换中文月份为数字
          text = text.replace('一月', '1月')
                    .replace('二月', '2月')
                    .replace('三月', '3月')
                    .replace('四月', '4月')
                    .replace('五月', '5月')
                    .replace('六月', '6月')
                    .replace('七月', '7月')
                    .replace('八月', '8月')
                    .replace('九月', '9月')
                    .replace('十月', '10月')
                    .replace('十一月', '11月')
                    .replace('十二月', '12月')
                    .replace('十1月', '11月')
                    .replace('十2月', '12月')
        }
        el.textContent = text
      }
    })

    // 查找并替换日期 - 使用正确的Vue Ganttastic类名
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
  console.log('📊 甘特图页面已挂载')
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
.gantt-chart-page {
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
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.statistics-bar {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.statistics-cards {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 200px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.stat-card.pending {
  border-top: 4px solid #409EFF;
}

.stat-card.in-progress {
  border-top: 4px solid #E6A23C;
}

.stat-card.completed {
  border-top: 4px solid #67C23A;
}

.stat-card.total {
  border-top: 4px solid #9C27B0;
}

.card-header {
  display: flex;
  align-items: center;
  padding: 20px;
  gap: 16px;
}

.icon-container {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.pending .icon-container {
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: white;
}

.in-progress .icon-container {
  background: linear-gradient(135deg, #E6A23C, #b88230);
  color: white;
}

.completed .icon-container {
  background: linear-gradient(135deg, #67C23A, #529b2e);
  color: white;
}

.total .icon-container {
  background: linear-gradient(135deg, #9C27B0, #7b1fa2);
  color: white;
}

.card-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
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
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  color: #909399;
  font-size: 16px;
}

.loading-state .el-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.gantt-chart-wrapper {
  height: 100%;
  overflow: hidden;
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
}

/* Vue Ganttastic 自定义样式 */
.bar-label {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  padding: 6px 10px;
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  letter-spacing: 0.3px;
}

.bar-product {
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: 4px;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  font-size: 13px;
  line-height: 1.2;
}

.bar-quantity {
  color: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* 甘特图全局样式增强 */
:deep(.g-gantt-chart) {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background: #ffffff;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 隐藏Vue Ganttastic的内置标签，我们使用自定义左侧标签 */
:deep(.g-gantt-row-label) {
  display: none;
}

/* 自定义甘特图布局 */
.custom-gantt-layout {
  display: flex;
  height: 100%;
  width: 100%;
}

/* 左侧机台标签列 */
.machine-labels-column {
  width: 180px;
  min-width: 180px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-right: 2px solid #dee2e6;
  display: flex;
  flex-direction: column;
}

.machine-labels-header {
  height: 80px; /* 匹配时间轴头部高度 */
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
  background: linear-gradient(135deg, #ffffff, #f8f9fa);
  border-bottom: 2px solid #dee2e6;
}

.machine-label-item {
  height: 60px; /* 匹配甘特图行高 */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  font-size: 12px;
  color: #2c3e50;
  text-align: center;
  white-space: pre-line;
  line-height: 1.4;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 右侧甘特图区域 */
.gantt-chart-area {
  flex: 1;
  overflow: hidden;
}

:deep(.g-gantt-bar) {
  border-radius: 6px;
  transition: all 0.2s ease;
  cursor: pointer;
}

:deep(.g-gantt-bar:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
  z-index: 10;
}

:deep(.g-gantt-timeline-grid-line) {
  stroke: #e9ecef;
  stroke-width: 1;
}

:deep(.g-gantt-timeline-header) {
  background: linear-gradient(135deg, #ffffff, #f8f9fa);
  border-bottom: 2px solid #dee2e6;
  font-weight: 600;
  color: #495057;
}

/* 时间轴样式 */
:deep(.g-gantt-timeline-header-primary) {
  font-size: 14px;
  font-weight: 700;
  color: #2c3e50;
}

:deep(.g-gantt-timeline-header-secondary) {
  font-size: 12px;
  color: #6c757d;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 时间轴自定义中文显示 */
:deep(.g-gantt-timeline-header-secondary):after {
  content: '';
}



/* 滚动条样式 */
.gantt-chart-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.gantt-chart-wrapper::-webkit-scrollbar-track {
  background: #f1f3f4;
  border-radius: 4px;
}

.gantt-chart-wrapper::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #c1c8cd, #a8b2ba);
  border-radius: 4px;
}

.gantt-chart-wrapper::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #a8b2ba, #9aa5af);
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .gantt-chart-page {
    background-color: #1a1a1a;
  }

  .page-header,
  .filter-bar,
  .statistics-bar,
  .gantt-container {
    background: #2d2d2d;
    border-color: #414243;
  }

  .page-header h1 {
    color: #e5eaf3;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .filter-bar .el-form {
    flex-direction: column;
  }

  .filter-bar .el-form-item {
    margin-bottom: 16px;
  }

  .main-content {
    padding: 16px;
  }
}
</style>
