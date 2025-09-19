<template>
  <div class="monthly-scheduling">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-text">
          <h1>
            <i class="fas fa-calendar-check"></i>
            月度排产管理
          </h1>
          <p class="page-description">
            基于月度计划数据进行智能排产，支持容量分析、约束求解和时间线规划
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" icon="Plus" @click="createNewScheduling">
            新建排产任务
          </el-button>
          <el-button icon="Refresh" @click="refreshData">
            刷新
          </el-button>
        </div>
      </div>
    </div>

    <!-- 快捷操作区域 -->
    <div class="quick-actions">
      <el-card>
        <div class="actions-content">
          <div class="action-group">
            <h3>快捷操作</h3>
            <div class="action-buttons">
              <el-button type="success" icon="Play" @click="showBatchScheduling">
                批量排产
              </el-button>
              <el-button type="warning" icon="Setting" @click="showSchedulingConfig">
                排产配置
              </el-button>
              <el-button type="info" icon="DataAnalysis" @click="showAnalytics">
                排产分析
              </el-button>
            </div>
          </div>
          <div class="filter-group">
            <h3>数据筛选</h3>
            <div class="filter-controls">
              <el-select v-model="filters.status" placeholder="选择状态" clearable>
                <el-option label="全部状态" value="" />
                <el-option label="待排产" value="PENDING" />
                <el-option label="排产中" value="SCHEDULING" />
                <el-option label="已完成" value="COMPLETED" />
                <el-option label="已失败" value="FAILED" />
              </el-select>
              <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                @change="handleDateRangeChange"
              />
              <el-button type="primary" icon="Search" @click="searchSchedulingTasks">
                搜索
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 排产任务列表 -->
    <div class="scheduling-tasks">
      <el-card>
        <template #header>
          <div class="section-header">
            <h3>
              <i class="fas fa-list"></i>
              排产任务列表
            </h3>
            <div class="header-stats">
              <el-tag size="small">共 {{ pagination.total }} 个任务</el-tag>
            </div>
          </div>
        </template>

        <div v-loading="loading">
          <el-table
            :data="schedulingTasks"
            style="width: 100%"
            @selection-change="handleSelectionChange"
            :empty-text="schedulingTasks.length === 0 ? '暂无排产任务' : ''"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="task_id" label="任务ID" width="150">
              <template #default="scope">
                <el-link type="primary" @click="viewTaskDetail(scope.row)">
                  {{ scope.row.task_id }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column prop="batch_id" label="数据批次" width="180">
              <template #default="scope">
                <el-tag size="small" type="info">{{ scope.row.batch_id }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="task_name" label="任务名称" min-width="200">
              <template #default="scope">
                <div class="task-cell">
                  <div class="task-name">{{ scope.row.task_name }}</div>
                  <div class="task-desc">{{ scope.row.description }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="plan_period" label="计划周期" width="120">
              <template #default="scope">
                {{ scope.row.plan_month }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="scope">
                <el-tag
                  :type="getTaskStatusColor(scope.row.status)"
                  size="small"
                >
                  {{ getTaskStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="scope">
                <el-progress
                  :percentage="scope.row.progress || 0"
                  :status="getProgressStatus(scope.row.status)"
                  :stroke-width="6"
                />
              </template>
            </el-table-column>
            <el-table-column prop="created_time" label="创建时间" width="180">
              <template #default="scope">
                {{ formatDateTime(scope.row.created_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="estimated_duration" label="预估用时" width="100">
              <template #default="scope">
                {{ scope.row.estimated_duration || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="scope">
                <div class="action-buttons">
                  <el-button
                    v-if="scope.row.status === 'PENDING'"
                    size="small"
                    type="primary"
                    icon="CaretRight"
                    @click="startScheduling(scope.row)"
                  >
                    开始
                  </el-button>
                  <el-button
                    v-if="scope.row.status === 'SCHEDULING'"
                    size="small"
                    type="warning"
                    icon="VideoPause"
                    @click="pauseScheduling(scope.row)"
                  >
                    暂停
                  </el-button>
                  <el-button
                    v-if="scope.row.status === 'COMPLETED'"
                    size="small"
                    type="success"
                    icon="View"
                    @click="viewResults(scope.row)"
                  >
                    查看结果
                  </el-button>
                  <el-button
                    size="small"
                    type="info"
                    icon="Setting"
                    @click="editTask(scope.row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    icon="Delete"
                    @click="deleteTask(scope.row)"
                  >
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 排产任务详情对话框 -->
    <el-dialog
      v-model="taskDetailVisible"
      title="排产任务详情"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedTask" class="task-detail">
        <div class="detail-sections">
          <!-- 基本信息 -->
          <div class="detail-section">
            <h4>基本信息</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="任务ID">{{ selectedTask.task_id }}</el-descriptions-item>
              <el-descriptions-item label="任务名称">{{ selectedTask.task_name }}</el-descriptions-item>
              <el-descriptions-item label="数据批次">{{ selectedTask.batch_id }}</el-descriptions-item>
              <el-descriptions-item label="计划周期">{{ selectedTask.plan_month }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getTaskStatusColor(selectedTask.status)">
                  {{ getTaskStatusText(selectedTask.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="进度">{{ selectedTask.progress || 0 }}%</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 排产配置 -->
          <div class="detail-section">
            <h4>排产配置</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="排产算法">{{ selectedTask.algorithm_type || '默认算法' }}</el-descriptions-item>
              <el-descriptions-item label="约束条件">{{ selectedTask.constraints_count || 0 }} 个</el-descriptions-item>
              <el-descriptions-item label="优化目标">{{ selectedTask.optimization_target || '最小化总工时' }}</el-descriptions-item>
              <el-descriptions-item label="时间粒度">{{ selectedTask.time_granularity || '小时' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 执行日志 -->
          <div class="detail-section">
            <h4>执行日志</h4>
            <div class="log-container">
              <div v-for="log in selectedTask.execution_logs" :key="log.timestamp" class="log-entry">
                <span class="log-time">{{ formatDateTime(log.timestamp) }}</span>
                <span :class="['log-level', log.level.toLowerCase()]">{{ log.level }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="taskDetailVisible = false">关闭</el-button>
          <el-button v-if="selectedTask?.status === 'COMPLETED'" type="primary" @click="downloadResults">
            下载结果
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 新建排产任务对话框 -->
    <el-dialog
      v-model="createTaskVisible"
      title="新建月度排产任务"
      width="60%"
      :close-on-click-modal="false"
    >
      <el-form
        ref="taskFormRef"
        :model="taskForm"
        :rules="taskFormRules"
        label-width="120px"
      >
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="数据批次" prop="batch_id">
          <el-select v-model="taskForm.batch_id" placeholder="选择月度计划批次" style="width: 100%">
            <el-option
              v-for="batch in availableBatches"
              :key="batch.batch_id"
              :label="`${batch.batch_id} (${batch.file_name})`"
              :value="batch.batch_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划周期" prop="plan_month">
          <el-date-picker
            v-model="taskForm.plan_month"
            type="month"
            placeholder="选择计划月份"
            format="YYYY年MM月"
            value-format="YYYY-MM"
          />
        </el-form-item>
        <el-form-item label="排产算法" prop="algorithm_type">
          <el-select v-model="taskForm.algorithm_type" placeholder="选择排产算法">
            <el-option label="约束求解算法" value="CONSTRAINT_SOLVER" />
            <el-option label="遗传算法" value="GENETIC_ALGORITHM" />
            <el-option label="模拟退火算法" value="SIMULATED_ANNEALING" />
          </el-select>
        </el-form-item>
        <el-form-item label="优化目标" prop="optimization_target">
          <el-select v-model="taskForm.optimization_target" placeholder="选择优化目标">
            <el-option label="最小化总工时" value="MIN_TOTAL_TIME" />
            <el-option label="最大化设备利用率" value="MAX_UTILIZATION" />
            <el-option label="最小化切换次数" value="MIN_SWITCHES" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务描述" prop="description">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务描述"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="createTaskVisible = false">取消</el-button>
          <el-button type="primary" @click="submitTask" :loading="submitting">
            创建任务
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const schedulingTasks = ref<any[]>([])
const selectedTasks = ref<any[]>([])
const selectedTask = ref<any>(null)
const availableBatches = ref<any[]>([])

// 对话框状态
const taskDetailVisible = ref(false)
const createTaskVisible = ref(false)

// 筛选条件
const filters = reactive({
  status: '',
  dateRange: [] as string[]
})

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 新建任务表单
const taskForm = reactive({
  task_name: '',
  batch_id: '',
  plan_month: '',
  algorithm_type: 'CONSTRAINT_SOLVER',
  optimization_target: 'MIN_TOTAL_TIME',
  description: ''
})

const taskFormRef = ref()
const taskFormRules = {
  task_name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' }
  ],
  batch_id: [
    { required: true, message: '请选择数据批次', trigger: 'change' }
  ],
  plan_month: [
    { required: true, message: '请选择计划周期', trigger: 'change' }
  ]
}

// 生命周期
onMounted(() => {
  // 检查URL参数
  const batchId = route.query.batch_id as string
  if (batchId) {
    taskForm.batch_id = batchId
  }
  
  loadSchedulingTasks()
  loadAvailableBatches()
})

// 方法
const loadSchedulingTasks = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    
    if (filters.status) {
      params.status = filters.status
    }
    
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }

    const response = await api.get('/api/v1/monthly-scheduling/tasks', { params })
    
    if (response.data.code === 200) {
      schedulingTasks.value = response.data.data.tasks || []
      pagination.total = response.data.data.pagination?.total_count || 0
    }
  } catch (error) {
    console.error('加载排产任务失败:', error)
    ElMessage.error('加载排产任务失败')
  } finally {
    loading.value = false
  }
}

const loadAvailableBatches = async () => {
  try {
    const response = await api.get('/api/v1/monthly-data/imports', {
      params: {
        status: 'COMPLETED',
        page_size: 100
      }
    })
    
    if (response.data.code === 200) {
      availableBatches.value = response.data.data.imports || []
    }
  } catch (error) {
    console.error('加载可用批次失败:', error)
  }
}

const refreshData = () => {
  loadSchedulingTasks()
  loadAvailableBatches()
}

const searchSchedulingTasks = () => {
  pagination.page = 1
  loadSchedulingTasks()
}

const handleDateRangeChange = () => {
  searchSchedulingTasks()
}

// 任务操作
const createNewScheduling = () => {
  createTaskVisible.value = true
}

const viewTaskDetail = (task: any) => {
  selectedTask.value = { 
    ...task,
    execution_logs: [
      { timestamp: '2024-01-15T10:00:00', level: 'INFO', message: '任务创建成功' },
      { timestamp: '2024-01-15T10:01:00', level: 'INFO', message: '开始数据预处理' },
      { timestamp: '2024-01-15T10:05:00', level: 'INFO', message: '容量分析完成' },
      { timestamp: '2024-01-15T10:10:00', level: 'INFO', message: '约束求解中...' }
    ]
  }
  taskDetailVisible.value = true
}

const startScheduling = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确认开始执行排产任务 "${task.task_name}"?`,
      '确认操作',
      { type: 'warning' }
    )
    
    const response = await api.post(`/api/v1/monthly-scheduling/tasks/${task.task_id}/start`)
    
    if (response.data.code === 200) {
      ElMessage.success('排产任务已开始执行')
      loadSchedulingTasks()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('启动排产任务失败')
    }
  }
}

const pauseScheduling = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确认暂停排产任务 "${task.task_name}"?`,
      '确认操作',
      { type: 'warning' }
    )
    
    const response = await api.post(`/api/v1/monthly-scheduling/tasks/${task.task_id}/pause`)
    
    if (response.data.code === 200) {
      ElMessage.success('排产任务已暂停')
      loadSchedulingTasks()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('暂停排产任务失败')
    }
  }
}

const viewResults = (task: any) => {
  router.push(`/monthly-scheduling/results/${task.task_id}`)
}

const editTask = (task: any) => {
  Object.assign(taskForm, task)
  createTaskVisible.value = true
}

const deleteTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确认删除排产任务 "${task.task_name}"? 此操作不可撤销。`,
      '危险操作',
      { type: 'error' }
    )
    
    const response = await api.delete(`/api/v1/monthly-scheduling/tasks/${task.task_id}`)
    
    if (response.data.code === 200) {
      ElMessage.success('排产任务已删除')
      loadSchedulingTasks()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除排产任务失败')
    }
  }
}

const submitTask = async () => {
  try {
    await taskFormRef.value?.validate()
    
    submitting.value = true
    const response = await api.post('/api/v1/monthly-scheduling/tasks', taskForm)
    
    if (response.data.code === 200) {
      ElMessage.success('排产任务创建成功')
      createTaskVisible.value = false
      loadSchedulingTasks()
      
      // 重置表单
      Object.assign(taskForm, {
        task_name: '',
        batch_id: '',
        plan_month: '',
        algorithm_type: 'CONSTRAINT_SOLVER',
        optimization_target: 'MIN_TOTAL_TIME',
        description: ''
      })
    }
  } catch (error) {
    ElMessage.error('创建排产任务失败')
  } finally {
    submitting.value = false
  }
}

// 批量操作
const showBatchScheduling = () => {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要批量操作的任务')
    return
  }
  ElMessage.info('批量排产功能开发中...')
}

const showSchedulingConfig = () => {
  ElMessage.info('排产配置功能开发中...')
}

const showAnalytics = () => {
  ElMessage.info('排产分析功能开发中...')
}

const downloadResults = () => {
  ElMessage.info('结果下载功能开发中...')
}

// 表格操作
const handleSelectionChange = (selection: any[]) => {
  selectedTasks.value = selection
}

const handleSizeChange = (val: number) => {
  pagination.pageSize = val
  loadSchedulingTasks()
}

const handleCurrentChange = (val: number) => {
  pagination.page = val
  loadSchedulingTasks()
}

// 辅助方法
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

const getTaskStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'PENDING': 'info',
    'SCHEDULING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'PAUSED': 'warning'
  }
  return colors[status] || 'info'
}

const getTaskStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'PENDING': '待排产',
    'SCHEDULING': '排产中',
    'COMPLETED': '已完成',
    'FAILED': '已失败',
    'PAUSED': '已暂停'
  }
  return texts[status] || status
}

const getProgressStatus = (status: string) => {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED') return 'exception'
  return undefined
}
</script>

<style scoped>
.monthly-scheduling {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-text h1 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 28px;
  font-weight: 600;
}

.header-text h1 i {
  margin-right: 10px;
  color: #409eff;
}

.page-description {
  color: #7f8c8d;
  font-size: 16px;
  margin: 0;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.quick-actions {
  margin-bottom: 32px;
}

.actions-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

.action-group, .filter-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-group h3, .filter-group h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.scheduling-tasks {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.section-header h3 i {
  margin-right: 8px;
  color: #409eff;
}

.header-stats {
  display: flex;
  gap: 8px;
}

.task-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-weight: 500;
  color: #303133;
}

.task-desc {
  font-size: 12px;
  color: #909399;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.task-detail {
  max-height: 600px;
  overflow-y: auto;
}

.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.log-container {
  max-height: 200px;
  overflow-y: auto;
  background: #f8f9fa;
  border-radius: 4px;
  padding: 12px;
}

.log-entry {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12px;
}

.log-time {
  color: #909399;
  min-width: 120px;
}

.log-level {
  min-width: 50px;
  font-weight: 500;
}

.log-level.info {
  color: #409eff;
}

.log-level.warning {
  color: #e6a23c;
}

.log-level.error {
  color: #f56c6c;
}

.log-message {
  color: #303133;
  flex: 1;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .monthly-scheduling {
    padding: 16px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .actions-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .action-buttons, .filter-controls {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
  
  .section-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .task-cell .action-buttons {
    flex-direction: column;
    width: 100%;
  }
}
</style>