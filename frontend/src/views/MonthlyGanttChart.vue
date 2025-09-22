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

        <!-- 机台数 -->
        <div class="stat-card total">
          <div class="card-header">
            <div class="icon-container">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="card-content">
              <div class="stat-value">{{ uniqueMachineCount }}</div>
              <div class="stat-label">机台数</div>
            </div>
          </div>
        </div>

        <!-- 总计划产量 -->
        <div class="stat-card pending">
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
              :disable-tooltip="true"
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
const machines = ref<Array<{ machine_code: string; machine_name: string }>>([])
const machineOptions = ref<Array<{ machine_code: string; machine_name: string }>>([])

// 筛选条件
const filterOptions = ref({
  task_id: '',
  machine_code: ''
})

// 计算属性
const uniqueMachineCount = computed(() => {
  return machines.value.length
})

// 格式化总产量
const formattedTotalQuantity = computed(() => {
  const total = workOrders.value.reduce((sum, order) => sum + (order.plan_quantity || 0), 0)
  if (total > 10000) {
    return (total / 10000).toFixed(1) + '万'
  }
  return total.toLocaleString()
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

  // 限制在单个月内显示，获取数据的主要月份
  const mainMonth = minStart.getMonth()
  const mainYear = minStart.getFullYear()
  
  // 设置为当月的第一天和最后一天
  const monthStart = new Date(mainYear, mainMonth, 1)
  const monthEnd = new Date(mainYear, mainMonth + 1, 0) // 下个月的第0天 = 本月最后一天
  
  // 设置具体时间
  monthStart.setHours(0, 0, 0, 0)
  monthEnd.setHours(23, 59, 59, 999)

  return {
    start: formatDateTime(monthStart),
    end: formatDateTime(monthEnd)
  }
})

const chartHeight = computed(() => {
  return Math.max(400, ganttRows.value.length * 60) + 'px'
})

// 转换月度工单数据为甘特图行数据
const ganttRows = computed(() => {
  if (workOrders.value.length === 0) return []

  // 按机台组合分组 - 按工单的卷包机+喂丝机组合
  const machineGroups: Record<string, MonthlyWorkOrder[]> = {}
  
  // 先按工单号分组，然后合并同一工单的机台信息
  const workOrderGroups: Record<string, MonthlyWorkOrder[]> = {}
  workOrders.value.forEach(order => {
    if (!workOrderGroups[order.work_order_nr]) {
      workOrderGroups[order.work_order_nr] = []
    }
    workOrderGroups[order.work_order_nr].push(order)
  })
  
  // 为每个工单组合创建机台组合键
  Object.values(workOrderGroups).forEach(orderGroup => {
    // 从同一工单的所有记录中提取机台信息
    const feederCode = orderGroup[0]?.assigned_feeder_code
    const makerCode = orderGroup[0]?.assigned_maker_code
    
    let machineKey = ''
    if (feederCode && makerCode) {
      machineKey = `${makerCode} + ${feederCode}\n(卷包机 + 喂丝机)`
    } else if (makerCode) {
      machineKey = `${makerCode}\n(卷包机)`
    } else if (feederCode) {
      machineKey = `${feederCode}\n(喂丝机)`
    } else {
      machineKey = `${orderGroup[0]?.machine_code || 'UNKNOWN'}\n(未知机台)`
    }

    if (!machineGroups[machineKey]) {
      machineGroups[machineKey] = []
    }
    // 只添加第一个工单作为代表，因为同一工单的不同机台记录应该合并显示
    if (machineGroups[machineKey].length === 0 || 
        !machineGroups[machineKey].find(o => o.work_order_nr === orderGroup[0].work_order_nr)) {
      machineGroups[machineKey].push(orderGroup[0])
    }
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
          label: `${order.work_order_nr} - ${order.article_name || order.product_code}`,
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
        product: order.article_name || order.product_code,
        quantity: order.plan_quantity,
        status: order.work_order_status
      }
    })
  }))
})

// 获取条形颜色
function getBarColor(order: MonthlyWorkOrder): string {
  const status = order.work_order_status || 'SCHEDULED'
  
  // 基于产品类型的渐变色（与旬计划保持一致）
  const productType = order.article_name || order.product_code

  if (productType?.includes('利群(软蓝)')) {
    return 'linear-gradient(135deg, #409eff, #337ecc)' // 蓝色渐变
  } else if (productType?.includes('利群(新版)') || productType?.includes('利群（新版）')) {
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
  } else if (productType?.includes('利群(新二代)')) {
    return 'linear-gradient(135deg, #17a2b8, #138496)' // 蓝绿渐变
  } else if (productType?.includes('利群')) {
    return 'linear-gradient(135deg, #6f42c1, #5a2d91)' // 紫色渐变（通用利群）
  } else {
    // 基于状态的颜色
    switch (status) {
      case 'COMPLETED':
        return 'linear-gradient(135deg, #67c23a, #529b2e)' // 绿色渐变
      case 'RUNNING':
        return 'linear-gradient(135deg, #409eff, #337ecc)' // 蓝色渐变
      case 'SCHEDULED':
        return 'linear-gradient(135deg, #e6a23c, #b88230)' // 橙色渐变
      case 'PAUSED':
        return 'linear-gradient(135deg, #f56c6c, #c45656)' // 红色渐变
      default:
        return 'linear-gradient(135deg, #909399, #73767a)' // 灰色渐变
    }
  }
}

// 工具方法
function formatDateTime(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function formatChineseDateTime(date: Date): string {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}年${month}月${day}日 ${hours}:${minutes}`
}

// 事件处理
function onBarClick(event: any) {
  const bar = event.bar
  console.log('点击条形:', bar)
  ElMessage.info(`工单详情: ${bar.workOrder} - ${bar.product} (${bar.quantity}箱)`)
}

function onBarMouseenter(event: any) {
  const bar = event.bar
  console.log('悬停条形:', bar)
  
  // 创建自定义中文tooltip
  const tooltip = document.createElement('div')
  tooltip.id = 'custom-gantt-tooltip'
  tooltip.style.cssText = `
    position: fixed;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 10000;
    pointer-events: none;
    min-width: 280px;
    max-width: 400px;
    line-height: 1.5;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(4px);
  `
  
  const startTime = new Date(bar.startTime)
  const endTime = new Date(bar.endTime)
  
  tooltip.innerHTML = `
    <div style="font-weight: 600; color: #fff; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.2);">
      ${bar.product}
    </div>
    <div style="margin-bottom: 4px;">
      <span style="color: #ddd; display: inline-block; width: 60px;">工单号</span>
      <span style="color: #fff; font-family: monospace;">${bar.workOrder}</span>
    </div>
    <div style="margin-bottom: 4px;">
      <span style="color: #ddd; display: inline-block; width: 60px;">数量</span>
      <span style="color: #4CAF50; font-weight: 500;">${bar.quantity}箱</span>
    </div>
    <div style="margin-bottom: 4px;">
      <span style="color: #ddd; display: inline-block; width: 60px;">开始</span>
      <span style="color: #2196F3;">${formatChineseDateTime(startTime)}</span>
    </div>
    <div>
      <span style="color: #ddd; display: inline-block; width: 60px;">结束</span>
      <span style="color: #FF9800;">${formatChineseDateTime(endTime)}</span>
    </div>
  `
  
  document.body.appendChild(tooltip)
  
  // 鼠标移动时更新tooltip位置
  const updateTooltipPosition = (e: MouseEvent) => {
    tooltip.style.left = (e.clientX + 10) + 'px'
    tooltip.style.top = (e.clientY + 10) + 'px'
  }
  
  document.addEventListener('mousemove', updateTooltipPosition)
  tooltip.setAttribute('data-mousemove-listener', 'true')
}

function onBarMouseleave(event: any) {
  console.log('离开条形:', event.bar)
  
  // 移除自定义tooltip
  const tooltip = document.getElementById('custom-gantt-tooltip')
  if (tooltip) {
    // 移除鼠标移动监听器
    if (tooltip.getAttribute('data-mousemove-listener')) {
      document.removeEventListener('mousemove', (e: MouseEvent) => {
        tooltip.style.left = (e.clientX + 10) + 'px'
        tooltip.style.top = (e.clientY + 10) + 'px'
      })
    }
    tooltip.remove()
  }
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
        scheduleData.gantt_data.schedule_blocks.forEach((block: any) => {
          extractedWorkOrders.push({
            work_order_nr: block.work_order_nr,
            work_order_type: block.machine_type === 'FEEDING' ? 'HWS' : 'HJB',
            machine_type: block.machine_type === 'FEEDING' ? '喂丝机' : '卷包机',
            machine_code: block.machine_code,
            maker_code: block.machine_type === 'PACKING' ? block.machine_code : undefined,
            feeder_code: block.machine_type === 'FEEDING' ? block.machine_code : undefined,
            assigned_maker_code: block.assigned_maker_code, // 添加分配的卷包机代码
            assigned_feeder_code: block.assigned_feeder_code, // 添加分配的喂丝机代码
            product_code: block.article_nr,
            article_name: block.article_name, // 添加产品名称
            plan_quantity: block.allocated_quantity || Math.round(block.duration * 10) || 100,
            work_order_status: block.status || 'SCHEDULED',
            planned_start_time: block.start_time,
            planned_end_time: block.end_time,
            monthly_batch_id: monthlyBatchId,
            duration: block.duration, // 添加持续时间
            color: block.color || '#409EFF' // 添加颜色
          })
        })
      }

      workOrders.value = extractedWorkOrders
      
      // 提取机台信息
      const uniqueMachines = new Set<string>()
      extractedWorkOrders.forEach(order => {
        if (order.machine_code) {
          uniqueMachines.add(order.machine_code)
        }
      })
      
      machines.value = Array.from(uniqueMachines).map(code => ({
        machine_code: code,
        machine_name: code
      }))
      
      // 更新筛选器中的机台选项
      machineOptions.value = machines.value
      
      console.log('📦 转换后的月度工单数据样本:', workOrders.value.slice(0, 2))
      console.log('🔧 提取的机台信息:', machines.value.length, '个机台')
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
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  font-size: 24px;
}

.completed .icon-container {
  background: linear-gradient(135deg, #67C23A, #85CE61);
  color: white;
}

.total .icon-container {
  background: linear-gradient(135deg, #9C27B0, #BA68C8);
  color: white;
}

.pending .icon-container {
  background: linear-gradient(135deg, #409EFF, #66B3FF);
  color: white;
}

.card-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 4px;
  line-height: 1;
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
