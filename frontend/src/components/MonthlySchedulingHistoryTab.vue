<template>
  <div class="monthly-scheduling-history-tab">
    <!-- 搜索筛选区域 -->
    <el-card class="filter-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>月度排产历史记录筛选 📅</span>
          <el-button type="primary" size="small" @click="loadHistoryData">
            刷新
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select
            v-model="filterOptions.status"
            placeholder="任务状态"
            style="width: 100%"
            clearable
            @change="onFilterChange"
          >
            <el-option label="全部" value="" />
            <el-option label="已完成" value="COMPLETED" />
            <el-option label="运行中" value="RUNNING" />
            <el-option label="等待中" value="PENDING" />
            <el-option label="失败" value="FAILED" />
            <el-option label="已取消" value="CANCELLED" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-date-picker
            v-model="filterOptions.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :span="6">
          <el-input
            v-model="filterOptions.batchId"
            placeholder="月度批次ID"
            clearable
            @change="onFilterChange"
          />
        </el-col>
        <el-col :span="6">
          <el-input
            v-model="filterOptions.taskId"
            placeholder="任务ID"
            clearable
            @change="onFilterChange"
          />
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史记录表格 -->
    <el-card class="history-table-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>月度排产历史记录</span>
          <div class="header-info">
            <el-tag type="info" size="small">
              共 {{ total }} 条记录
            </el-tag>
          </div>
        </div>
      </template>
      
      <el-table 
        v-loading="loading"
        :data="historyData"
        style="width: 100%"
        @row-click="onRowClick"
      >
        <el-table-column prop="task_id" label="任务ID" width="200" show-overflow-tooltip />
        <el-table-column prop="monthly_batch_id" label="月度批次" width="150" show-overflow-tooltip />
        <el-table-column prop="task_name" label="任务名称" min-width="200" show-overflow-tooltip />
        
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="progress" label="进度" width="120" align="center">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.progress" 
              :status="getProgressStatus(row.status)"
              :show-text="false"
            />
            <span class="progress-text">{{ row.progress }}%</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="processed_records" label="处理记录" width="120" align="center">
          <template #default="{ row }">
            {{ row.scheduled_plans }} / {{ row.total_plans }}
          </template>
        </el-table-column>
        
        <el-table-column prop="execution_time" label="执行时长" width="120" align="center">
          <template #default="{ row }">
            {{ formatDuration(row.execution_time) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.start_time) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="end_time" label="结束时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.end_time) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button 
                size="small" 
                type="primary" 
                @click.stop="viewTaskDetail(row)"
              >
                详情
              </el-button>
              <el-button 
                v-if="row.status === 'COMPLETED'"
                size="small" 
                type="success" 
                @click.stop="viewGanttChart(row)"
              >
                甘特图
              </el-button>
              <el-button 
                v-if="row.algorithm_summary"
                size="small" 
                type="info" 
                @click.stop="viewResults(row)"
              >
                结果
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="total"
          :page-sizes="[5, 10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="onPageSizeChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <!-- 任务详情抽屉 -->
    <el-drawer
      v-model="detailDrawer"
      title="月度排产任务详情"
      direction="rtl"
      size="600px"
    >
      <div v-if="selectedTask" class="task-detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">
            {{ selectedTask.task_id }}
          </el-descriptions-item>
          <el-descriptions-item label="任务名称">
            {{ selectedTask.task_name }}
          </el-descriptions-item>
          <el-descriptions-item label="月度批次">
            {{ selectedTask.monthly_batch_id }}
          </el-descriptions-item>
          <el-descriptions-item label="任务状态">
            <el-tag :type="getStatusType(selectedTask.status)">
              {{ getStatusText(selectedTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            {{ selectedTask.current_stage }}
          </el-descriptions-item>
          <el-descriptions-item label="执行进度">
            <el-progress :percentage="selectedTask.progress" />
          </el-descriptions-item>
          <el-descriptions-item label="处理记录">
            {{ selectedTask.scheduled_plans }} / {{ selectedTask.total_plans }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时长">
            {{ formatDuration(selectedTask.execution_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(selectedTask.start_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatDateTime(selectedTask.end_time) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- 算法配置信息 -->
        <div v-if="selectedTask.algorithm_summary" class="algorithm-config-section">
          <h4>算法执行摘要</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="执行算法">
              <div v-if="selectedTask.algorithm_summary.algorithms_used">
                <el-tag 
                  v-for="algorithm in selectedTask.algorithm_summary.algorithms_used" 
                  :key="algorithm"
                  type="success"
                  size="small"
                  style="margin-right: 8px;"
                >
                  {{ algorithm }}
                </el-tag>
              </div>
              <span v-else>--</span>
            </el-descriptions-item>
            <el-descriptions-item label="效率达成">
              {{ selectedTask.algorithm_summary.efficiency_achieved || '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="执行时间">
              {{ formatDuration(selectedTask.algorithm_summary.execution_time) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        
        <!-- 错误信息 -->
        <div v-if="selectedTask.error_message" class="error-section">
          <h4>错误信息</h4>
          <el-alert
            :title="selectedTask.error_message"
            type="error"
            show-icon
            :closable="false"
          />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { MonthlySchedulingAPI } from '@/services/api'
import type { MonthlySchedulingTaskResponse } from '@/services/api'

const router = useRouter()

// Props
interface Props {
  limit?: number
}

const props = withDefaults(defineProps<Props>(), {
  limit: 20
})

// 响应式数据
const loading = ref(false)
const historyData = ref<MonthlySchedulingTaskResponse[]>([])
const total = ref(0)
const detailDrawer = ref(false)
const selectedTask = ref<MonthlySchedulingTaskResponse | null>(null)

// 筛选选项
const filterOptions = reactive({
  status: '',
  dateRange: null as [Date, Date] | null,
  batchId: '',
  taskId: ''
})

// 分页配置
const pagination = reactive({
  page: 1,
  pageSize: props.limit
})

// 方法定义
const loadHistoryData = async () => {
  loading.value = true
  try {
    console.log('📊 加载月度排产历史数据...')
    
    // 构建查询参数
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    
    if (filterOptions.status) {
      params.status = filterOptions.status
    }
    
    if (filterOptions.batchId) {
      params.monthly_batch_id = filterOptions.batchId
    }
    
    if (filterOptions.dateRange && filterOptions.dateRange.length === 2) {
      params.created_after = filterOptions.dateRange[0].toISOString()
      params.created_before = filterOptions.dateRange[1].toISOString()
    }
    
    // 调用月度排产API获取真实数据
    const response = await MonthlySchedulingAPI.getTaskHistory(params)
    
    if (response.code === 200) {
      historyData.value = response.data.tasks || []
      total.value = response.data.pagination?.total_count || 0
      
      console.log('✅ 月度排产历史数据加载完成:', {
        记录数: historyData.value.length,
        总记录数: total.value
      })
    } else {
      throw new Error(response.message || '获取数据失败')
    }
    
  } catch (error: any) {
    console.error('❌ 加载月度排产历史数据失败:', error)
    ElMessage.error(error.message || '加载历史数据失败')
    
    // 如果API调用失败，显示空数据
    historyData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => {
  pagination.page = 1
  loadHistoryData()
}

const onPageChange = (page: number) => {
  pagination.page = page
  loadHistoryData()
}

const onPageSizeChange = (pageSize: number) => {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadHistoryData()
}

const onRowClick = (row: MonthlySchedulingTaskResponse) => {
  viewTaskDetail(row)
}

const viewTaskDetail = (task: MonthlySchedulingTaskResponse) => {
  selectedTask.value = task
  detailDrawer.value = true
}

const viewGanttChart = (task: MonthlySchedulingTaskResponse) => {
  // 跳转到甘特图页面并传递任务信息
  router.push({
    name: 'GanttChart',
    query: {
      task_id: task.task_id,
      monthly_batch_id: task.monthly_batch_id
    }
  })
}

const viewResults = (task: MonthlySchedulingTaskResponse) => {
  ElMessage.info('查看详细结果功能开发中...')
}

// 状态处理方法
const getStatusType = (status: string) => {
  const statusMap: Record<string, any> = {
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'RUNNING': 'warning',
    'PENDING': 'info',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'RUNNING': '运行中',
    'PENDING': '等待中',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const getProgressStatus = (status: string) => {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED') return 'exception'
  return undefined
}

const formatDuration = (duration?: number) => {
  if (!duration) return '--'
  if (duration < 60) return `${duration}秒`
  const minutes = Math.floor(duration / 60)
  const seconds = duration % 60
  return `${minutes}分${seconds}秒`
}

const formatDateTime = (dateTime?: string) => {
  if (!dateTime) return '--'
  try {
    return new Date(dateTime).toLocaleString('zh-CN')
  } catch {
    return dateTime
  }
}

// 生命周期
onMounted(() => {
  loadHistoryData()
})
</script>

<style scoped>
.monthly-scheduling-history-tab {
  padding: 0;
}

.filter-card, .history-table-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-text {
  font-size: 12px;
  color: #606266;
  margin-left: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.task-detail-content {
  padding: 20px;
}

.algorithm-config-section,
.error-section {
  margin-top: 20px;
}

.algorithm-config-section h4,
.error-section h4 {
  margin-bottom: 10px;
  color: #303133;
}
</style>