<template>
  <div class="scheduling-management">
    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 待排产月度计划列表 -->
      <div class="plans-section">
        <el-card class="plans-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><FolderOpened /></el-icon>
                <div>
                  <h2>待排产月度计划</h2>
                  <p>选择需要排产的月度计划，点击开始排产按钮执行智能算法</p>
                </div>
              </div>
              <div class="header-stats">
                <div class="modern-stat-card pending">
                  <div class="stat-icon">
                    <el-icon><Clock /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ availablePlansCount }}</div>
                    <div class="stat-label">待排产计划</div>
                  </div>
                  <div class="stat-trend up">
                    <el-icon><TrendCharts /></el-icon>
                  </div>
                </div>
                <div class="modern-stat-card running">
                  <div class="stat-icon">
                    <el-icon><Timer /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ runningTasksCount }}</div>
                    <div class="stat-label">进行中</div>
                  </div>
                  <div class="stat-trend">
                    <el-icon><Operation /></el-icon>
                  </div>
                </div>
                <div class="modern-stat-card completed">
                  <div class="stat-icon">
                    <el-icon><CircleCheck /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ completedTasksCount }}</div>
                    <div class="stat-label">已完成</div>
                  </div>
                  <div class="stat-trend up">
                    <el-icon><TrendCharts /></el-icon>
                  </div>
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
                  @click="$router.push('/monthly-plan/entry')"
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
              <el-button type="primary" @click="$router.push('/monthly-plan/entry')">
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
          
          <MonthlySchedulingHistoryTab :limit="5" />
        </el-card>
      </div>
    </div>
    
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
                <span class="detail-value">{{ currentTask.monthly_batch_id?.slice(-8) || '--' }}</span>
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
          <div v-if="currentTask.status === 'COMPLETED' && currentTask.algorithm_summary" class="result-summary">
            <div class="summary-grid">
              <div class="summary-card">
                <div class="summary-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ currentTask.scheduled_plans || 0 }}</h3>
                  <p>总工单数</p>
                </div>
              </div>
              <div class="summary-card">
                <div class="summary-icon success">
                  <el-icon><Box /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ Math.floor((currentTask.scheduled_plans || 0) * 0.6) }}</h3>
                  <p>卷包机工单</p>
                </div>
              </div>
              <div class="summary-card">
                <div class="summary-icon warning">
                  <el-icon><Operation /></el-icon>
                </div>
                <div class="summary-content">
                  <h3>{{ Math.floor((currentTask.scheduled_plans || 0) * 0.4) }}</h3>
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
import { MonthlySchedulingAPI, MonthlyPlanAPI } from '@/services/api'
import type { 
  SchedulingAlgorithmConfig, 
  MonthlySchedulingTaskResponse,
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
  Share,
  CircleCheck
} from '@element-plus/icons-vue'

// 导入子组件
import MonthlySchedulingHistoryTab from '@/components/MonthlySchedulingHistoryTab.vue'

const router = useRouter()

// 响应式数据
const availablePlans = ref<AvailableBatch[]>([])
const selectedPlans = ref<AvailableBatch[]>([])
const plansLoading = ref(false)
const schedulingLoading = ref(false)
const currentTask = ref<MonthlySchedulingTaskResponse | null>(null)
const progressDialogVisible = ref(false)
const selectedPlanForScheduling = ref<AvailableBatch | null>(null)
const pollingTimer = ref<number | null>(null)

// 分页相关数据
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)

// 全局统计数据（基于全库数据）
const availablePlansCount = ref(0)
const runningTasksCount = ref(0)
const completedTasksCount = ref(0)

// 计算属性
const canExecuteScheduling = computed(() => {
  return selectedPlanForScheduling.value && !schedulingLoading.value
})

// 基于列表数据计算统计数据，确保一致性
const calculateStatisticsFromPlans = () => {
  let available = 0
  let running = 0
  let completed = 0
  
  availablePlans.value.forEach(plan => {
    switch (plan.scheduling_status) {
      case 'unscheduled':
        if (plan.can_schedule) {
          available++
        }
        break
      case 'pending':
      case 'running':
        running++
        break
      case 'completed':
        completed++
        break
    }
  })
  
  availablePlansCount.value = available
  runningTasksCount.value = running
  completedTasksCount.value = completed
  
  console.log('✅ 基于列表数据计算统计:', {
    待排产计划: available,
    进行中: running,
    已完成: completed,
    总计: availablePlans.value.length
  })
}

// 方法定义
const refreshPlans = async () => {
  plansLoading.value = true
  try {
    // 加载列表数据
    const historyResponse = await MonthlyPlanAPI.getUploadHistory(
      currentPage.value,
      pageSize.value, 
      'COMPLETED' // 只获取已解析完成的记录
    )
    
    const allRecords = historyResponse.data.imports
    totalCount.value = historyResponse.data.pagination.total_count
    
    // 查询每个批次的最新排产任务状态
    const plansWithStatus = await Promise.all(
      allRecords.map(async (record: any) => {
        const can_schedule = record.valid_records > 0
        let scheduling_status = 'unscheduled'
        let scheduling_text = can_schedule ? '可排产' : '无法排产'
        let task_id = null
        
        if (can_schedule) {
          try {
            // 查询该批次的最新排产任务
            const taskResponse = await MonthlySchedulingAPI.getHistory({
              monthly_batch_id: record.monthly_batch_id,
              page: 1,
              page_size: 1
            })
            
            if (taskResponse.code === 200 && taskResponse.data.tasks.length > 0) {
              const latestTask = taskResponse.data.tasks[0]
              task_id = latestTask.task_id
              
              // 根据任务状态设置排产状态
              switch (latestTask.status) {
                case 'PENDING':
                  scheduling_status = 'pending'
                  scheduling_text = '等待中'
                  break
                case 'RUNNING':
                  scheduling_status = 'running'
                  scheduling_text = '排产中'
                  break
                case 'COMPLETED':
                  scheduling_status = 'completed'
                  scheduling_text = '已完成'
                  break
                case 'FAILED':
                  scheduling_status = 'failed'
                  scheduling_text = '失败'
                  break
                default:
                  scheduling_status = 'unscheduled'
                  scheduling_text = '可排产'
              }
            }
          } catch (error) {
            console.warn(`获取批次 ${record.monthly_batch_id} 的任务状态失败:`, error)
          }
        }
        
        return {
          batch_id: record.monthly_batch_id, // 使用正确的字段名
          file_name: record.file_name,
          total_records: record.total_records,
          valid_records: record.valid_records,
          import_end_time: record.updated_time, // 使用updated_time作为完成时间
          display_name: `${record.file_name} (${record.valid_records}条记录)`,
          can_schedule: can_schedule, // 根据有效记录数判断是否可排产
          scheduling_status: scheduling_status, // 动态查询的状态
          scheduling_text: scheduling_text, // 动态设置的文本
          task_id: task_id, // 最新任务ID
          work_orders_summary: 0 // 目前没有工单摘要
        }
      })
    )
    
    availablePlans.value = plansWithStatus
    
    // 基于列表数据计算统计，确保一致性
    calculateStatisticsFromPlans()
    
    console.log('📊 列表数据加载完成:', {
      当前页记录数: availablePlans.value.length,
      总记录数: totalCount.value
    })
    
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

const startScheduling = async (plan: AvailableBatch) => {
  // 直接执行排产，不显示配置对话框
  selectedPlanForScheduling.value = plan
  await confirmScheduling()
}

const confirmScheduling = async () => {
  if (!selectedPlanForScheduling.value) return
  
  // 防止重复提交
  if (schedulingLoading.value) {
    console.log('⚠️ 排产任务正在执行中，忽略重复提交')
    return
  }
  
  schedulingLoading.value = true
  progressDialogVisible.value = true
  
  try {
    // 使用默认的月度算法配置
    const defaultConfig = {
      optimization_level: 'medium',
      enable_load_balancing: true,
      max_execution_time: 300,
      target_efficiency: 0.85
    }
    
    // 直接使用batch_id，它已经包含正确的MONTHLY_前缀  
    const batchId = selectedPlanForScheduling.value.batch_id
    
    console.log('🚀 开始执行月度排产:', {
      monthly_batch_id: batchId,
      config: defaultConfig
    })
    
    const response = await MonthlySchedulingAPI.executeScheduling(
      batchId,
      defaultConfig
    )
    
    console.log('✅ 月度排产任务创建成功:', response)
    ElMessage.success('月度排产任务已创建')
    
    // 开始轮询任务状态
    await pollTaskStatus(response.data.task_id)
    
    // 刷新计划列表和全局统计
    await Promise.all([
      refreshPlans(),
      loadGlobalStatistics()
    ])
    
  } catch (error: any) {
    console.error('❌ 月度排产执行失败:', error)
    
    // 处理不同类型的错误
    if (error.response?.status === 409) {
      // 409冲突，任务已存在
      const detail = error.response?.data?.detail || '月度排产任务已创建，正在后台执行'
      ElMessage.warning(detail)
      
      // 如果错误信息包含任务ID，尝试开始轮询
      const taskIdMatch = detail.match(/任务ID：(\w+)/)
      if (taskIdMatch) {
        const taskId = taskIdMatch[1]
        console.log('🔄 检测到已存在任务，开始轮询状态:', taskId)
        await pollTaskStatus(taskId)
      }
    } else if (error.response?.status === 404) {
      // 404错误，月度批次不存在
      const errorMessage = error.response?.data?.detail || '月度批次不存在'
      ElMessage.error(errorMessage)
      progressDialogVisible.value = false
      
      // 刷新列表以更新状态
      await refreshPlans()
    } else {
      // 其他错误
      const errorMessage = error.response?.data?.detail || error.message || '排产任务创建失败'
      ElMessage.error(errorMessage)
      progressDialogVisible.value = false
    }
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
      const response = await MonthlySchedulingAPI.getTaskStatus(taskId)
      currentTask.value = response.data
      
              if (response.data.status === 'COMPLETED') {
          ElMessage.success('排产完成！')
          clearInterval(pollingTimer.value!)
          pollingTimer.value = null
          // 刷新列表和全局统计
          await Promise.all([
            refreshPlans(),
            loadGlobalStatistics()
          ])
          // 延迟关闭弹窗，让用户看到完成状态
          setTimeout(() => {
            progressDialogVisible.value = false
          }, 2000)
        } else if (response.data.status === 'FAILED') {
          ElMessage.error('排产失败')
          clearInterval(pollingTimer.value!)
          pollingTimer.value = null
          // 刷新列表和全局统计
          await Promise.all([
            refreshPlans(),
            loadGlobalStatistics()
          ])
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
  // 刷新列表状态和全局统计
  Promise.all([
    refreshPlans(),
    loadGlobalStatistics()
  ])
}

const viewAllHistory = () => {
  router.push('/scheduling/history')
}

const viewGanttChart = (planOrTask: AvailableBatch | MonthlySchedulingTaskResponse) => {
  let taskId: string | undefined
  let importBatchId: string
  
  if ('task_id' in planOrTask) {
    // MonthlySchedulingTaskResponse
    taskId = planOrTask.task_id
    importBatchId = planOrTask.monthly_batch_id
  } else {
    // AvailableBatch with task info
    taskId = (planOrTask as any).task_id
    importBatchId = planOrTask.batch_id
  }
  
  router.push({
    name: 'MonthlyGanttChart',
    query: {
      ...(taskId && { task_id: taskId }),
      monthly_batch_id: importBatchId
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

/* Header统计样式 - 现代化设计 */
.header-stats {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.modern-stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #f0f0f0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 140px;
  overflow: hidden;
  z-index: 1;
}

.modern-stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--card-color), var(--card-color-light));
}

.modern-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.modern-stat-card.pending {
  --card-color: #3b82f6;
  --card-color-light: #60a5fa;
}

.modern-stat-card.running {
  --card-color: #f59e0b;
  --card-color-light: #fbbf24;
}

.modern-stat-card.completed {
  --card-color: #10b981;
  --card-color-light: #34d399;
}

.modern-stat-card .stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--card-color), var(--card-color-light));
  color: white;
  font-size: 18px;
  flex-shrink: 0;
}

.modern-stat-card .stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.modern-stat-card .stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
  position: relative;
  overflow: hidden;
}

.modern-stat-card .stat-label {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 500;
  white-space: nowrap;
}

.modern-stat-card .stat-trend {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(var(--card-color-rgb), 0.1);
  color: var(--card-color);
  font-size: 12px;
  flex-shrink: 0;
}

.modern-stat-card.pending {
  --card-color-rgb: 59, 130, 246;
}

.modern-stat-card.running {
  --card-color-rgb: 245, 158, 11;
}

.modern-stat-card.completed {
  --card-color-rgb: 16, 185, 129;
}

/* 添加数字动画效果 */

.modern-stat-card .stat-value::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, var(--card-color), var(--card-color-light));
  transform: scaleX(0);
  transition: transform 0.3s ease;
  transform-origin: left;
}

.modern-stat-card:hover .stat-value::after {
  transform: scaleX(1);
}

/* 卡片阴影层次已在上面定义 */

.modern-stat-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(var(--card-color-rgb), 0.03), rgba(var(--card-color-rgb), 0.01));
  border-radius: 16px;
  z-index: -1;
  transition: opacity 0.3s ease;
  opacity: 0;
}

.modern-stat-card:hover::after {
  opacity: 1;
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

/* 移除旧的stat样式，使用新的modern-stat-card样式 */

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
    flex-direction: column;
    gap: 12px;
    width: 100%;
    align-items: stretch;
  }
  
  .modern-stat-card {
    min-width: auto;
    width: 100%;
    justify-content: space-between;
  }
  
  .modern-stat-card .stat-value {
    font-size: 1.6rem;
  }
  
  .modern-stat-card .stat-label {
    font-size: 0.75rem;
  }
  
  .modern-stat-card .stat-icon {
    width: 36px;
    height: 36px;
    font-size: 16px;
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