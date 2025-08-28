<template>
  <div class="gantt-chart-tab">
    <!-- 任务选择区域 -->
    <el-card class="task-selection-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>甘特图数据源</span>
          <el-button type="primary" size="small" @click="loadGanttData">
            刷新数据
          </el-button>
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
              :label="task.display_name"
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
    // 模拟获取可用的已完成排产任务
    const mockTasks: SchedulingTask[] = [
      {
        task_id: 'SCHEDULE_20250828_145614_4858b735',
        import_batch_id: 'BATCH_20250828_120000',
        task_name: '卷包旬计划智能排产 - 8月第4周',
        status: 'COMPLETED',
        current_stage: '任务完成',
        progress: 100,
        total_records: 25,
        processed_records: 25,
        start_time: '2025-08-28T14:56:14',
        end_time: '2025-08-28T15:12:33',
        execution_duration: 979,
        algorithm_config: {
          merge_enabled: true,
          split_enabled: true,
          correction_enabled: true,
          parallel_enabled: true
        },
        result_summary: {
          total_work_orders: 42,
          packing_orders: 25,
          feeding_orders: 17
        }
      },
      {
        task_id: 'SCHEDULE_20250827_093221_a1b2c3d4',
        import_batch_id: 'BATCH_20250827_090000',
        task_name: '卷包旬计划智能排产 - 8月第3周',
        status: 'COMPLETED',
        current_stage: '任务完成',
        progress: 100,
        total_records: 18,
        processed_records: 18,
        start_time: '2025-08-27T09:32:21',
        end_time: '2025-08-27T09:45:12',
        execution_duration: 771,
        algorithm_config: {
          merge_enabled: true,
          split_enabled: false,
          correction_enabled: true,
          parallel_enabled: true
        },
        result_summary: {
          total_work_orders: 28,
          packing_orders: 18,
          feeding_orders: 10
        }
      }
    ]
    
    availableTasks.value = mockTasks.map(task => ({
      ...task,
      display_name: `${task.task_name} (${task.result_summary?.total_work_orders || 0}个工单)`
    })) as (SchedulingTask & { display_name: string })[]
    
  } catch (error) {
    console.error('加载可用任务失败:', error)
    ElMessage.error('加载可用任务失败')
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
    
    // 模拟根据任务ID获取工单数据
    const mockWorkOrders: WorkOrder[] = [
      {
        work_order_nr: 'MAKER20250828000001',
        work_order_type: 'HJB',
        machine_type: '卷包机',
        machine_code: 'C01',
        product_code: '云烟(紫)',
        plan_quantity: 800,
        work_order_status: 'PENDING',
        planned_start_time: '2025-08-28T08:00:00',
        planned_end_time: '2025-08-28T16:00:00',
        created_time: new Date().toISOString()
      },
      {
        work_order_nr: 'FEEDER20250828000001',
        work_order_type: 'HWS',
        machine_type: '喂丝机',
        machine_code: 'F01',
        product_code: '云烟(紫)',
        plan_quantity: 650,
        safety_stock: 50,
        work_order_status: 'PENDING',
        planned_start_time: '2025-08-28T07:30:00',
        planned_end_time: '2025-08-28T15:30:00',
        created_time: new Date().toISOString()
      },
      {
        work_order_nr: 'MAKER20250828000002',
        work_order_type: 'HJB',
        machine_type: '卷包机',
        machine_code: 'C02',
        product_code: '玉溪(软)',
        plan_quantity: 1200,
        work_order_status: 'PENDING',
        planned_start_time: '2025-08-28T08:30:00',
        planned_end_time: '2025-08-28T18:30:00',
        created_time: new Date().toISOString()
      },
      {
        work_order_nr: 'FEEDER20250828000002',
        work_order_type: 'HWS',
        machine_type: '喂丝机',
        machine_code: 'F02',
        product_code: '玉溪(软)',
        plan_quantity: 980,
        safety_stock: 80,
        work_order_status: 'PENDING',
        planned_start_time: '2025-08-28T08:00:00',
        planned_end_time: '2025-08-28T18:00:00',
        created_time: new Date().toISOString()
      }
    ]
    
    workOrders.value = mockWorkOrders
    console.log('✅ 成功加载工单数据:', workOrders.value.length, '条')
    
    // 转换为甘特图数据
    convertToGanttData()
    
    // 计算统计信息
    calculateStatistics()
    
    // 渲染甘特图
    await nextTick()
    renderGanttChart()
    
  } catch (error) {
    console.error('加载工单数据失败:', error)
    ElMessage.error('加载工单数据失败')
  } finally {
    chartLoading.value = false
  }
}

const convertToGanttData = () => {
  ganttTasks.value = workOrders.value.map(order => ({
    id: order.work_order_nr,
    name: `${order.work_order_nr} - ${order.product_code}`,
    start: order.planned_start_time ? new Date(order.planned_start_time) : new Date(),
    end: order.planned_end_time ? new Date(order.planned_end_time) : new Date(),
    progress: order.work_order_status === 'COMPLETED' ? 100 : 
              order.work_order_status === 'IN_PROGRESS' ? 50 : 0,
    type: order.work_order_type,
    machine: order.machine_code,
    product: order.product_code,
    quantity: order.plan_quantity,
    status: order.work_order_status
  }))
}

const calculateStatistics = () => {
  statistics.totalOrders = workOrders.value.length
  statistics.makerOrders = workOrders.value.filter(o => o.work_order_type === 'HJB').length
  statistics.feederOrders = workOrders.value.filter(o => o.work_order_type === 'HWS').length
  statistics.totalQuantity = workOrders.value.reduce((sum, o) => sum + o.plan_quantity, 0)
  
  // 计算平均时长（小时）
  const totalHours = workOrders.value.reduce((sum, order) => {
    if (order.planned_start_time && order.planned_end_time) {
      const start = new Date(order.planned_start_time)
      const end = new Date(order.planned_end_time)
      return sum + (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    }
    return sum
  }, 0)
  
  statistics.avgDuration = statistics.totalOrders > 0 ? totalHours / statistics.totalOrders : 0
  
  // 简单的机台利用率计算
  const completedOrders = workOrders.value.filter(o => 
    o.work_order_status === 'COMPLETED'
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
  
  if (tasks.length === 0) {
    container.innerHTML = '<div class="no-data">暂无工单数据</div>'
    return
  }
  
  // 应用筛选
  let filteredTasks = tasks
  if (filterOptions.orderType) {
    filteredTasks = filteredTasks.filter(t => t.type === filterOptions.orderType)
  }
  
  if (filteredTasks.length === 0) {
    container.innerHTML = '<div class="no-data">没有符合筛选条件的工单</div>'
    return
  }
  
  // 计算时间范围
  const minDate = new Date(Math.min(...filteredTasks.map(t => t.start.getTime())))
  const maxDate = new Date(Math.max(...filteredTasks.map(t => t.end.getTime())))
  const timeRange = maxDate.getTime() - minDate.getTime()
  
  // 创建甘特图HTML结构
  let chartHTML = '<div class="gantt-timeline">'
  
  // 时间轴头部
  chartHTML += '<div class="timeline-header">'
  chartHTML += '<div class="machine-column">机台</div>'
  chartHTML += '<div class="time-column">'
  
  // 根据视图模式生成时间标签
  if (viewMode.value === 'day') {
    const hourCount = Math.ceil(timeRange / (1000 * 60 * 60))
    for (let i = 0; i <= hourCount; i += 2) {
      const date = new Date(minDate.getTime() + i * 1000 * 60 * 60)
      chartHTML += `<div class="time-label">${date.getHours()}:00</div>`
    }
  } else {
    const dayCount = Math.ceil(timeRange / (1000 * 60 * 60 * 24))
    for (let i = 0; i <= dayCount; i++) {
      const date = new Date(minDate.getTime() + i * 1000 * 60 * 60 * 24)
      chartHTML += `<div class="time-label">${date.getMonth() + 1}/${date.getDate()}</div>`
    }
  }
  
  chartHTML += '</div></div>'
  
  // 获取所有机台
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
      const widthPercent = (duration / timeRange) * 100
      
      const taskClass = `task-bar task-${task.type.toLowerCase()}`
      const statusClass = `status-${task.status.toLowerCase().replace('_', '-')}`
      
      chartHTML += `
        <div class="${taskClass} ${statusClass}" 
             style="left: ${startPercent}%; width: ${widthPercent}%;"
             title="${task.name} (${task.quantity}件)">
          <div class="task-content">
            ${displayOptions.showOrderDetails ? 
              `<span class="task-name">${task.id}</span>
               <span class="task-quantity">${task.quantity}</span>` : 
              `<span class="task-name">${task.id}</span>`
            }
          </div>
          ${displayOptions.showProgress ? 
            `<div class="progress-bar" style="width: ${task.progress}%"></div>` : 
            ''
          }
        </div>
      `
    })
    
    chartHTML += '</div></div>'
  })
  
  chartHTML += '</div>'
  
  container.innerHTML = chartHTML
}

const updateChart = () => {
  renderGanttChart()
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
}

.gantt-timeline {
  min-width: 800px;
  background: #fff;
}

.timeline-header {
  display: flex;
  border-bottom: 2px solid #ebeef5;
  background-color: #f5f7fa;
  position: sticky;
  top: 0;
  z-index: 10;
}

.machine-column {
  width: 120px;
  padding: 12px;
  font-weight: bold;
  border-right: 1px solid #ebeef5;
  background-color: #f5f7fa;
}

.time-column {
  flex: 1;
  display: flex;
}

.time-label {
  flex: 1;
  padding: 12px 5px;
  text-align: center;
  border-right: 1px solid #ebeef5;
  font-size: 12px;
  min-width: 60px;
}

.timeline-row {
  display: flex;
  border-bottom: 1px solid #ebeef5;
}

.machine-label {
  width: 120px;
  padding: 15px 12px;
  border-right: 1px solid #ebeef5;
  font-weight: 500;
  display: flex;
  align-items: center;
  background-color: #fafafa;
}

.task-timeline {
  flex: 1;
  position: relative;
  height: 50px;
  background-color: #fff;
}

.task-bar {
  position: absolute;
  height: 30px;
  top: 10px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.task-bar:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  border-color: rgba(0, 0, 0, 0.1);
}

.task-maker {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.task-feeder {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.status-pending {
  opacity: 0.7;
}

.status-in-progress {
  opacity: 0.9;
}

.status-completed {
  opacity: 1;
  border-color: #67c23a;
}

.status-cancelled {
  opacity: 0.5;
  filter: grayscale(50%);
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
}

.task-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-quantity {
  font-size: 10px;
  opacity: 0.9;
  font-weight: normal;
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.2);
  z-index: 1;
  border-radius: 3px;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  font-size: 14px;
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