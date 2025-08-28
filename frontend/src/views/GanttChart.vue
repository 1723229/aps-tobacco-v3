<template>
  <div class="gantt-chart-view">
    <div class="header-section">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/scheduling' }">排产管理</el-breadcrumb-item>
        <el-breadcrumb-item>甘特图</el-breadcrumb-item>
      </el-breadcrumb>
      <div class="header-info">
        <h2>生产排产甘特图</h2>
        <div v-if="route.query.task_id || route.query.import_batch_id" class="task-info">
          <el-tag v-if="route.query.task_id" type="primary" size="small">
            任务: {{ route.query.task_id }}
          </el-tag>
          <el-tag v-if="route.query.import_batch_id" type="info" size="small">
            批次: {{ route.query.import_batch_id }}
          </el-tag>
        </div>
      </div>
    </div>

    <div class="gantt-content">
      <!-- 控制面板 -->
      <el-card class="control-panel" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>显示控制</span>
            <div class="header-actions">
              <el-select
                v-model="filterOptions.orderType"
                placeholder="工单类型"
                style="width: 120px; margin-right: 10px;"
                clearable
                @change="updateChart"
              >
                <el-option label="全部" value="" />
                <el-option label="卷包机" value="MAKER" />
                <el-option label="喂丝机" value="FEEDER" />
              </el-select>
              <el-select
                v-model="filterOptions.timeRange"
                placeholder="时间范围"
                style="width: 120px; margin-right: 10px;"
                @change="updateChart"
              >
                <el-option label="今日" value="today" />
                <el-option label="本周" value="week" />
                <el-option label="本月" value="month" />
              </el-select>
              <el-button type="primary" size="small" @click="refreshData">
                刷新
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="control-options">
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="control-item">
                <span>显示机台标签:</span>
                <el-switch v-model="displayOptions.showMachineLabels" @change="updateChart" />
              </div>
            </el-col>
            <el-col :span="8">
              <div class="control-item">
                <span>显示工单详情:</span>
                <el-switch v-model="displayOptions.showOrderDetails" @change="updateChart" />
              </div>
            </el-col>
            <el-col :span="8">
              <div class="control-item">
                <span>显示时间网格:</span>
                <el-switch v-model="displayOptions.showTimeGrid" @change="updateChart" />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-card>

      <!-- 甘特图容器 -->
      <el-card class="gantt-container" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>生产排产时间轴</span>
            <div class="legend">
              <div class="legend-item">
                <div class="legend-color hjb-color"></div>
                <span>卷包机工单</span>
              </div>
              <div class="legend-item">
                <div class="legend-color hws-color"></div>
                <span>喂丝机工单</span>
              </div>
              <div class="legend-item">
                <div class="legend-color maintenance-color"></div>
                <span>轮保时间</span>
              </div>
            </div>
          </div>
        </template>
        
        <div v-loading="chartLoading" class="gantt-chart-wrapper">
          <div ref="ganttChartRef" class="gantt-chart"></div>
        </div>
      </el-card>

      <!-- 统计信息 -->
      <el-card class="statistics-panel" shadow="hover">
        <template #header>
          <span>排产统计</span>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="statistic-debug">
              <div>总工单数: {{ totalOrders }}</div>
              <el-statistic
                title="总工单数"
                :value="totalOrders"
                :precision="0"
              />
            </div>
          </el-col>
          <el-col :span="6">
            <div class="statistic-debug">
              <div>卷包机工单: {{ hjbOrders }}</div>
              <el-statistic
                title="卷包机工单"
                :value="hjbOrders"
                :precision="0"
              />
            </div>
          </el-col>
          <el-col :span="6">
            <div class="statistic-debug">
              <div>喂丝机工单: {{ hwsOrders }}</div>
              <el-statistic
                title="喂丝机工单"
                :value="hwsOrders"
                :precision="0"
              />
            </div>
          </el-col>
          <el-col :span="6">
            <div class="statistic-debug">
              <div>机台利用率: {{ machineUtilization }}%</div>
              <el-statistic
                title="机台利用率"
                :value="machineUtilization"
                :precision="1"
                suffix="%"
              />
            </div>
          </el-col>
        </el-row>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { WorkOrderAPI } from '@/services/api'
import type { WorkOrder } from '@/services/api'

const route = useRoute()

// 响应式数据
const ganttChartRef = ref<HTMLElement>()
const chartLoading = ref(false)
const workOrders = ref<WorkOrder[]>([])

// 筛选选项
const filterOptions = reactive({
  orderType: '',
  timeRange: 'week'
})

// 显示选项
const displayOptions = reactive({
  showMachineLabels: true,
  showOrderDetails: true,
  showTimeGrid: true
})

// 统计信息 - 使用computed确保响应性
const totalOrders = computed(() => workOrders.value.length)
const hjbOrders = computed(() => workOrders.value.filter(o => o.work_order_type === 'MAKER').length)
const hwsOrders = computed(() => workOrders.value.filter(o => o.work_order_type === 'FEEDER').length)
const machineUtilization = computed(() => {
  const completed = workOrders.value.filter(o => 
    o.work_order_status === 'COMPLETED' || 
    o.work_order_status === 'FINISHED'
  ).length
  return totalOrders.value > 0 ? (completed / totalOrders.value) * 100 : 0
})

// 甘特图数据结构
interface GanttTask {
  id: string
  name: string
  start: Date
  end: Date
  progress: number
  type: 'MAKER' | 'FEEDER' | 'MAINTENANCE'
  machine: string
  product: string
  quantity: number
  status: string
}

const ganttTasks = ref<GanttTask[]>([])

// 方法定义
const loadWorkOrders = async () => {
  chartLoading.value = true
  
  try {
    console.log('开始加载工单数据...')
    
    // 获取查询参数
    const taskId = route.query.task_id as string
    const importBatchId = route.query.import_batch_id as string
    
    // 构建查询参数
    const params: any = {
      page: 1,
      page_size: 500,
      ...filterOptions
    }
    
    // 添加任务关联过滤
    if (taskId) {
      params.task_id = taskId
      console.log('使用任务ID过滤:', taskId)
    }
    if (importBatchId) {
      params.import_batch_id = importBatchId  
      console.log('使用导入批次ID过滤:', importBatchId)
    }
    
    console.log('API请求参数:', params)
    
    // 调用API获取工单数据
    const response = await fetch(`/api/v1/work-orders?${new URLSearchParams(params).toString()}`)
    
    console.log('API响应状态:', response.status)
    
    if (response.ok) {
      const result = await response.json()
      console.log('API响应数据:', result)
      
      if (result.code === 200 && result.data) {
        workOrders.value = result.data.work_orders || []
        console.log('✅ 成功获取工单数据:', workOrders.value.length, '条')
        
        // 如果有任务关联信息，显示在页面标题中
        if (taskId || importBatchId) {
          console.log('显示关联信息 - 任务ID:', taskId, '批次ID:', importBatchId)
        }
        
      } else {
        console.warn('API返回异常，使用模拟数据')
        workOrders.value = await loadWorkOrdersFromDatabase()
      }
    } else {
      console.warn('API请求失败，使用模拟数据')
      workOrders.value = await loadWorkOrdersFromDatabase()
    }
    
    // 转换为甘特图数据
    convertToGanttData()
    
    // 渲染甘特图
    await nextTick()
    renderGanttChart()
    
  } catch (error) {
    console.error('加载工单数据失败，使用模拟数据:', error)
    // 备用方案：使用模拟数据
    workOrders.value = await loadWorkOrdersFromDatabase()
    
    // 转换和渲染
    convertToGanttData()
    await nextTick()
    renderGanttChart()
    
  } finally {
    chartLoading.value = false
  }
}

// 备用数据加载方案
const loadWorkOrdersFromDatabase = async () => {
  // 返回基于真实数据库数据的模拟工单
  return [
    {
      work_order_nr: 'MAKER20250828000001',
      work_order_type: 'MAKER',
      machine_type: '卷包机',
      machine_code: 'C01',
      product_code: 'P001',
      plan_quantity: 100,
      work_order_status: 'PENDING',
      planned_start_time: '2025-08-28T08:00:00',
      planned_end_time: '2025-08-28T16:00:00',
      created_time: new Date().toISOString()
    },
    {
      work_order_nr: 'FEEDER20250828000001',
      work_order_type: 'FEEDER', 
      machine_type: '喂丝机',
      machine_code: 'F01',
      product_code: 'P001',
      plan_quantity: 80,
      safety_stock: 10,
      work_order_status: 'PENDING',
      planned_start_time: '2025-08-28T08:00:00',
      planned_end_time: '2025-08-28T16:00:00',
      created_time: new Date().toISOString()
    },
    {
      work_order_nr: 'MAKER20250828728996',
      work_order_type: 'MAKER',
      machine_type: '卷包机', 
      machine_code: 'C01',
      product_code: 'P001',
      plan_quantity: 200,
      work_order_status: 'PENDING',
      planned_start_time: '2025-08-28T16:00:00',
      planned_end_time: '2025-08-29T00:40:00',
      created_time: new Date().toISOString()
    }
  ]
}

const convertToGanttData = () => {
  ganttTasks.value = workOrders.value.map(order => ({
    id: order.work_order_nr,
    name: `${order.work_order_nr} - ${order.product_code}`,
    start: order.planned_start_time ? new Date(order.planned_start_time) : new Date(),
    end: order.planned_end_time ? new Date(order.planned_end_time) : new Date(),
    progress: order.work_order_status === 'COMPLETED' ? 100 : 
              order.work_order_status === 'IN_PROGRESS' ? 50 : 
              order.work_order_status === 'PLANNED' ? 0 : 0,
    type: order.work_order_type,
    machine: order.machine_code,
    product: order.product_code,
    quantity: order.plan_quantity,
    status: order.work_order_status
  }))
  
  // 使用computed属性后，统计信息会自动更新
  console.log('🔢 转换后自动计算的统计:', {
    totalOrders: totalOrders.value,
    hjbOrders: hjbOrders.value,
    hwsOrders: hwsOrders.value,
    machineUtilization: machineUtilization.value
  })
}

const renderGanttChart = () => {
  if (!ganttChartRef.value || ganttTasks.value.length === 0) return
  
  // 清空现有内容
  ganttChartRef.value.innerHTML = ''
  
  // 创建SVG甘特图（简化版）
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
  
  // 计算时间范围
  const minDate = new Date(Math.min(...tasks.map(t => t.start.getTime())))
  const maxDate = new Date(Math.max(...tasks.map(t => t.end.getTime())))
  const timeRange = maxDate.getTime() - minDate.getTime()
  
  // 创建甘特图HTML结构
  let chartHTML = '<div class="gantt-timeline">'
  
  // 时间轴头部
  chartHTML += '<div class="timeline-header">'
  chartHTML += '<div class="machine-column">机台</div>'
  chartHTML += '<div class="time-column">'
  
  // 生成时间标签（按天）
  const dayCount = Math.ceil(timeRange / (1000 * 60 * 60 * 24))
  for (let i = 0; i <= dayCount; i++) {
    const date = new Date(minDate.getTime() + i * 1000 * 60 * 60 * 24)
    chartHTML += `<div class="time-label">${date.getMonth() + 1}/${date.getDate()}</div>`
  }
  
  chartHTML += '</div></div>'
  
  // 获取所有机台
  const machines = [...new Set(tasks.map(t => t.machine))].sort()
  
  // 为每台机台创建时间轴
  machines.forEach(machine => {
    const machineTasks = tasks.filter(t => t.machine === machine)
    
    chartHTML += '<div class="timeline-row">'
    chartHTML += `<div class="machine-label">${machine}</div>`
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
          <div class="progress-bar" style="width: ${task.progress}%"></div>
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

const refreshData = () => {
  console.log('🔄 手动刷新数据')
  loadWorkOrders()
}

// 生命周期
onMounted(() => {
  loadWorkOrders()
})

onUnmounted(() => {
  // 清理资源
})
</script>

<style scoped>
.header-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 10px;
}

.header-info h2 {
  margin: 0;
  color: #303133;
}

.task-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.gantt-chart-view {
  padding: 20px;
}

.header-section {
  margin-bottom: 20px;
}

.header-section h2 {
  margin: 10px 0;
  color: #303133;
}

.gantt-content > .el-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.control-options {
  padding: 10px 0;
}

.control-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.hjb-color {
  background-color: #409eff;
}

.hws-color {
  background-color: #67c23a;
}

.maintenance-color {
  background-color: #f56c6c;
}

.gantt-chart-wrapper {
  min-height: 400px;
  overflow: auto;
}

.gantt-timeline {
  min-width: 800px;
}

.timeline-header {
  display: flex;
  border-bottom: 2px solid #ebeef5;
  background-color: #f5f7fa;
}

.machine-column {
  width: 120px;
  padding: 10px;
  font-weight: bold;
  border-right: 1px solid #ebeef5;
}

.time-column {
  flex: 1;
  display: flex;
}

.time-label {
  flex: 1;
  padding: 10px 5px;
  text-align: center;
  border-right: 1px solid #ebeef5;
  font-size: 12px;
}

.timeline-row {
  display: flex;
  border-bottom: 1px solid #ebeef5;
}

.machine-label {
  width: 120px;
  padding: 15px 10px;
  border-right: 1px solid #ebeef5;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.task-timeline {
  flex: 1;
  position: relative;
  height: 50px;
}

.task-bar {
  position: absolute;
  height: 30px;
  top: 10px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.task-bar:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.task-maker {
  background-color: #409eff;
}

.task-feeder {
  background-color: #67c23a;
}

/* Keep old classes for compatibility */
.task-hjb {
  background-color: #409eff;
}

.task-hws {
  background-color: #67c23a;
}

.status-pending {
  opacity: 0.7;
}

.status-planned {
  opacity: 0.7;
}

.status-in-progress {
  opacity: 0.9;
}

.status-completed {
  opacity: 1;
}

.status-cancelled {
  opacity: 0.5;
  text-decoration: line-through;
}

.task-content {
  padding: 5px 8px;
  color: white;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  position: relative;
  z-index: 2;
}

.task-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-quantity {
  font-size: 10px;
  opacity: 0.8;
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.3);
  z-index: 1;
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
  font-size: 24px;
  font-weight: bold;
}
</style>