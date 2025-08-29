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
        <el-form-item label="批次ID">
          <el-input 
            v-model="filterOptions.import_batch_id" 
            placeholder="输入批次ID"
            clearable 
            @change="fetchWorkOrders"
          />
        </el-form-item>
        <el-form-item label="工单类型">
          <el-select 
            v-model="filterOptions.order_type" 
            placeholder="选择类型"
            clearable
            @change="fetchWorkOrders"
          >
            <el-option label="全部" value="" />
            <el-option label="卷包机工单" value="MAKER" />
            <el-option label="喂丝机工单" value="FEEDER" />
          </el-select>
        </el-form-item>
        <el-form-item label="机台">
          <el-input 
            v-model="filterOptions.machine_code" 
            placeholder="输入机台代码"
            clearable 
            @change="fetchWorkOrders"
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- 统计信息 -->
    <div class="statistics-bar" v-if="!loading && workOrders.length > 0">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总工单数" :value="workOrders.length" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="卷包机工单" :value="makerOrdersCount" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="喂丝机工单" :value="feederOrdersCount" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总计划产量" :value="totalQuantity" />
        </el-col>
      </el-row>
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

        <!-- 甘特图内容 -->
        <div v-else class="gantt-chart" ref="ganttChartRef">
          <!-- 甘特图将在这里渲染 -->
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Loading } from '@element-plus/icons-vue'
import { WorkOrderAPI } from '@/services/api'
import * as echarts from 'echarts'

// 路由信息
const route = useRoute()

// 响应式数据
const loading = ref(false)
const error = ref<string | null>(null)
const ganttChartRef = ref<HTMLElement | null>(null)
const workOrders = ref<WorkOrder[]>([])
let chartInstance: echarts.ECharts | null = null

// 筛选条件
const filterOptions = ref({
  task_id: (route.query.task_id as string) || '',
  import_batch_id: (route.query.import_batch_id as string) || '',
  order_type: '',
  machine_code: ''
})

// 工单数据接口（根据实际API返回结构定义）
interface WorkOrder {
  work_order_nr: string
  work_order_type: 'MAKER' | 'FEEDER'
  machine_type: '卷包机' | '喂丝机'
  machine_code: string
  product_code: string
  plan_quantity: number
  safety_stock?: number
  work_order_status: string
  planned_start_time: string | null
  planned_end_time: string | null
  actual_start_time?: string | null
  actual_end_time?: string | null
  created_time?: string | null
  updated_time?: string | null
}

// 甘特图数据接口
interface GanttTask {
  id: string
  name: string
  machine: string
  start: Date
  end: Date
  quantity: number
  status: string
  type: 'MAKER' | 'FEEDER'
  progress: number
}

const ganttTasks = ref<GanttTask[]>([])

// 计算属性
const makerOrdersCount = computed(() => 
  workOrders.value.filter(order => order.work_order_type === 'MAKER').length
)

const feederOrdersCount = computed(() => 
  workOrders.value.filter(order => order.work_order_type === 'FEEDER').length
)

const totalQuantity = computed(() => 
  workOrders.value.reduce((total, order) => total + (order.plan_quantity || 0), 0)
)

// 转换API数据为甘特图任务格式
const transformToGanttTasks = (orders: WorkOrder[]): GanttTask[] => {
  console.log('🔄 转换工单数据为甘特图任务:', orders.length, '个工单')
  
  return orders.map(order => {
    // 解析时间
    let startTime: Date
    let endTime: Date
    
    if (order.planned_start_time) {
      startTime = new Date(order.planned_start_time)
    } else {
      // 默认时间
      startTime = new Date()
    }
    
    if (order.planned_end_time) {
      endTime = new Date(order.planned_end_time)
    } else {
      // 默认结束时间为开始时间后8小时
      endTime = new Date(startTime.getTime() + 8 * 60 * 60 * 1000)
    }
    
    // 确保时间有效
    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      console.warn('⚠️ 无效时间数据:', order.work_order_nr, order.planned_start_time, order.planned_end_time)
      // 使用当前时间作为默认
      const now = new Date()
      startTime = now
      endTime = new Date(now.getTime() + 8 * 60 * 60 * 1000)
    }
    
    // 计算进度（基于状态）
    let progress = 0
    const status = order.work_order_status.toLowerCase()
    if (status.includes('completed')) {
      progress = 100
    } else if (status.includes('progress') || status.includes('running')) {
      progress = 50
    }
    
    const task: GanttTask = {
      id: order.work_order_nr,
      name: `${order.work_order_nr} - ${order.product_code}`,
      machine: order.machine_code,
      start: startTime,
      end: endTime,
      quantity: order.plan_quantity,
      status: status,
      type: order.work_order_type,
      progress: progress
    }
    
    return task
  })
}

// 获取工单数据
const fetchWorkOrders = async () => {
  loading.value = true
  error.value = null
  
  try {
    console.log('🔍 获取工单数据，查询参数:', filterOptions.value)
    
    // 构建查询参数
    const params: any = {
      page: 1,
      page_size: 1000 // 增加页面大小以获取更多数据
    }
    
    // 添加筛选条件
    if (filterOptions.value.task_id) {
      params.task_id = filterOptions.value.task_id
    }
    if (filterOptions.value.import_batch_id) {
      params.import_batch_id = filterOptions.value.import_batch_id
    }
    if (filterOptions.value.order_type) {
      params.order_type = filterOptions.value.order_type
    }
    if (filterOptions.value.machine_code) {
      params.machine_code = filterOptions.value.machine_code
    }
    
    // 使用正确的API调用
    const response = await WorkOrderAPI.getWorkOrders(params)
    
    console.log('✅ API响应:', {
      code: response.code,
      message: response.message,
      total_count: response.data?.total_count,
      work_orders_count: response.data?.work_orders?.length
    })
    
    if (response.code === 200 && response.data?.work_orders) {
      workOrders.value = response.data.work_orders as WorkOrder[]
      console.log('📦 工单数据样本:', workOrders.value.slice(0, 2))
      
      ganttTasks.value = transformToGanttTasks(workOrders.value)
      
      console.log('🎯 转换后的甘特图任务数量:', ganttTasks.value.length)
      
      // 自动渲染甘特图
      await nextTick()
      setTimeout(() => {
        renderGanttChart()
      }, 100) // 延迟渲染确保DOM完全更新
    } else {
      console.warn('⚠️ 无工单数据或响应格式错误')
      workOrders.value = []
      ganttTasks.value = []
      setTimeout(() => {
        renderGanttChart()
      }, 100)
    }
    
  } catch (err) {
    console.error('❌ 获取工单数据失败:', err)
    error.value = err instanceof Error ? err.message : '获取数据失败'
    workOrders.value = []
    ganttTasks.value = []
  } finally {
    loading.value = false
  }
}

// 渲染ECharts甘特图
const renderGanttChart = () => {
  console.log('🔍 检查甘特图容器元素...', {
    ganttChartRef: !!ganttChartRef.value,
    element: ganttChartRef.value
  })
  
  if (!ganttChartRef.value) {
    console.error('❌ 甘特图容器元素不存在')
    // 尝试通过选择器直接获取
    const container = document.querySelector('.gantt-chart')
    if (container) {
      console.log('✅ 通过选择器找到容器元素，继续渲染')
      ganttChartRef.value = container as HTMLElement
    } else {
      console.error('❌ 无法找到甘特图容器元素')
      return
    }
  }
  
  console.log('🎨 开始渲染ECharts甘特图...')
  console.log('📋 任务数据数量:', ganttTasks.value.length)
  
  const container = ganttChartRef.value
  const tasks = ganttTasks.value
  
  if (tasks.length === 0) {
    console.warn('⚠️ 没有任务数据，显示空状态')
    container.innerHTML = '<div class="no-data">暂无工单数据，请先选择排产任务或批次</div>'
    return
  }
  
  // 销毁现有图表实例
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  
  // 创建ECharts实例
  chartInstance = echarts.init(container)
  
  // 生成甘特图配置
  const option = createGanttChartOption(tasks)
  
  // 渲染图表
  chartInstance.setOption(option)
  
  // 添加点击事件
  chartInstance.on('click', (params: any) => {
    if (params.data && params.data.taskInfo) {
      const task = params.data.taskInfo
      ElMessage.info(`工单详情: ${task.id} - ${task.product} (${task.quantity}件)`)
    }
  })
  
  console.log('✅ ECharts甘特图渲染完成')
}

// 创建ECharts甘特图配置
const createGanttChartOption = (tasks: GanttTask[]) => {
  console.log('🎯 开始生成ECharts甘特图配置...')
  
  // 按机台分组
  const machineGroups = tasks.reduce((acc, task) => {
    const machineKey = `${task.machine} (${task.type === 'MAKER' ? '卷包机' : '喂丝机'})`
    if (!acc[machineKey]) {
      acc[machineKey] = {
        type: task.type,
        tasks: []
      }
    }
    acc[machineKey].tasks.push(task)
    return acc
  }, {} as Record<string, { type: string, tasks: GanttTask[] }>)

  // 获取所有机台名称
  const machines = Object.keys(machineGroups)
  
  // 计算时间范围
  const minTime = Math.min(...tasks.map(t => t.start.getTime()))
  const maxTime = Math.max(...tasks.map(t => t.end.getTime()))
  
  console.log('⏰ 时间范围:', {
    minTime: new Date(minTime).toISOString(),
    maxTime: new Date(maxTime).toISOString(),
    machines: machines.length
  })

  // 生成系列数据
  const series: any[] = []
  
  machines.forEach((machine, machineIndex) => {
    const group = machineGroups[machine]
    const taskData = group.tasks.map(task => {
      return {
        name: task.id,
        value: [
          machineIndex,
          task.start.getTime(),
          task.end.getTime(),
          task.end.getTime() - task.start.getTime()
        ],
        itemStyle: {
          color: task.type === 'MAKER' ? '#409eff' : '#67c23a'
        },
        taskInfo: {
          id: task.id,
          product: task.name.split(' - ')[1] || task.name,
          quantity: task.quantity,
          machine: task.machine,
          type: task.type,
          start: task.start.toLocaleString(),
          end: task.end.toLocaleString()
        }
      }
    })

    series.push({
      name: machine,
      type: 'custom',
      renderItem: renderGanttItem,
      encode: {
        x: [1, 2],
        y: 0
      },
      data: taskData
    })
  })

  const option = {
    title: {
      text: '生产甘特图',
      left: 'center',
      textStyle: {
        fontSize: 16,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.data && params.data.taskInfo) {
          const task = params.data.taskInfo
          const duration = Math.round((params.data.value[3]) / (1000 * 60 * 60) * 10) / 10
          return `
            <div>
              <strong>${task.id}</strong><br/>
              产品: ${task.product}<br/>
              机台: ${task.machine} (${task.type === 'MAKER' ? '卷包机' : '喂丝机'})<br/>
              数量: ${task.quantity} 件<br/>
              时长: ${duration} 小时<br/>
              开始: ${task.start}<br/>
              结束: ${task.end}
            </div>
          `
        }
        return ''
      }
    },
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'weakFilter',
        height: 20,
        bottom: 0,
        start: 0,
        end: 100,
        handleIcon: 'path://M10.7,11.9H9.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4h1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7v-1.2h6.6z M13.3,22H6.7v-1.2h6.6z M13.3,19.6H6.7v-1.2h6.6z'
      },
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'weakFilter'
      }
    ],
    grid: {
      left: 150,
      right: 60,
      top: 80,
      bottom: 60
    },
    xAxis: {
      type: 'time',
      position: 'top',
      splitLine: {
        lineStyle: {
          color: ['#E9EDFF']
        }
      },
      axisLine: {
        show: false
      },
      axisTick: {
        lineStyle: {
          color: '#929ABA'
        }
      },
      axisLabel: {
        color: '#929ABA',
        formatter: (value: number) => {
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
        }
      }
    },
    yAxis: {
      type: 'category',
      data: machines,
      axisTick: {
        show: false
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: '#929ABA',
        formatter: (value: string) => {
          // 截取机台名称，避免过长
          return value.length > 15 ? value.substring(0, 15) + '...' : value
        }
      }
    },
    series: series
  }

  return option
}

// ECharts自定义渲染函数
const renderGanttItem = (params: any, api: any) => {
  const categoryIndex = api.value(0)
  const start = api.coord([api.value(1), categoryIndex])
  const end = api.coord([api.value(2), categoryIndex])
  const height = api.size([0, 1])[1] * 0.6

  const rectShape = echarts.graphic.clipRectByRect({
    x: start[0],
    y: start[1] - height / 2,
    width: end[0] - start[0],
    height: height
  }, {
    x: params.coordSys.x,
    y: params.coordSys.y,
    width: params.coordSys.width,
    height: params.coordSys.height
  })

  return rectShape && {
    type: 'rect',
    transition: ['shape'],
    shape: rectShape,
    style: {
      fill: params.data?.itemStyle?.color || '#409eff',
      stroke: params.data?.itemStyle?.color || '#409eff',
      lineWidth: 1,
      opacity: 0.8
    }
  }
}

// 刷新数据
const refreshData = () => {
  fetchWorkOrders()
}

// 生命周期钩子
onMounted(() => {
  console.log('📊 甘特图页面已挂载')
  fetchWorkOrders()
})

onUnmounted(() => {
  // 销毁ECharts实例
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.gantt-chart-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.filter-bar {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.statistics-bar {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.main-content {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.gantt-container {
  min-height: 400px;
}

.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  flex-direction: column;
  gap: 12px;
}

.gantt-chart {
  width: 100%;
  height: 600px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #909399;
  font-size: 14px;
  background: #f9f9f9;
  border-radius: 8px;
}
</style>