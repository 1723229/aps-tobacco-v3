<template>
  <div class="gantt-chart-tab">
    <!-- 任务选择区域 -->
    <el-card class="task-selection-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>甘特图数据源</span>
          <div>
            <el-button type="primary" size="small" @click="loadGanttData">
              刷新数据
            </el-button>
            <el-button type="success" size="small" @click="forceReloadChart" v-if="selectedTaskId">
              重新渲染
            </el-button>
          </div>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="8">
          <el-select
            v-model="selectedTaskId"
            placeholder="选择排产任务"
            style="width: 100%"
            filterable
            clearable
            @change="onTaskSelected"
          >
            <el-option
              v-for="task in availableTasks"
              :key="task.task_id"
              :label="`${task.task_name} (${task.result_summary?.total_work_orders || 0}个工单)`"
              :value="task.task_id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ task.task_name }}</span>
                <el-tag 
                  :type="getTaskStatusType(task.status)" 
                  size="small"
                >
                  {{ getTaskStatusText(task.status) }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select
            v-model="filterOptions.orderType"
            placeholder="工单类型筛选"
            style="width: 100%"
            clearable
            @change="updateChart"
          >
            <el-option label="全部工单" value="" />
            <el-option label="卷包机工单" value="HJB" />
            <el-option label="喂丝机工单" value="HWS" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select
            v-model="filterOptions.timeRange"
            placeholder="时间范围"
            style="width: 100%"
            @change="updateChart"
          >
            <el-option label="今日" value="today" />
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
            <el-option label="全部" value="all" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 甘特图控制面板 -->
    <el-card class="control-panel" shadow="hover" v-if="selectedTaskId">
      <template #header>
        <div class="card-header">
          <span>显示控制</span>
          <div class="chart-legend">
            <div class="legend-item">
              <div class="legend-color maker-color"></div>
              <span>卷包机工单(HJB)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color feeder-color"></div>
              <span>喂丝机工单(HWS)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color maintenance-color"></div>
              <span>轮保时间</span>
            </div>
          </div>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="control-item">
            <span>显示机台标签:</span>
            <el-switch v-model="displayOptions.showMachineLabels" @change="updateChart" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="control-item">
            <span>显示工单详情:</span>
            <el-switch v-model="displayOptions.showOrderDetails" @change="updateChart" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="control-item">
            <span>显示时间网格:</span>
            <el-switch v-model="displayOptions.showTimeGrid" @change="updateChart" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="control-item">
            <span>显示进度条:</span>
            <el-switch v-model="displayOptions.showProgress" @change="updateChart" />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 甘特图容器 -->
    <el-card class="gantt-container" shadow="hover" v-if="selectedTaskId">
      <template #header>
        <div class="card-header">
          <span>生产排产时间轴</span>
          <div class="header-actions">
            <el-button-group size="small">
              <el-button :type="viewMode === 'day' ? 'primary' : 'default'" @click="setViewMode('day')">
                日视图
              </el-button>
              <el-button :type="viewMode === 'week' ? 'primary' : 'default'" @click="setViewMode('week')">
                周视图
              </el-button>
              <el-button :type="viewMode === 'month' ? 'primary' : 'default'" @click="setViewMode('month')">
                月视图
              </el-button>
            </el-button-group>
            <el-button size="small" @click="exportChart">
              导出图表
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="chartLoading" class="gantt-chart-wrapper">
        <div ref="ganttChartRef" class="gantt-chart"></div>
      </div>
    </el-card>

    <!-- 统计信息面板 -->
    <el-card class="statistics-panel" shadow="hover" v-if="selectedTaskId && workOrders.length > 0">
      <template #header>
        <span>排产统计信息</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="4">
          <el-statistic
            title="总工单数"
            :value="statistics.totalOrders"
            :precision="0"
          >
            <template #suffix>
              <span>个</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic
            title="卷包机工单"
            :value="statistics.makerOrders"
            :precision="0"
          >
            <template #suffix>
              <span>个</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic
            title="喂丝机工单"
            :value="statistics.feederOrders"
            :precision="0"
          >
            <template #suffix>
              <span>个</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic
            title="机台利用率"
            :value="statistics.machineUtilization"
            :precision="1"
          >
            <template #suffix>
              <span>%</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic
            title="总计划产量"
            :value="statistics.totalQuantity"
            :precision="0"
          >
            <template #suffix>
              <span>件</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic
            title="平均工单时长"
            :value="statistics.avgDuration"
            :precision="1"
          >
            <template #suffix>
              <span>小时</span>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!selectedTaskId" description="请选择排产任务查看甘特图" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { SchedulingAPI, WorkOrderAPI } from '@/services/api'
import type { SchedulingTask, WorkOrder } from '@/services/api'

// 响应式数据
const chartLoading = ref(false)
const ganttChartRef = ref<HTMLElement>()
const selectedTaskId = ref<string>('')
const availableTasks = ref<SchedulingTask[]>([])
const workOrders = ref<WorkOrder[]>([])
const viewMode = ref<'day' | 'week' | 'month'>('week')

// 筛选选项
const filterOptions = reactive({
  orderType: '',
  timeRange: 'week'
})

// 显示选项
const displayOptions = reactive({
  showMachineLabels: true,
  showOrderDetails: true,
  showTimeGrid: true,
  showProgress: true
})

// 统计信息
const statistics = reactive({
  totalOrders: 0,
  makerOrders: 0,
  feederOrders: 0,
  machineUtilization: 0,
  totalQuantity: 0,
  avgDuration: 0
})

// 甘特图任务数据结构
interface GanttTask {
  id: string
  name: string
  start: Date
  end: Date
  progress: number
  type: 'HJB' | 'HWS' | 'MAINTENANCE'
  machine: string
  product: string
  quantity: number
  status: string
}

const ganttTasks = ref<GanttTask[]>([])

// 方法定义
const loadAvailableTasks = async () => {
  try {
    // 从API获取已完成的排产任务
    const response = await fetch('/api/v1/scheduling/tasks?status=COMPLETED&page_size=50')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.code === 200 && result.data?.tasks) {
      availableTasks.value = result.data.tasks.map((task: any) => ({
        task_id: task.task_id,
        import_batch_id: task.import_batch_id,
        task_name: task.task_name,
        status: task.status,
        current_stage: task.current_stage,
        progress: task.progress,
        total_records: task.total_records,
        processed_records: task.processed_records,
        start_time: task.start_time,
        end_time: task.end_time,
        execution_duration: task.execution_duration,
        algorithm_config: task.algorithm_config,
        result_summary: task.result_summary
      })) as SchedulingTask[]
      
      // 自动选择第一个任务
      if (availableTasks.value.length > 0 && !selectedTaskId.value) {
        selectedTaskId.value = availableTasks.value[0].task_id
        console.log('自动选择第一个任务:', selectedTaskId.value)
        await onTaskSelected(selectedTaskId.value)
      }
    } else {
      console.warn('未找到已完成的排产任务')
      availableTasks.value = []
    }
    
  } catch (error) {
    console.error('加载可用任务失败:', error)
    ElMessage.error('加载可用任务失败')
    // 如果API失败，显示空状态而不是模拟数据
    availableTasks.value = []
  }
}

const onTaskSelected = async (taskId: string) => {
  if (!taskId) {
    workOrders.value = []
    ganttTasks.value = []
    return
  }
  
  selectedTaskId.value = taskId
  await loadWorkOrders()
}

const loadWorkOrders = async () => {
  if (!selectedTaskId.value) return
  
  chartLoading.value = true
  
  try {
    console.log('加载任务工单:', selectedTaskId.value)
    
    // 使用统一的API调用
    const response = await WorkOrderAPI.getWorkOrders({
      task_id: selectedTaskId.value,
      page_size: 1000
    })
    
    if (response.code === 200 && response.data?.work_orders) {
      // 直接使用API返回的工单数据，确保类型一致
      workOrders.value = response.data.work_orders.map((order: any) => ({
        work_order_nr: order.work_order_nr,
        work_order_type: order.work_order_type,
        machine_type: order.machine_type,
        machine_code: order.machine_code,
        product_code: order.product_code,
        plan_quantity: order.plan_quantity,
        safety_stock: order.safety_stock || 0,
        work_order_status: order.work_order_status,
        planned_start_time: order.planned_start_time,
        planned_end_time: order.planned_end_time,
        actual_start_time: order.actual_start_time,
        actual_end_time: order.actual_end_time,
        created_time: order.created_time,
        updated_time: order.updated_time
      })) as WorkOrder[]
      
      console.log('✅ 成功加载工单数据:', workOrders.value.length, '条')
      console.log('📦 工单数据样本:', workOrders.value.slice(0, 2))
    } else {
      console.warn('API返回数据格式异常:', response)
      workOrders.value = []
    }
    
    // 转换为甘特图数据
    convertToGanttData()
    console.log('甘特图数据转换完成:', ganttTasks.value.length, '个任务')
    console.log('前3个任务:', ganttTasks.value.slice(0, 3))
    
    // 计算统计信息
    calculateStatistics()
    
    // 渲染甘特图
    await nextTick()
    renderGanttChart()
    
  } catch (error) {
    console.error('加载工单数据失败:', error)
    ElMessage.error('加载工单数据失败')
    workOrders.value = []
  } finally {
    chartLoading.value = false
  }
}

const convertToGanttData = () => {
  ganttTasks.value = workOrders.value.map(order => {
    // 根据实际API返回的work_order_type映射
    let ganttType: 'HJB' | 'HWS' | 'MAINTENANCE' = 'HJB'
    if (order.work_order_type === 'HWS' || order.machine_type === '喂丝机') {
      ganttType = 'HWS'
    } else if (order.work_order_type === 'HJB' || order.machine_type === '卷包机') {
      ganttType = 'HJB'
    }
    
    // 处理时间数据
    let startTime: Date
    let endTime: Date
    
    if (order.planned_start_time) {
      startTime = new Date(order.planned_start_time)
    } else {
      startTime = new Date()
    }
    
    if (order.planned_end_time) {
      endTime = new Date(order.planned_end_time)
    } else {
      endTime = new Date(startTime.getTime() + 8 * 60 * 60 * 1000) // 默认8小时
    }
    
    // 确保时间有效
    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      console.warn('无效时间数据:', order.work_order_nr, order.planned_start_time, order.planned_end_time)
      const now = new Date()
      startTime = now
      endTime = new Date(now.getTime() + 8 * 60 * 60 * 1000)
    }
    
    // 计算进度
    let progress = 0
    const status = order.work_order_status.toLowerCase()
    if (status.includes('completed')) {
      progress = 100
    } else if (status.includes('progress') || status.includes('running')) {
      progress = 50
    }
    
    return {
      id: order.work_order_nr,
      name: `${order.work_order_nr} - ${order.product_code}`,
      start: startTime,
      end: endTime,
      progress: progress,
      type: ganttType,
      machine: order.machine_code,
      product: order.product_code,
      quantity: order.plan_quantity,
      status: status
    }
  })
}

const calculateStatistics = () => {
  statistics.totalOrders = workOrders.value.length
  // 根据实际API数据计算卷包机工单（work_order_type为HJB）
  statistics.makerOrders = workOrders.value.filter(o => 
    o.work_order_type === 'HJB' || o.machine_type === '卷包机'
  ).length
  // 根据实际API数据计算喂丝机工单（work_order_type为HWS）
  statistics.feederOrders = workOrders.value.filter(o => 
    o.work_order_type === 'HWS' || o.machine_type === '喂丝机'
  ).length
  statistics.totalQuantity = workOrders.value.reduce((sum, o) => sum + (o.plan_quantity || 0), 0)
  
  // 计算平均时长（小时）
  const totalHours = workOrders.value.reduce((sum, order) => {
    if (order.planned_start_time && order.planned_end_time) {
      const start = new Date(order.planned_start_time)
      const end = new Date(order.planned_end_time)
      if (!isNaN(start.getTime()) && !isNaN(end.getTime())) {
        return sum + (end.getTime() - start.getTime()) / (1000 * 60 * 60)
      }
    }
    return sum
  }, 0)
  
  statistics.avgDuration = statistics.totalOrders > 0 ? totalHours / statistics.totalOrders : 0
  
  // 计算机台利用率（基于已完成工单）
  const completedOrders = workOrders.value.filter(o => 
    o.work_order_status.toLowerCase().includes('completed')
  ).length
  statistics.machineUtilization = statistics.totalOrders > 0 ? 
    (completedOrders / statistics.totalOrders) * 100 : 0
}

const renderGanttChart = () => {
  if (!ganttChartRef.value || ganttTasks.value.length === 0) return
  
  // 清空现有内容
  ganttChartRef.value.innerHTML = ''
  
  // 创建简化版甘特图
  createSimpleGanttChart()
}

const createSimpleGanttChart = () => {
  if (!ganttChartRef.value) return
  
  const container = ganttChartRef.value
  const tasks = ganttTasks.value
  
  console.log('开始渲染甘特图，任务数量:', tasks.length)
  
  if (tasks.length === 0) {
    console.log('没有任务数据，显示空状态')
    container.innerHTML = '<div class="no-data">暂无工单数据</div>'
    return
  }
  
  // 应用筛选
  let filteredTasks = tasks
  if (filterOptions.orderType) {
    console.log('应用筛选条件:', filterOptions.orderType)
    filteredTasks = filteredTasks.filter(t => {
      if (filterOptions.orderType === 'HJB') {
        return t.type === 'HJB'
      } else if (filterOptions.orderType === 'HWS') {
        return t.type === 'HWS'
      }
      return true
    })
  }
  
  console.log('筛选后的任务数量:', filteredTasks.length)
  
  if (filteredTasks.length === 0) {
    console.log('筛选后没有任务，显示空状态')
    container.innerHTML = '<div class="no-data">没有符合筛选条件的工单</div>'
    return
  }
  
  // 计算时间范围
  const minDate = new Date(Math.min(...filteredTasks.map(t => t.start.getTime())))
  const maxDate = new Date(Math.max(...filteredTasks.map(t => t.end.getTime())))
  const timeRange = maxDate.getTime() - minDate.getTime()
  
  console.log('时间范围计算:', {
    minDate: minDate.toISOString(),
    maxDate: maxDate.toISOString(), 
    timeRangeDays: timeRange / (1000 * 60 * 60 * 24),
    sampleTask: filteredTasks[0]
  })
  
  // 创建甘特图HTML结构
  let chartHTML = '<div class="gantt-timeline">'
  
  // 时间轴头部
  chartHTML += '<div class="timeline-header">'
  chartHTML += '<div class="machine-column">机台</div>'
  chartHTML += '<div class="time-column">'
  
  // 生成时间标签 - 改进显示逻辑
  const timeLabelCount = Math.min(20, Math.max(5, Math.ceil(timeRange / (1000 * 60 * 60 * 2)))) // 每2小时一个标签，最多20个
  for (let i = 0; i <= timeLabelCount; i++) {
    const date = new Date(minDate.getTime() + (i / timeLabelCount) * timeRange)
    const label = viewMode.value === 'day' 
      ? `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:00`
      : `${date.getMonth() + 1}/${date.getDate()}`
    chartHTML += `<div class="time-label" style="flex: 1; min-width: 80px;">${label}</div>`
  }
  
  chartHTML += '</div></div>'
  
  // 获取所有机台并排序
  const machines = [...new Set(filteredTasks.map(t => t.machine))].sort()
  
  // 为每台机台创建时间轴
  machines.forEach(machine => {
    const machineTasks = filteredTasks.filter(t => t.machine === machine)
    
    chartHTML += '<div class="timeline-row">'
    if (displayOptions.showMachineLabels) {
      chartHTML += `<div class="machine-label">${machine}</div>`
    } else {
      chartHTML += '<div class="machine-label"></div>'
    }
    chartHTML += '<div class="task-timeline">'
    
    machineTasks.forEach(task => {
      const startPercent = ((task.start.getTime() - minDate.getTime()) / timeRange) * 100
      const duration = task.end.getTime() - task.start.getTime()
      const widthPercent = Math.max(1, (duration / timeRange) * 100) // 最小宽度1%
      
      console.log(`工单 ${task.id} 渲染参数:`, {
        machine: task.machine,
        startPercent: startPercent.toFixed(2) + '%',
        widthPercent: widthPercent.toFixed(2) + '%',
        startTime: task.start.toISOString(),
        endTime: task.end.toISOString()
      })
      
      const taskClass = `task-bar task-${task.type.toLowerCase()}`
      const statusClass = `status-${task.status.toLowerCase().replace('_', '-')}`
      
      // 改进的工单信息显示
      const startTime = task.start.toLocaleString('zh-CN', { 
        month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit' 
      })
      const endTime = task.end.toLocaleString('zh-CN', { 
        month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit' 
      })
      const durationHours = Math.round(duration / (1000 * 60 * 60) * 10) / 10
      
      const tooltipInfo = `工单: ${task.id}\\n产品: ${task.product}\\n数量: ${task.quantity}\\n开始: ${startTime}\\n结束: ${endTime}\\n时长: ${durationHours}小时\\n状态: ${getTaskStatusText(task.status)}`
      
      chartHTML += `
        <div class="${taskClass} ${statusClass}" 
             style="left: ${startPercent}%; width: ${widthPercent}%; position: absolute; cursor: pointer;"
             title="${tooltipInfo}"
             data-task-id="${task.id}">
          <div class="task-content">
            ${displayOptions.showOrderDetails ? 
              `<span class="task-name">${task.id}</span>
               <span class="task-quantity">${task.quantity}</span>` : 
              `<span class="task-name">${task.id}</span>`
            }
          </div>
          ${displayOptions.showProgress && task.progress > 0 ? 
            `<div class="progress-bar" style="width: ${task.progress}%"></div>` : 
            ''
          }
        </div>
      `
    })
    
    chartHTML += '</div></div>'
  })
  
  chartHTML += '</div>'
  
  console.log('生成的甘特图HTML长度:', chartHTML.length)
  console.log('HTML前500字符:', chartHTML.substring(0, 500))
  
  container.innerHTML = chartHTML
  
  // 添加点击事件处理
  container.addEventListener('click', (event) => {
    const target = event.target as HTMLElement
    const taskBar = target.closest('.task-bar') as HTMLElement
    if (taskBar && taskBar.dataset.taskId) {
      const taskId = taskBar.dataset.taskId
      const task = filteredTasks.find(t => t.id === taskId)
      if (task) {
        ElMessage.info(`工单详情: ${task.id} - ${task.product} (${task.quantity})`)
      }
    }
  })
}

const updateChart = () => {
  renderGanttChart()
}

const forceReloadChart = async () => {
  console.log('强制重新加载甘特图数据')
  if (selectedTaskId.value) {
    await loadWorkOrders()
    ElMessage.success('甘特图数据已重新加载')
  }
}

const loadGanttData = () => {
  if (selectedTaskId.value) {
    loadWorkOrders()
  } else {
    loadAvailableTasks()
  }
}

const setViewMode = (mode: 'day' | 'week' | 'month') => {
  viewMode.value = mode
  updateChart()
}

const exportChart = () => {
  ElMessage.info('导出甘特图功能开发中...')
}

// 状态处理方法
const getTaskStatusType = (status: string) => {
  const statusMap: Record<string, any> = {
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'RUNNING': 'warning',
    'PENDING': 'info',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'info'
}

const getTaskStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'RUNNING': '运行中',
    'PENDING': '等待中',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

// 生命周期
onMounted(() => {
  loadAvailableTasks()
})
</script>

<style scoped>
.gantt-chart-tab {
  padding: 0;
}

.task-selection-card, .control-panel, .gantt-container, .statistics-panel {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.chart-legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.maker-color {
  background-color: #409eff;
}

.feeder-color {
  background-color: #67c23a;
}

.maintenance-color {
  background-color: #f56c6c;
}

.control-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 0;
}

.gantt-chart-wrapper {
  min-height: 400px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  position: relative;
}

.gantt-timeline {
  min-width: 800px;
  background: #fff;
  font-family: 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.timeline-header {
  display: flex;
  border-bottom: 2px solid #ebeef5;
  background: linear-gradient(135deg, #f5f7fa, #f0f2f5);
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.machine-column {
  width: 120px;
  padding: 12px;
  font-weight: bold;
  border-right: 1px solid #ebeef5;
  background: linear-gradient(135deg, #f5f7fa, #f0f2f5);
  color: #333;
  font-size: 14px;
}

.time-column {
  flex: 1;
  display: flex;
  min-width: 600px;
}

.time-label {
  padding: 12px 5px;
  text-align: center;
  border-right: 1px solid #ebeef5;
  font-size: 12px;
  min-width: 80px;
  color: #666;
  font-weight: 500;
  background: linear-gradient(135deg, #f9fafb, #f5f7fa);
}

.time-label:hover {
  background: linear-gradient(135deg, #e6f7ff, #f0f9ff);
  color: #1890ff;
}

.timeline-row {
  display: flex;
  border-bottom: 1px solid #ebeef5;
  transition: background-color 0.2s;
}

.timeline-row:hover {
  background-color: #fafbfc;
}

.machine-label {
  width: 120px;
  padding: 15px 12px;
  border-right: 1px solid #ebeef5;
  font-weight: 500;
  display: flex;
  align-items: center;
  background-color: #fafafa;
  font-size: 13px;
  color: #555;
}

.task-timeline {
  flex: 1;
  position: relative;
  height: 50px;
  background: linear-gradient(90deg, #ffffff 0%, #fafbfc 50%, #ffffff 100%);
  min-width: 600px;
}

.task-bar {
  position: absolute;
  height: 30px;
  top: 10px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  font-size: 11px;
  min-width: 40px; /* 确保最小宽度 */
}

.task-bar:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
  z-index: 5;
}

/* 卷包机工单样式 */
.task-hjb {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  border-color: rgba(64, 158, 255, 0.3);
}

.task-hjb:hover {
  background: linear-gradient(135deg, #337ecc, #5aa7ff);
  border-color: #409eff;
}

/* 喂丝机工单样式 */
.task-hws {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  border-color: rgba(103, 194, 58, 0.3);
}

.task-hws:hover {
  background: linear-gradient(135deg, #529b2e, #73c755);
  border-color: #67c23a;
}

/* 维护工单样式 */
.task-maintenance {
  background: linear-gradient(135deg, #f56c6c, #f78989);
  border-color: rgba(245, 108, 108, 0.3);
}

.task-maintenance:hover {
  background: linear-gradient(135deg, #f23030, #f56c6c);
  border-color: #f56c6c;
}

/* 工单状态样式 */
.status-pending {
  opacity: 0.75;
  filter: saturate(0.8);
}

.status-in-progress {
  opacity: 0.95;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.95; }
  50% { opacity: 1; }
}

.status-completed {
  opacity: 1;
  box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.3);
}

.status-cancelled {
  opacity: 0.4;
  filter: grayscale(80%);
  text-decoration: line-through;
}

.task-content {
  padding: 6px 10px;
  color: white;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  position: relative;
  z-index: 2;
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.task-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  font-weight: 600;
}

.task-quantity {
  font-size: 10px;
  opacity: 0.9;
  font-weight: normal;
  margin-left: 8px;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 10px;
  flex-shrink: 0;
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, 
    rgba(255, 255, 255, 0.3), 
    rgba(255, 255, 255, 0.1)
  );
  z-index: 1;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  font-size: 14px;
  background: #f9f9f9;
  border-radius: 4px;
}

/* 网格线效果 */
.gantt-timeline::before {
  content: '';
  position: absolute;
  top: 0;
  left: 120px; /* 机台列宽度 */
  right: 0;
  height: 100%;
  background-image: linear-gradient(90deg, 
    transparent 0%, 
    rgba(235, 238, 245, 0.5) 1px, 
    transparent 1px
  );
  background-size: 80px 1px; /* 与时间标签宽度对应 */
  pointer-events: none;
  z-index: 1;
}

.statistics-panel :deep(.el-statistic__content) {
  font-size: 20px;
  font-weight: bold;
}

.statistics-panel :deep(.el-statistic__head) {
  color: #606266;
  font-size: 13px;
}
</style>