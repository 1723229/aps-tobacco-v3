<template>
  <div class="scheduling-history">
    <div class="header-section">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>排产管理</el-breadcrumb-item>
        <el-breadcrumb-item>排产历史</el-breadcrumb-item>
      </el-breadcrumb>
      <h2>排产任务历史</h2>
    </div>

    <div class="history-content">
      <!-- 查询条件 -->
      <el-card class="filter-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>查询条件</span>
            <div class="header-actions">
              <el-button 
                type="primary" 
                size="small"
                @click="searchTasks"
                :loading="loading"
              >
                查询
              </el-button>
              <el-button 
                size="small"
                @click="resetFilters"
              >
                重置
              </el-button>
            </div>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="任务状态">
              <el-select 
                v-model="filters.status" 
                placeholder="请选择状态"
                clearable
              >
                <el-option label="等待中" value="PENDING" />
                <el-option label="运行中" value="RUNNING" />
                <el-option label="已完成" value="COMPLETED" />
                <el-option label="失败" value="FAILED" />
                <el-option label="已取消" value="CANCELLED" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="导入批次">
              <el-input 
                v-model="filters.import_batch_id" 
                placeholder="输入批次ID"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="filters.start_date"
                type="datetime"
                placeholder="选择开始时间"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="filters.end_date"
                type="datetime"
                placeholder="选择结束时间"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 任务列表 -->
      <el-card class="tasks-list-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>排产任务列表</span>
            <el-tag type="info" size="large">
              共 {{ pagination.total_count }} 条记录
            </el-tag>
          </div>
        </template>
        
        <el-table 
          :data="tasks" 
          :loading="loading"
          style="width: 100%"
          @row-click="viewTaskDetail"
          row-class-name="task-row"
        >
          <el-table-column prop="task_id" label="任务ID" width="200" />
          <el-table-column prop="task_name" label="任务名称" width="200" />
          <el-table-column prop="import_batch_id" label="导入批次" width="180" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag 
                :type="getTaskStatusType(row.status)"
                size="small"
              >
                {{ getTaskStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="current_stage" label="当前阶段" width="120" />
          <el-table-column label="进度" width="120">
            <template #default="{ row }">
              <el-progress 
                :percentage="row.progress" 
                :status="getProgressStatus(row.status)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="记录统计" width="120">
            <template #default="{ row }">
              {{ row.processed_records || 0 }} / {{ row.total_records || 0 }}
            </template>
          </el-table-column>
          <el-table-column label="执行时长" width="100">
            <template #default="{ row }">
              {{ formatDuration(row.execution_duration) }}
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column label="结束时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.end_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button 
                type="primary" 
                size="small"
                @click.stop="viewTaskDetail(row)"
              >
                详情
              </el-button>
              <el-button 
                v-if="row.status === 'FAILED'"
                type="warning" 
                size="small"
                @click.stop="retryTask(row)"
              >
                重试
              </el-button>
              <el-button 
                v-if="['PENDING', 'RUNNING'].includes(row.status)"
                type="danger" 
                size="small"
                @click.stop="cancelTask(row)"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total_count"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="onPageSizeChange"
            @current-change="onPageChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="taskDetailVisible"
      title="排产任务详情"
      width="80%"
      :before-close="closeTaskDetail"
    >
      <div v-if="selectedTask" class="task-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">
            {{ selectedTask.task_id }}
          </el-descriptions-item>
          <el-descriptions-item label="任务名称">
            {{ selectedTask.task_name }}
          </el-descriptions-item>
          <el-descriptions-item label="导入批次">
            {{ selectedTask.import_batch_id }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getTaskStatusType(selectedTask.status)">
              {{ getTaskStatusText(selectedTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            {{ selectedTask.current_stage }}
          </el-descriptions-item>
          <el-descriptions-item label="进度">
            <el-progress 
              :percentage="selectedTask.progress" 
              :status="getProgressStatus(selectedTask.status)"
            />
          </el-descriptions-item>
          <el-descriptions-item label="记录统计">
            {{ selectedTask.processed_records || 0 }} / {{ selectedTask.total_records || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时长">
            {{ formatDuration(selectedTask.execution_duration) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(selectedTask.start_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatDateTime(selectedTask.end_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(selectedTask.created_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="算法配置">
            <div class="algorithm-config">
              <el-tag 
                v-if="selectedTask.algorithm_config?.merge_enabled" 
                type="success" 
                size="small"
              >
                合并
              </el-tag>
              <el-tag 
                v-if="selectedTask.algorithm_config?.split_enabled" 
                type="success" 
                size="small"
              >
                拆分
              </el-tag>
              <el-tag 
                v-if="selectedTask.algorithm_config?.correction_enabled" 
                type="success" 
                size="small"
              >
                校正
              </el-tag>
              <el-tag 
                v-if="selectedTask.algorithm_config?.parallel_enabled" 
                type="success" 
                size="small"
              >
                并行
              </el-tag>
            </div>
          </el-descriptions-item>
        </el-descriptions>

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

        <!-- 结果摘要 -->
        <div v-if="selectedTask.result_summary" class="result-section">
          <h4>执行结果摘要</h4>
          <div class="result-tags">
            <el-tag type="info" class="result-tag">
              总工单数: {{ selectedTask.result_summary.total_work_orders || 0 }}
            </el-tag>
            <el-tag type="success" class="result-tag">
              卷包机工单: {{ selectedTask.result_summary.packing_orders_generated || 0 }}
            </el-tag>
            <el-tag type="warning" class="result-tag">
              喂丝机工单: {{ selectedTask.result_summary.feeding_orders_generated || 0 }}
            </el-tag>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeTaskDetail">关闭</el-button>
          <el-button 
            v-if="selectedTask?.status === 'COMPLETED'"
            type="primary"
            @click="viewWorkOrders"
          >
            查看工单
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import httpClient from '@/utils/http'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const tasks = ref<any[]>([])
const taskDetailVisible = ref(false)
const selectedTask = ref<any>(null)

// 查询条件
const filters = reactive({
  status: '',
  import_batch_id: '',
  start_date: null as Date | null,
  end_date: null as Date | null
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total_count: 0,
  total_pages: 0,
  has_next: false,
  has_prev: false
})

// 方法定义
const searchTasks = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size
    }

    if (filters.status) {
      params.status = filters.status
    }
    if (filters.import_batch_id) {
      params.import_batch_id = filters.import_batch_id
    }
    if (filters.start_date) {
      params.start_date = filters.start_date.toISOString()
    }
    if (filters.end_date) {
      params.end_date = filters.end_date.toISOString()
    }

    const response = await httpClient.get('/api/v1/scheduling/tasks', { params })
    tasks.value = response.data.data.tasks
    
    Object.assign(pagination, response.data.data.pagination)
  } catch (error) {
    ElMessage.error('查询排产任务失败')
    console.error('Search tasks error:', error)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  Object.assign(filters, {
    status: '',
    import_batch_id: '',
    start_date: null,
    end_date: null
  })
  pagination.page = 1
  searchTasks()
}

const onPageChange = (page: number) => {
  pagination.page = page
  searchTasks()
}

const onPageSizeChange = (size: number) => {
  pagination.page_size = size
  pagination.page = 1
  searchTasks()
}

const viewTaskDetail = async (task: any) => {
  try {
    const response = await httpClient.get(`/api/v1/scheduling/tasks/${task.task_id}`)
    selectedTask.value = response.data.data.task
    taskDetailVisible.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
    console.error('View task detail error:', error)
  }
}

const closeTaskDetail = () => {
  taskDetailVisible.value = false
  selectedTask.value = null
}

const retryTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要重试这个失败的排产任务吗？',
      '确认重试',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await httpClient.post(`/api/v1/scheduling/tasks/${task.task_id}/retry`)
    ElMessage.success('任务重试已启动')
    await searchTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重试任务失败')
      console.error('Retry task error:', error)
    }
  }
}

const cancelTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个正在运行的排产任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await httpClient.post(`/api/v1/scheduling/tasks/${task.task_id}/cancel`)
    ElMessage.success('任务已取消')
    await searchTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('取消任务失败')
      console.error('Cancel task error:', error)
    }
  }
}

const viewWorkOrders = () => {
  if (selectedTask.value) {
    router.push({
      name: 'GanttChart',
      query: {
        task_id: selectedTask.value.task_id,
        import_batch_id: selectedTask.value.import_batch_id
      }
    })
    closeTaskDetail()
  }
}

// 工具方法
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

const formatDateTime = (datetime?: string) => {
  if (!datetime) return '--'
  return new Date(datetime).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  searchTasks()
})
</script>

<style scoped>
.scheduling-history {
  padding: 20px;
}

.header-section {
  margin-bottom: 20px;
}

.header-section h2 {
  margin: 10px 0;
  color: #303133;
}

.history-content > .el-card {
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
  gap: 10px;
}

.task-row {
  cursor: pointer;
}

.task-row:hover {
  background-color: #f5f7fa;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.task-detail {
  padding: 10px 0;
}

.algorithm-config .el-tag {
  margin-right: 5px;
}

.error-section,
.result-section {
  margin-top: 20px;
}

.error-section h4,
.result-section h4 {
  margin-bottom: 10px;
  color: #303133;
}

.result-tags .result-tag {
  margin-right: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>