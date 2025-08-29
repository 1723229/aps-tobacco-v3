<template>
  <div class="scheduling-management">
    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 待排产旬计划列表 -->
      <div class="plans-section">
        <el-card class="plans-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><FolderOpened /></el-icon>
                <div>
                  <h2>待排产旬计划</h2>
                  <p>选择需要排产的导入计划，点击开始排产按钮执行智能算法</p>
                </div>
              </div>
              <div class="header-stats">
                <div class="stat-item">
                  <span class="stat-value">{{ availablePlansCount }}</span>
                  <span class="stat-label">待排产计划</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ runningTasksCount }}</span>
                  <span class="stat-label">进行中</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ completedTasksCount }}</span>
                  <span class="stat-label">已完成</span>
                </div>
              </div>
              <div class="header-actions">
                <el-button 
                  type="primary" 
                  @click="refreshPlans"
                  :loading="plansLoading"
                  class="refresh-btn"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新列表
                </el-button>
                <el-button 
                  @click="$router.push('/decade-plan/entry')"
                  class="upload-btn"
                >
                  <el-icon><Upload /></el-icon>
                  上传新计划
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="plans-content">
            <div v-if="availablePlans.length === 0" class="empty-state">
              <el-icon class="empty-icon"><DocumentRemove /></el-icon>
              <h3>暂无待排产计划</h3>
              <p>请先上传生产计划文件，系统解析完成后即可进行排产</p>
              <el-button type="primary" @click="$router.push('/decade-plan/entry')">
                <el-icon><Upload /></el-icon>
                去上传文件
              </el-button>
            </div>
            
            <div v-else class="plans-table-container">
              <el-table 
                :data="availablePlans" 
                style="width: 100%"
                :loading="plansLoading"
                empty-text="暂无数据"
                @selection-change="handleSelectionChange"
              >
                <el-table-column type="selection" width="55" :selectable="canSelectPlan" />
                
                <el-table-column prop="file_name" label="文件名" min-width="200">
                  <template #default="{ row }">
                    <div class="file-info">
                      <el-icon class="file-icon"><Document /></el-icon>
                      <div>
                        <div class="file-name">{{ row.file_name }}</div>
                        <div class="file-id">批次: {{ row.batch_id.slice(-8) }}</div>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                
                <el-table-column prop="valid_records" label="记录数" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" type="info">{{ row.valid_records }}</el-tag>
                  </template>
                </el-table-column>
                
                <el-table-column prop="import_end_time" label="解析时间" width="160">
                  <template #default="{ row }">
                    {{ formatDateTime(row.import_end_time) }}
                  </template>
                </el-table-column>
                
                <el-table-column label="排产状态" width="120" align="center">
                  <template #default="{ row }">
                    <el-tag :type="getSchedulingStatusType(row)" size="small">
                      {{ getSchedulingStatusText(row) }}
                    </el-tag>
                  </template>
                </el-table-column>
                
                <el-table-column label="操作" width="200" align="center">
                  <template #default="{ row }">
                    <div class="action-buttons">
                      <el-button 
                        v-if="canStartScheduling(row)"
                        type="primary" 
                        size="small"
                        @click="startScheduling(row)"
                        :loading="row.scheduling"
                      >
                        开始排产
                      </el-button>
                      
                      <el-button 
                        v-if="row.scheduling_status === 'pending'"
                        type="info" 
                        size="small"
                        @click="viewSchedulingProgress(row)"
                      >
                        查看任务
                      </el-button>
                      
                      <el-button 
                        v-if="row.scheduling_status === 'running'"
                        type="warning" 
                        size="small"
                        @click="viewSchedulingProgress(row)"
                      >
                        查看进度
                      </el-button>
                      
                      <el-button 
                        v-if="row.scheduling_status === 'completed'"
                        type="success" 
                        size="small"
                        @click="viewGanttChart(row)"
                      >
                        查看甘特图
                      </el-button>
                      
                      <el-button 
                        v-if="row.scheduling_status === 'failed'"
                        type="danger" 
                        size="small"
                        @click="retryScheduling(row)"
                      >
                        重试
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- 分页组件 -->
              <div v-if="availablePlans.length > 0" class="pagination-container">
                <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="totalCount"
                  layout="total, sizes, prev, pager, next, jumper"
                  background
                  @size-change="handleSizeChange"
                  @current-change="handlePageChange"
                />
              </div>
            </div>
          </div>
        </el-card>
      </div>


      <!-- 排产历史记录 -->
      <div class="history-section">
        <el-card class="history-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><Clock /></el-icon>
                <div>
                  <h2>最近排产记录</h2>
                  <p>查看最近的排产任务执行历史</p>
                </div>
              </div>
              <el-button 
                @click="viewAllHistory"
                class="view-all-btn"
              >
                查看全部
                <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          
          <SchedulingHistoryTab :limit="5" />
        </el-card>
      </div>
    </div>
    
    <!-- 算法配置对话框 -->
    <el-dialog
      v-model="algorithmDialogVisible"
      title="算法配置"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="algorithm-config">
        <p class="config-description">选择适合的智能排产算法组合：</p>
        
        <div class="algorithm-options">
          <div v-for="option in algorithmOptions" :key="option.key" class="algorithm-option">
            <div class="option-header">
              <el-switch 
                v-model="algorithmConfig[option.key]"
                class="option-switch"
              />
              <div class="option-info">
                <h3>{{ option.title }}</h3>
                <p>{{ option.description }}</p>
              </div>
            </div>
            <div class="option-tags">
              <el-tag
                v-for="tag in option.tags"
                :key="tag"
                size="small"
                type="info"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="algorithmDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmAlgorithmConfig">确定</el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 排产进度监控弹窗 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="排产进度监控"
      width="80%"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="true"
      @close="closeProgressPanel"
    >
      <div v-if="currentTask" class="dialog-progress-content">
        <div class="progress-header-section">
          <div class="task-info">
            <h3>{{ currentTask.task_name }}</h3>
            <el-tag 
              :type="getTaskStatusType(currentTask.status)"
              size="large"
              class="status-tag"
            >
              {{ getTaskStatusText(currentTask.status) }}
            </el-tag>
          </div>
        </div>
        
        <div class="progress-body">
          <div class="progress-section">
            <div class="progress-header">
              <h4>执行进度</h4>
              <span class="progress-percent">{{ currentTask.progress }}%</span>
            </div>
            <el-progress 
              :percentage="currentTask.progress" 
              :status="getProgressStatus(currentTask.status)"
              stroke-width="8"
              class="progress-bar"
            />
            <div class="progress-details">
              <span>当前阶段: {{ currentTask.current_stage }}</span>
              <span>{{ currentTask.processed_records }} / {{ currentTask.total_records }} 记录</span>
            </div>
          </div>
          
          <div class="task-details">
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">任务ID</span>
                <span class="detail-value">{{ currentTask.task_id.slice(-12) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">批次ID</span>
                <span class="detail-value">{{ currentTask.import_batch_id.slice(-8) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">执行时长</span>
                <span class="detail-value">{{ formatDuration(currentTask.execution_duration) }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="currentTask.error_message" class="error-section">
            <el-alert
              :title="currentTask.error_message"
              type="error"
              show-icon
              :closable="false"
            />
          </div>
          
          <!-- 排产完成结果 -->
          <div v-if="currentTask.status === 'COMPLETED' && currentTask.result_summary" class="result-summary">
            <div class="summary-grid">
              <div class="summary-card">
                <div class="summary-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ currentTask.result_summary.total_work_orders || 0 }}</h3>
                  <p>总工单数</p>
                </div>
              </div>
              <div class="summary-card">
                <div class="summary-icon success">
                  <el-icon><Box /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ currentTask.result_summary.packing_orders_generated || 0 }}</h3>
                  <p>卷包机工单</p>
                </div>
              </div>
              <div class="summary-card">
                <div class="summary-icon warning">
                  <el-icon><Operation /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ currentTask.result_summary.feeding_orders_generated || 0 }}</h3>
                  <p>喂丝机工单</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            v-if="currentTask?.status === 'COMPLETED'"
            type="primary" 
            @click="viewGanttChart(currentTask)"
          >
            <el-icon><TrendCharts /></el-icon>
            查看甘特图
          </el-button>
          <el-button @click="closeProgressPanel">
            关闭
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { SchedulingAPI, DecadePlanAPI } from '@/services/api'
import type { 
  SchedulingAlgorithmConfig, 
  SchedulingTask,
  AvailableBatch
} from '@/services/api'
import { formatDateTime } from '@/utils'
import {
  Operation,
  FolderOpened,
  Refresh,
  DocumentRemove,
  Document,
  ArrowRight,
  Setting,
  VideoPlay,
  TrendCharts,
  Clock,
  RefreshRight,
  Box,
  Upload,
  Close,
  Connection,
  Grid,
  Timer,
  Share
} from '@element-plus/icons-vue'

// 导入子组件
import SchedulingHistoryTab from '@/components/SchedulingHistoryTab.vue'

const router = useRouter()

// 响应式数据
const availablePlans = ref<AvailableBatch[]>([])
const selectedPlans = ref<AvailableBatch[]>([])
const plansLoading = ref(false)
const schedulingLoading = ref(false)
const currentTask = ref<SchedulingTask | null>(null)
const algorithmDialogVisible = ref(false)
const progressDialogVisible = ref(false)
const selectedPlanForScheduling = ref<AvailableBatch | null>(null)
const pollingTimer = ref<number | null>(null)

// 分页相关数据
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)

// 计算统计数据（基于当前页数据）
const availablePlansCount = computed(() => 
  availablePlans.value.filter(p => (p as any).scheduling_status === 'unscheduled' && p.can_schedule).length
)

const runningTasksCount = computed(() => 
  availablePlans.value.filter(p => ['pending', 'running'].includes((p as any).scheduling_status)).length
)

const completedTasksCount = computed(() => 
  availablePlans.value.filter(p => (p as any).scheduling_status === 'completed').length
)

// 算法配置
const algorithmConfig = reactive<SchedulingAlgorithmConfig>({
  merge_enabled: true,
  split_enabled: true,
  correction_enabled: true,
  parallel_enabled: true
})

// 算法选项定义
const algorithmOptions = ref([
  {
    key: 'merge_enabled',
    title: '规则合并',
    description: '合并相同条件的生产计划，减少工单数量',
    icon: 'Connection',
    color: '#67c23a',
    tags: ['效率优化', '减少工单']
  },
  {
    key: 'split_enabled',
    title: '规则拆分',
    description: '按机台能力拆分大批量工单',
    icon: 'Grid',
    color: '#409eff',
    tags: ['负载均衡', '机台优化']
  },
  {
    key: 'correction_enabled',
    title: '时间校正',
    description: '根据轮保计划和班次调整时间',
    icon: 'Timer',
    color: '#e6a23c',
    tags: ['时间优化', '班次调整']
  },
  {
    key: 'parallel_enabled',
    title: '并行处理',
    description: '确保同工单多机台并行执行',
    icon: 'Share',
    color: '#f56c6c',
    tags: ['并行执行', '同步优化']
  }
])

// 计算属性
const canExecuteScheduling = computed(() => {
  return selectedBatchId.value && !schedulingLoading.value
})

const enabledAlgorithmCount = computed(() => {
  return Object.values(algorithmConfig).filter(Boolean).length
})

// 方法定义
const refreshPlans = async () => {
  plansLoading.value = true
  try {
    // 获取分页的历史记录（包含排产状态）
    const historyResponse = await DecadePlanAPI.getUploadHistory(
      currentPage.value,
      pageSize.value, 
      'COMPLETED' // 只获取已解析完成的记录
    )
    
    const allRecords = historyResponse.data.records
    totalCount.value = historyResponse.data.pagination.total_count
    
    // 直接使用后端返回的数据，不需要额外合并
    availablePlans.value = allRecords.map(record => {
      // 修正状态显示逻辑
      let scheduling_status = record.scheduling_status
      let scheduling_text = record.scheduling_text
      
      // 如果没有task_id，说明确实未排产
      if (!record.task_id) {
        scheduling_status = 'unscheduled'
        scheduling_text = record.can_schedule ? '可排产' : '无法排产'
      }
      
      return {
        batch_id: record.batch_id,
        file_name: record.file_name,
        total_records: record.total_records,
        valid_records: record.valid_records,
        import_end_time: record.import_end_time,
        display_name: `${record.file_name} (${record.valid_records}条记录)`,
        can_schedule: record.can_schedule, // 使用后端计算的can_schedule
        scheduling_status: scheduling_status, // 使用修正后的状态
        scheduling_text: scheduling_text, // 使用修正后的文本
        task_id: record.task_id,
        work_orders_summary: record.work_orders_summary || 0
      }
    })
    
    console.log('📊 计划列表状态统计:', {
      total: availablePlans.value.length,
      canSchedule: availablePlansCount.value,
      running: runningTasksCount.value,
      completed: completedTasksCount.value
    })
    
    console.log('📋 详细状态分析:', availablePlans.value.map(p => ({
      file: p.file_name.slice(-20),
      status: (p as any).scheduling_status,
      can_schedule: p.can_schedule,
      task_id: p.task_id ? 'exists' : 'null'
    })))
    
  } catch (error) {
    ElMessage.error('获取计划列表失败')
    console.error('Refresh plans error:', error)
  } finally {
    plansLoading.value = false
  }
}

// 分页相关方法
const handlePageChange = (page: number) => {
  currentPage.value = page
  refreshPlans()
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  refreshPlans()
}

const handleSelectionChange = (selection: AvailableBatch[]) => {
  selectedPlans.value = selection
}

// 排产状态判断方法（修复逻辑）
const canSelectPlan = (row: AvailableBatch) => {
  // 只有未排产的计划才能被选中
  return (row as any).scheduling_status === 'unscheduled'
}

const canStartScheduling = (row: AvailableBatch) => {
  // 只有同时满足两个条件的才能开始排产：
  // 1. 在可排产列表中 (can_schedule = true)
  // 2. 未排产状态 (scheduling_status = 'unscheduled')
  return row.can_schedule && (row as any).scheduling_status === 'unscheduled'
}

const getSchedulingStatusType = (row: AvailableBatch) => {
  const status = (row as any).scheduling_status
  const statusMap: Record<string, any> = {
    'unscheduled': 'info',     // 未排产 - 蓝色
    'pending': 'warning',      // 等待中 - 黄色  
    'running': 'warning',      // 排产中 - 黄色
    'completed': 'success',    // 已完成 - 绿色
    'failed': 'danger',        // 已失败 - 红色
    'cancelled': ''            // 已取消 - 灰色
  }
  return statusMap[status] || 'info'
}

const getSchedulingStatusText = (row: AvailableBatch) => {
  const status = (row as any).scheduling_status
  const canSchedule = row.can_schedule
  
  // 根据排产状态显示正确的文本
  if (status === 'unscheduled') {
    return canSchedule ? '可排产' : '无法排产'
  }
  
  const statusMap: Record<string, string> = {
    'pending': '待排产',
    'running': '排产中', 
    'completed': '已完成',
    'failed': '排产失败',
    'cancelled': '已取消'
  }
  return statusMap[status] || (row as any).scheduling_text || '未知状态'
}

const startScheduling = (plan: AvailableBatch) => {
  selectedPlanForScheduling.value = plan
  algorithmDialogVisible.value = true
}

const confirmAlgorithmConfig = () => {
  algorithmDialogVisible.value = false
  confirmScheduling()
}

const confirmScheduling = async () => {
  if (!selectedPlanForScheduling.value) return
  
  schedulingLoading.value = true
  algorithmDialogVisible.value = false
  
  try {
    const response = await SchedulingAPI.executeScheduling(
      selectedPlanForScheduling.value.batch_id,
      algorithmConfig
    )
    
    ElMessage.success('排产任务已创建')
    
    // 开始轮询任务状态
    await pollTaskStatus(response.data.task_id)
    
    // 刷新计划列表
    await refreshPlans()
    
  } catch (error) {
    ElMessage.error('排产任务创建失败')
    console.error('Execute scheduling error:', error)
  } finally {
    schedulingLoading.value = false
  }
}

const viewSchedulingProgress = (plan: AvailableBatch) => {
  if ((plan as any).task_id) {
    progressDialogVisible.value = true
    pollTaskStatus((plan as any).task_id)
  }
}

const retryScheduling = async (plan: AvailableBatch) => {
  try {
    await ElMessageBox.confirm('确定要重新执行排产吗？', '确认重试', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 重新开始排产
    startScheduling(plan)
  } catch {
    // 用户取消
  }
}

const pollTaskStatus = async (taskId: string) => {
  // 清除之前的轮询
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
  
  const poll = async () => {
    try {
      const response = await SchedulingAPI.getTaskStatus(taskId)
      currentTask.value = response.data
      
      if (response.data.status === 'COMPLETED') {
        ElMessage.success('排产完成！')
        clearInterval(pollingTimer.value!)
        pollingTimer.value = null
        await refreshPlans() // 刷新列表
        // 延迟关闭弹窗，让用户看到完成状态
        setTimeout(() => {
          progressDialogVisible.value = false
        }, 2000)
      } else if (response.data.status === 'FAILED') {
        ElMessage.error('排产失败')
        clearInterval(pollingTimer.value!)
        pollingTimer.value = null
        await refreshPlans() // 刷新列表
      }
    } catch (error) {
      console.error('Poll task status error:', error)
      // 停止轮询如果出错
      if (pollingTimer.value) {
        clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }
    }
  }
  
  // 立即执行一次
  await poll()
  
  // 开始轮询（每3秒）
  if (currentTask.value && ['PENDING', 'RUNNING'].includes(currentTask.value.status)) {
    pollingTimer.value = window.setInterval(poll, 3000)
  }
}

const closeProgressPanel = () => {
  progressDialogVisible.value = false
  currentTask.value = null
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
  refreshPlans() // 刷新列表状态
}

const viewAllHistory = () => {
  router.push('/scheduling/history')
}

const viewGanttChart = (planOrTask: AvailableBatch | SchedulingTask) => {
  let taskId: string | undefined
  let importBatchId: string
  
  if ('task_id' in planOrTask) {
    // SchedulingTask
    taskId = planOrTask.task_id
    importBatchId = planOrTask.import_batch_id
  } else {
    // AvailableBatch with task info
    taskId = (planOrTask as any).task_id
    importBatchId = planOrTask.batch_id
  }
  
  router.push({
    name: 'GanttChart',
    query: {
      ...(taskId && { task_id: taskId }),
      import_batch_id: importBatchId
    }
  })
}

// 清理计时器
const cleanup = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

// 移除旧的批次状态方法，已由新的排产状态方法替代

// 保留任务状态处理方法，用于进度监控
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

// 生命周期
onMounted(() => {
  refreshPlans()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.scheduling-management {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

/* Header统计样式 */
.header-stats {
  display: flex;
  gap: 20px;
  align-items: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 8px;
  color: white;
  min-width: 60px;
}

.stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  color: white;
}

.stat-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
}

/* 计划列表样式 */
.plans-section {
  margin-bottom: 30px;
}

.plans-card {
  border-radius: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.upload-btn {
  border-radius: 8px;
}

.plans-table-container {
  margin-top: 20px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 1.2rem;
  color: #409eff;
}

.file-name {
  font-weight: 600;
  color: #303133;
}

.file-id {
  font-size: 0.8rem;
  color: #909399;
  margin-top: 2px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

/* 进度监控样式 */
.progress-section {
  margin-bottom: 30px;
}

.progress-card {
  border-radius: 16px;
}

.progress-content {
  padding: 20px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.progress-percent {
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #666;
  margin-top: 12px;
}

.task-details {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 0.8rem;
  color: #999;
  text-transform: uppercase;
  font-weight: 500;
}

.detail-value {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.error-section {
  margin: 20px 0;
}

/* 历史记录样式 */
.history-section {
  margin-bottom: 30px;
}

.history-card {
  border-radius: 16px;
}

.view-all-btn {
  border-radius: 8px;
}

/* 算法配置对话框样式 */
.algorithm-config {
  padding: 20px 0;
}

.config-description {
  margin-bottom: 24px;
  color: #606266;
  font-size: 1rem;
}

.algorithm-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.algorithm-option {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
}

.algorithm-option:hover {
  border-color: #c6e2ff;
  background-color: #f0f7ff;
}

.option-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.option-icon {
  font-size: 1.5rem;
  margin-top: 4px;
}

.option-info {
  flex: 1;
}

.option-info h4 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 6px 0;
  color: #303133;
}

.option-info p {
  font-size: 0.9rem;
  color: #606266;
  margin: 0;
  line-height: 1.4;
}

.option-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.algorithm-summary {
  margin-top: 24px;
  text-align: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 主内容区域 */
.main-content {
  max-width: 1200px;
  margin: 0 auto;
}

/* 步骤面板 */
.step-panel {
  margin-bottom: 40px;
}

.step-card {
  background: white;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.step-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.15);
}

.card-header {
  padding: 30px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  font-size: 2rem;
  color: #667eea;
}

.header-content h2 {
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.header-content p {
  font-size: 1rem;
  color: #666;
  margin: 4px 0 0 0;
}

.card-content {
  padding: 40px 30px;
}

/* 批次选择样式 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 4rem;
  color: #ddd;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 1.4rem;
  color: #666;
  margin: 20px 0 10px 0;
}

.empty-state p {
  color: #999;
  margin-bottom: 30px;
}

.batch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.batch-card {
  border: 2px solid #eee;
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.batch-card:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
}

.batch-card.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
}

.batch-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.batch-icon {
  font-size: 1.5rem;
  color: #667eea;
}

.batch-info {
  flex: 1;
}

.batch-info h4 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.batch-info p {
  font-size: 0.9rem;
  color: #666;
  margin: 4px 0 0 0;
}

.batch-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.8rem;
  color: #999;
}

.stat-value {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

/* 算法配置样式 */
.algorithm-summary {
  padding: 8px 16px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 20px;
  color: #667eea;
  font-weight: 500;
}

.algorithm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.algorithm-card {
  border: 2px solid #eee;
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s ease;
  background: white;
}

.algorithm-card.enabled {
  border-color: #67c23a;
  background: linear-gradient(135deg, #f0f9ff 0%, #ecfdf5 100%);
}

.algorithm-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.algorithm-icon {
  font-size: 1.8rem;
  color: #667eea;
}

.algorithm-info {
  flex: 1;
}

.algorithm-info h4 {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #333;
}

.algorithm-info p {
  font-size: 0.95rem;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.algorithm-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 执行排产样式 */
.execute-ready {
  text-align: center;
  padding: 60px 20px;
}

.ready-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 30px;
}

.ready-icon .el-icon {
  font-size: 2.5rem;
  color: white;
}

.execute-ready h3 {
  font-size: 1.6rem;
  color: #333;
  margin: 0 0 12px 0;
}

.execute-ready p {
  color: #666;
  margin-bottom: 40px;
}

.execute-btn {
  padding: 16px 40px;
  font-size: 1.1rem;
  border-radius: 50px;
}

.task-progress {
  max-width: 600px;
  margin: 0 auto;
}

.progress-section {
  margin-bottom: 30px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.progress-header h4 {
  font-size: 1.2rem;
  color: #333;
  margin: 0;
}

.progress-percent {
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.progress-bar {
  margin-bottom: 12px;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #666;
}

.task-details {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 0.8rem;
  color: #999;
  text-transform: uppercase;
  font-weight: 500;
}

.detail-value {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

/* 结果展示样式 */
.result-summary {
  margin-bottom: 40px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.summary-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border-radius: 16px;
  padding: 30px 24px;
  text-align: center;
  border: 1px solid #eee;
}

.summary-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #667eea;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.summary-icon.success {
  background: #67c23a;
}

.summary-icon.warning {
  background: #e6a23c;
}

.summary-icon .el-icon {
  font-size: 1.8rem;
  color: white;
}

.summary-content h3 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: #333;
}

.summary-content p {
  font-size: 1rem;
  color: #666;
  margin: 0;
}

/* 操作按钮样式 */
.step-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 30px;
}

.next-step-action {
  text-align: center;
  padding: 30px 0;
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.next-btn, .action-btn {
  padding: 12px 30px;
  font-size: 1rem;
  border-radius: 50px;
  min-width: 160px;
}

.prev-btn {
  padding: 10px 24px;
  border-radius: 50px;
}

.refresh-btn {
  border-radius: 50px;
  padding: 10px 20px;
}

/* 动画效果 */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.5s ease;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* 标签页样式 */
.scheduling-tabs {
  margin-top: 40px;
  background: white;
  border-radius: 24px 24px 0 0;
  overflow: hidden;
  box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.1);
}

.scheduling-tabs :deep(.el-tabs__header) {
  background: #f8f9fa;
  margin: 0;
}

.scheduling-tabs :deep(.el-tabs__content) {
  padding: 40px;
}

/* 分页样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  border-top: 1px solid #ebeef5;
  margin-top: 20px;
}

.pagination-container .el-pagination {
  --el-pagination-bg-color: transparent;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-stats {
    flex-direction: row;
    gap: 12px;
    width: 100%;
    justify-content: center;
  }
  
  .stat-item {
    min-width: 50px;
  }
  
  .stat-value {
    font-size: 1.2rem;
  }
  
  .stat-label {
    font-size: 0.6rem;
  }
  
  .card-header {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .steps-container {
    flex-direction: column;
    gap: 30px;
  }
  
  .step-connector {
    display: none;
  }
  
  .batch-grid {
    grid-template-columns: 1fr;
  }
  
  .algorithm-grid {
    grid-template-columns: 1fr;
  }
  
  .summary-grid {
    grid-template-columns: 1fr;
  }
  
  .step-actions {
    flex-direction: column;
    gap: 12px;
  }
  
  .result-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .card-header {
    padding: 20px;
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .card-content {
    padding: 30px 20px;
  }
}

/* 弹窗相关样式 */
.dialog-progress-content {
  padding: 20px;
}

.progress-header-section {
  margin-bottom: 24px;
}

.task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
}

.task-info h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.status-tag {
  margin-left: 16px;
}

.progress-body {
  padding: 16px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 确保弹窗中的进度条样式正确 */
.dialog-progress-content .progress-section {
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 24px;
}

.dialog-progress-content .progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.dialog-progress-content .progress-header h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.dialog-progress-content .progress-percent {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

.dialog-progress-content .progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.dialog-progress-content .detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.dialog-progress-content .detail-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.dialog-progress-content .detail-label {
  font-weight: 500;
  color: #606266;
}

.dialog-progress-content .detail-value {
  color: #303133;
  font-family: monospace;
}

.dialog-progress-content .error-section {
  margin: 24px 0;
}

.dialog-progress-content .result-summary {
  margin-top: 24px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
}

.dialog-progress-content .summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.dialog-progress-content .summary-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.dialog-progress-content .summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  background: #409eff;
  color: white;
}

.dialog-progress-content .summary-icon.success {
  background: #67c23a;
}

.dialog-progress-content .summary-icon.warning {
  background: #e6a23c;
}

.dialog-progress-content .summary-content h3 {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.dialog-progress-content .summary-content p {
  margin: 0;
  font-size: 14px;
  color: #606266;
}
</style>