<template>
  <div class="task-detail">
    <div class="header-section">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/scheduling/history' }">排产历史</el-breadcrumb-item>
        <el-breadcrumb-item>任务详情</el-breadcrumb-item>
      </el-breadcrumb>
      <div class="header-content">
        <h2>{{ task?.task_name || '排产任务详情' }}</h2>
        <div class="header-actions">
          <el-button 
            v-if="task?.status === 'FAILED'"
            type="warning"
            @click="retryTask"
            :loading="retryLoading"
          >
            重试任务
          </el-button>
          <el-button 
            v-if="['PENDING', 'RUNNING'].includes(task?.status || '')"
            type="danger"
            @click="cancelTask"
            :loading="cancelLoading"
          >
            取消任务
          </el-button>
          <el-button 
            v-if="task?.status === 'COMPLETED'"
            type="primary"
            @click="viewWorkOrders"
          >
            查看工单
          </el-button>
        </div>
      </div>
    </div>

    <div class="detail-content" v-loading="loading">
      <!-- 基本信息 -->
      <el-card class="info-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-tag 
              :type="getTaskStatusType(task?.status)"
              size="large"
            >
              {{ getTaskStatusText(task?.status) }}
            </el-tag>
          </div>
        </template>
        
        <el-descriptions :column="2" border v-if="task">
          <el-descriptions-item label="任务ID">
            <el-text copyable>{{ task.task_id }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="任务名称">
            {{ task.task_name }}
          </el-descriptions-item>
          <el-descriptions-item label="导入批次">
            <el-text copyable>{{ task.import_batch_id }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            {{ task.current_stage }}
          </el-descriptions-item>
          <el-descriptions-item label="执行进度">
            <el-progress 
              :percentage="task.progress" 
              :status="getProgressStatus(task.status)"
              style="width: 200px"
            />
          </el-descriptions-item>
          <el-descriptions-item label="记录统计">
            <div class="record-stats">
              <span>{{ task.processed_records || 0 }} / {{ task.total_records || 0 }}</span>
              <el-progress 
                v-if="task.total_records > 0"
                :percentage="Math.round((task.processed_records || 0) / task.total_records * 100)"
                :stroke-width="4"
                :show-text="false"
                style="width: 100px; margin-left: 10px"
              />
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(task.start_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatDateTime(task.end_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时长">
            {{ formatDuration(task.execution_duration) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(task.created_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建者">
            {{ task.created_by || '系统' }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDateTime(task.updated_time) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 算法配置 -->
      <el-card class="config-card" shadow="hover" v-if="task?.algorithm_config">
        <template #header>
          <span>算法配置</span>
        </template>
        
        <div class="algorithm-config">
          <div class="config-item">
            <el-tag 
              :type="task.algorithm_config.merge_enabled ? 'success' : 'info'" 
              size="large"
            >
              {{ task.algorithm_config.merge_enabled ? '✓' : '✗' }} 规则合并
            </el-tag>
            <p class="config-desc">合并相同条件的生产计划，减少工单数量</p>
          </div>
          <div class="config-item">
            <el-tag 
              :type="task.algorithm_config.split_enabled ? 'success' : 'info'" 
              size="large"
            >
              {{ task.algorithm_config.split_enabled ? '✓' : '✗' }} 规则拆分
            </el-tag>
            <p class="config-desc">按机台能力拆分大批量工单</p>
          </div>
          <div class="config-item">
            <el-tag 
              :type="task.algorithm_config.correction_enabled ? 'success' : 'info'" 
              size="large"
            >
              {{ task.algorithm_config.correction_enabled ? '✓' : '✗' }} 时间校正
            </el-tag>
            <p class="config-desc">根据轮保计划和班次调整时间</p>
          </div>
          <div class="config-item">
            <el-tag 
              :type="task.algorithm_config.parallel_enabled ? 'success' : 'info'" 
              size="large"
            >
              {{ task.algorithm_config.parallel_enabled ? '✓' : '✗' }} 并行处理
            </el-tag>
            <p class="config-desc">确保同工单多机台并行执行</p>
          </div>
        </div>
      </el-card>

      <!-- 错误信息 -->
      <el-card 
        class="error-card" 
        shadow="hover" 
        v-if="task?.error_message"
      >
        <template #header>
          <span>错误信息</span>
        </template>
        
        <el-alert
          :title="task.error_message"
          type="error"
          show-icon
          :closable="false"
        >
          <template #default>
            <div class="error-details">
              <pre>{{ task.error_message }}</pre>
            </div>
          </template>
        </el-alert>
      </el-card>

      <!-- 执行结果 -->
      <el-card 
        class="result-card" 
        shadow="hover" 
        v-if="task?.result_summary"
      >
        <template #header>
          <span>执行结果摘要</span>
        </template>
        
        <div class="result-summary">
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="summary-item">
                <div class="summary-value">{{ task.result_summary.total_work_orders || 0 }}</div>
                <div class="summary-label">总工单数</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="summary-item">
                <div class="summary-value success">{{ task.result_summary.packing_orders_generated || 0 }}</div>
                <div class="summary-label">卷包机工单</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="summary-item">
                <div class="summary-value warning">{{ task.result_summary.feeding_orders_generated || 0 }}</div>
                <div class="summary-label">喂丝机工单</div>
              </div>
            </el-col>
          </el-row>

          <el-divider />

          <div class="execution-summary" v-if="task.result_summary.execution_summary">
            <h4>算法执行摘要</h4>
            <el-descriptions :column="2" size="small">
              <el-descriptions-item 
                v-for="(value, key) in task.result_summary.execution_summary"
                :key="key"
                :label="formatSummaryKey(key)"
              >
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-card>

      <!-- 执行日志 -->
      <el-card class="logs-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>执行日志</span>
            <div class="header-actions">
              <el-button 
                size="small" 
                @click="loadLogs"
                :loading="logsLoading"
              >
                刷新日志
              </el-button>
              <el-tag type="info" size="small">
                共 {{ logs.length }} 条日志
              </el-tag>
            </div>
          </div>
        </template>
        
        <div class="logs-content" v-loading="logsLoading">
          <div v-if="logs.length === 0" class="no-logs">
            暂无执行日志
          </div>
          <div v-else class="logs-list">
            <div 
              v-for="log in logs" 
              :key="log.id"
              class="log-item"
              :class="`log-${log.level.toLowerCase()}`"
            >
              <div class="log-header">
                <el-tag 
                  :type="getLogLevelType(log.level)" 
                  size="small"
                >
                  {{ log.level }}
                </el-tag>
                <span class="log-stage">{{ log.stage }}</span>
                <span class="log-step">{{ log.step_name }}</span>
                <span class="log-time">{{ formatDateTime(log.execution_time) }}</span>
                <span class="log-duration" v-if="log.duration_ms">
                  {{ log.duration_ms }}ms
                </span>
              </div>
              <div class="log-message">{{ log.message }}</div>
              <div v-if="log.processing_data" class="log-data">
                <el-collapse size="small">
                  <el-collapse-item title="处理数据详情">
                    <pre>{{ JSON.stringify(log.processing_data, null, 2) }}</pre>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import httpClient from '@/utils/http'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const logsLoading = ref(false)
const retryLoading = ref(false)
const cancelLoading = ref(false)
const task = ref<any>(null)
const logs = ref<any[]>([])

// 方法定义
const loadTaskDetail = async () => {
  const taskId = route.params.taskId as string
  if (!taskId) {
    ElMessage.error('任务ID参数缺失')
    return
  }

  loading.value = true
  try {
    const response = await httpClient.get(`/api/v1/scheduling/tasks/${taskId}`)
    task.value = response.data.data.task
    logs.value = response.data.data.logs || []
  } catch (error) {
    ElMessage.error('获取任务详情失败')
    console.error('Load task detail error:', error)
  } finally {
    loading.value = false
  }
}

const loadLogs = async () => {
  const taskId = route.params.taskId as string
  if (!taskId) return

  logsLoading.value = true
  try {
    const response = await httpClient.get(`/api/v1/scheduling/tasks/${taskId}`)
    logs.value = response.data.data.logs || []
  } catch (error) {
    ElMessage.error('刷新日志失败')
    console.error('Load logs error:', error)
  } finally {
    logsLoading.value = false
  }
}

const retryTask = async () => {
  if (!task.value) return

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

    retryLoading.value = true
    await httpClient.post(`/api/v1/scheduling/tasks/${task.value.task_id}/retry`)
    ElMessage.success('任务重试已启动')
    await loadTaskDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重试任务失败')
      console.error('Retry task error:', error)
    }
  } finally {
    retryLoading.value = false
  }
}

const cancelTask = async () => {
  if (!task.value) return

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

    cancelLoading.value = true
    await httpClient.post(`/api/v1/scheduling/tasks/${task.value.task_id}/cancel`)
    ElMessage.success('任务已取消')
    await loadTaskDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('取消任务失败')
      console.error('Cancel task error:', error)
    }
  } finally {
    cancelLoading.value = false
  }
}

const viewWorkOrders = () => {
  if (task.value) {
    router.push({
      name: 'GanttChart',
      query: {
        task_id: task.value.task_id,
        import_batch_id: task.value.import_batch_id
      }
    })
  }
}

// 工具方法
const getTaskStatusType = (status?: string) => {
  if (!status) return 'info'
  const statusMap: Record<string, any> = {
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'RUNNING': 'warning',
    'PENDING': 'info',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'info'
}

const getTaskStatusText = (status?: string) => {
  if (!status) return ''
  const statusMap: Record<string, string> = {
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'RUNNING': '运行中',
    'PENDING': '等待中',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const getProgressStatus = (status?: string) => {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED') return 'exception'
  return undefined
}

const getLogLevelType = (level: string) => {
  const levelMap: Record<string, any> = {
    'ERROR': 'danger',
    'WARN': 'warning',
    'INFO': 'success',
    'DEBUG': 'info'
  }
  return levelMap[level] || 'info'
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

const formatSummaryKey = (key: string) => {
  const keyMap: Record<string, string> = {
    'input_records': '输入记录数',
    'output_records': '输出记录数',
    'merge_count': '合并数量',
    'split_count': '拆分数量',
    'correction_count': '校正数量',
    'parallel_count': '并行处理数量'
  }
  return keyMap[key] || key
}

// 生命周期
onMounted(() => {
  loadTaskDetail()
})
</script>

<style scoped>
.task-detail {
  padding: 20px;
}

.header-section {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 10px;
}

.header-content h2 {
  margin: 0;
  color: #303133;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-content > .el-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-stats {
  display: flex;
  align-items: center;
}

.algorithm-config {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.config-item {
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  text-align: center;
}

.config-desc {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #909399;
}

.error-details pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.result-summary {
  padding: 10px 0;
}

.summary-item {
  text-align: center;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.summary-value {
  font-size: 28px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 8px;
}

.summary-value.success {
  color: #67c23a;
}

.summary-value.warning {
  color: #e6a23c;
}

.summary-label {
  font-size: 14px;
  color: #909399;
}

.execution-summary h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.no-logs {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.logs-list {
  max-height: 600px;
  overflow-y: auto;
}

.log-item {
  margin-bottom: 15px;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #dcdfe6;
}

.log-item.log-error {
  background-color: #fef0f0;
  border-left-color: #f56c6c;
}

.log-item.log-warn {
  background-color: #fdf6ec;
  border-left-color: #e6a23c;
}

.log-item.log-info {
  background-color: #f0f9ff;
  border-left-color: #409eff;
}

.log-item.log-debug {
  background-color: #f8f9fa;
  border-left-color: #909399;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
}

.log-stage {
  font-weight: bold;
  color: #606266;
}

.log-step {
  color: #909399;
}

.log-time {
  color: #c0c4cc;
  margin-left: auto;
}

.log-duration {
  color: #c0c4cc;
}

.log-message {
  font-size: 14px;
  line-height: 1.4;
  color: #303133;
}

.log-data {
  margin-top: 10px;
}

.log-data pre {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  max-height: 200px;
  overflow-y: auto;
}
</style>