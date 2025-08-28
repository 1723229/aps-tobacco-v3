<template>
  <div class="scheduling-management">
    <!-- 现代化背景和标题区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <el-breadcrumb separator="/" class="hero-breadcrumb">
          <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>排产管理</el-breadcrumb-item>
        </el-breadcrumb>
        <h1 class="hero-title">
          <el-icon class="hero-icon"><Operation /></el-icon>
          智能排产系统
        </h1>
        <p class="hero-description">基于AI算法的烟草生产智能排产解决方案</p>
      </div>
    </div>

    <!-- 工作流步骤指示器 -->
    <div class="workflow-steps">
      <div class="steps-container">
        <div 
          v-for="(step, index) in workflowSteps" 
          :key="step.id"
          class="step-item"
          :class="{ 'active': currentStep >= index + 1, 'completed': currentStep > index + 1 }"
        >
          <div class="step-circle">
            <el-icon v-if="currentStep > index + 1" class="step-check"><Check /></el-icon>
            <span v-else>{{ index + 1 }}</span>
          </div>
          <div class="step-content">
            <h3 class="step-title">{{ step.title }}</h3>
            <p class="step-description">{{ step.description }}</p>
          </div>
          <div v-if="index < workflowSteps.length - 1" class="step-connector">
            <div class="connector-line" :class="{ 'active': currentStep > index + 1 }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 步骤1: 选择排产批次 -->
      <transition name="slide-fade">
        <div v-if="currentStep >= 1" class="step-panel" id="step-batch">
          <div class="step-card">
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><FolderOpened /></el-icon>
                <div>
                  <h2>选择排产批次</h2>
                  <p>从已导入的生产计划中选择需要排产的批次</p>
                </div>
              </div>
              <el-button 
                type="primary" 
                @click="refreshBatches"
                :loading="batchLoading"
                class="refresh-btn"
              >
                <el-icon><Refresh /></el-icon>
                刷新批次
              </el-button>
            </div>
            
            <div class="card-content">
              <div v-if="availableBatches.length === 0" class="empty-state">
                <el-icon class="empty-icon"><DocumentRemove /></el-icon>
                <h3>暂无可用批次</h3>
                <p>请先上传生产计划文件，或刷新查看最新批次</p>
                <el-button type="primary" @click="$router.push('/decade-plan/entry')">
                  去上传文件
                </el-button>
              </div>
              
              <div v-else class="batch-grid">
                <div
                  v-for="batch in availableBatches"
                  :key="batch.batch_id"
                  class="batch-card"
                  :class="{ 'selected': selectedBatchId === batch.batch_id }"
                  @click="selectBatch(batch.batch_id)"
                >
                  <div class="batch-header">
                    <el-icon class="batch-icon"><Document /></el-icon>
                    <div class="batch-info">
                      <h4>{{ batch.file_name }}</h4>
                      <p>{{ formatDateTime(batch.upload_time) }}</p>
                    </div>
                    <el-tag :type="getBatchStatusType(batch.status)" size="small">
                      {{ getBatchStatusText(batch.status) }}
                    </el-tag>
                  </div>
                  <div class="batch-stats">
                    <div class="stat-item">
                      <span class="stat-label">记录数</span>
                      <span class="stat-value">{{ batch.valid_records }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">批次ID</span>
                      <span class="stat-value">{{ batch.batch_id.slice(-8) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-if="selectedBatchId" class="next-step-action">
                <el-button 
                  type="primary" 
                  size="large" 
                  @click="nextStep"
                  class="next-btn"
                >
                  下一步：算法配置
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 步骤2: 算法配置 -->
      <transition name="slide-fade">
        <div v-if="currentStep >= 2" class="step-panel" id="step-algorithm">
          <div class="step-card">
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><Setting /></el-icon>
                <div>
                  <h2>算法配置</h2>
                  <p>选择适合的智能排产算法组合</p>
                </div>
              </div>
              <div class="algorithm-summary">
                <span>已启用: {{ enabledAlgorithmCount }} / 4</span>
              </div>
            </div>
            
            <div class="card-content">
              <div class="algorithm-grid">
                <div
                  v-for="algorithm in algorithmOptions"
                  :key="algorithm.key"
                  class="algorithm-card"
                  :class="{ 'enabled': algorithmConfig[algorithm.key] }"
                >
                  <div class="algorithm-header">
                    <el-icon class="algorithm-icon">
                      <component :is="algorithm.icon" />
                    </el-icon>
                    <div class="algorithm-info">
                      <h4>{{ algorithm.title }}</h4>
                      <p>{{ algorithm.description }}</p>
                    </div>
                    <el-switch
                      v-model="algorithmConfig[algorithm.key]"
                      size="large"
                      :active-color="algorithm.color"
                    />
                  </div>
                  <div class="algorithm-tags">
                    <el-tag
                      v-for="tag in algorithm.tags"
                      :key="tag"
                      size="small"
                      effect="plain"
                    >
                      {{ tag }}
                    </el-tag>
                  </div>
                </div>
              </div>
              
              <div class="step-actions">
                <el-button @click="prevStep" class="prev-btn">
                  <el-icon><ArrowLeft /></el-icon>
                  上一步
                </el-button>
                <el-button 
                  type="primary" 
                  size="large" 
                  @click="nextStep"
                  class="next-btn"
                >
                  下一步：开始排产
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 步骤3: 执行排产 -->
      <transition name="slide-fade">
        <div v-if="currentStep >= 3" class="step-panel" id="step-execute">
          <div class="step-card">
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><VideoPlay /></el-icon>
                <div>
                  <h2>执行排产</h2>
                  <p>智能算法正在为您生成最优排产方案</p>
                </div>
              </div>
              <el-tag 
                v-if="currentTask"
                :type="getTaskStatusType(currentTask.status)"
                size="large"
                class="task-status-tag"
              >
                {{ getTaskStatusText(currentTask.status) }}
              </el-tag>
            </div>
            
            <div class="card-content">
              <div v-if="!currentTask" class="execute-ready">
                <div class="ready-icon">
                  <el-icon><Lightning /></el-icon>
                </div>
                <h3>准备就绪</h3>
                <p>点击开始按钮启动智能排产</p>
                <el-button 
                  type="primary" 
                  size="large"
                  :loading="schedulingLoading"
                  @click="executeScheduling"
                  class="execute-btn"
                >
                  <el-icon v-if="!schedulingLoading"><VideoPlay /></el-icon>
                  {{ schedulingLoading ? '正在创建任务...' : '开始排产' }}
                </el-button>
              </div>
              
              <div v-else class="task-progress">
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
              </div>
              
              <div class="step-actions">
                <el-button @click="prevStep" :disabled="schedulingLoading" class="prev-btn">
                  <el-icon><ArrowLeft /></el-icon>
                  上一步
                </el-button>
                <el-button 
                  v-if="currentTask?.status === 'COMPLETED'"
                  type="success" 
                  size="large" 
                  @click="nextStep"
                  class="next-btn"
                >
                  查看结果
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 步骤4: 查看结果 -->
      <transition name="slide-fade">
        <div v-if="currentStep >= 4 && currentTask?.status === 'COMPLETED'" class="step-panel" id="step-result">
          <div class="step-card">
            <div class="card-header">
              <div class="header-content">
                <el-icon class="header-icon"><TrendCharts /></el-icon>
                <div>
                  <h2>排产结果</h2>
                  <p>智能排产已完成，查看生成的工单和时间安排</p>
                </div>
              </div>
              <el-tag type="success" size="large">
                排产完成
              </el-tag>
            </div>
            
            <div class="card-content">
              <div v-if="currentTask.result_summary" class="result-summary">
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
                      <h3>{{ currentTask.result_summary.packing_orders || 0 }}</h3>
                      <p>卷包机工单</p>
                    </div>
                  </div>
                  <div class="summary-card">
                    <div class="summary-icon warning">
                      <el-icon><Operation /></el-icon>
                    </div>
                    <div class="summary-content">
                      <h3>{{ currentTask.result_summary.feeding_orders || 0 }}</h3>
                      <p>喂丝机工单</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="result-actions">
                <el-button 
                  type="primary" 
                  size="large"
                  @click="viewGanttChart"
                  class="action-btn"
                >
                  <el-icon><TrendCharts /></el-icon>
                  查看甘特图
                </el-button>
                <el-button 
                  size="large"
                  @click="viewTaskHistory"
                  class="action-btn"
                >
                  <el-icon><Clock /></el-icon>
                  历史记录
                </el-button>
                <el-button 
                  size="large"
                  @click="resetWorkflow"
                  class="action-btn"
                >
                  <el-icon><RefreshRight /></el-icon>
                  新建排产
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 其他标签页内容 -->
    <el-tabs v-model="activeTab" type="card" class="scheduling-tabs" v-if="showTabs">
      <!-- 排产历史标签页 -->
      <el-tab-pane label="排产历史" name="history">
        <SchedulingHistoryTab />
      </el-tab-pane>

      <!-- 甘特图查看标签页 -->
      <el-tab-pane label="甘特图查看" name="gantt">
        <GanttChartTab />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { SchedulingAPI, DecadePlanAPI } from '@/services/api'
import type { 
  SchedulingAlgorithmConfig, 
  SchedulingTask 
} from '@/services/api'
import { formatDateTime } from '@/utils'
import {
  Operation,
  Check,
  FolderOpened,
  Refresh,
  DocumentRemove,
  Document,
  ArrowRight,
  ArrowLeft,
  Setting,
  VideoPlay,
  Lightning,
  TrendCharts,
  Clock,
  RefreshRight,
  Box
} from '@element-plus/icons-vue'

// 导入子组件
import SchedulingHistoryTab from '@/components/SchedulingHistoryTab.vue'
import GanttChartTab from '@/components/GanttChartTab.vue'

const router = useRouter()

// 响应式数据
const activeTab = ref('execute')
const currentStep = ref(1)
const selectedBatchId = ref<string>('')
const availableBatches = ref<any[]>([])
const batchLoading = ref(false)
const schedulingLoading = ref(false)
const currentTask = ref<SchedulingTask | null>(null)
const showTabs = ref(false)

// 工作流步骤定义
const workflowSteps = ref([
  {
    id: 'batch',
    title: '选择批次',
    description: '选择需要排产的数据批次'
  },
  {
    id: 'algorithm',
    title: '算法配置', 
    description: '配置智能排产算法参数'
  },
  {
    id: 'execute',
    title: '执行排产',
    description: '启动AI算法进行排产计算'
  },
  {
    id: 'result',
    title: '查看结果',
    description: '查看排产结果和工单详情'
  }
])

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
const refreshBatches = async () => {
  batchLoading.value = true
  try {
    const response = await DecadePlanAPI.getAvailableBatchesForScheduling()
    availableBatches.value = response.data.available_batches
  } catch (error) {
    ElMessage.error('获取可排产批次失败')
    console.error('Refresh batches error:', error)
  } finally {
    batchLoading.value = false
  }
}

const selectBatch = (batchId: string) => {
  selectedBatchId.value = batchId
  currentTask.value = null
}

const nextStep = () => {
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const executeScheduling = async () => {
  if (!selectedBatchId.value) return
  
  schedulingLoading.value = true
  try {
    const response = await SchedulingAPI.executeScheduling(
      selectedBatchId.value,
      algorithmConfig
    )
    
    ElMessage.success('排产任务已创建')
    
    // 开始轮询任务状态
    await pollTaskStatus(response.data.task_id)
    
  } catch (error) {
    ElMessage.error('排产任务创建失败')
    console.error('Execute scheduling error:', error)
  } finally {
    schedulingLoading.value = false
  }
}

const pollTaskStatus = async (taskId: string) => {
  try {
    await SchedulingAPI.pollTaskStatus(
      taskId,
      (statusResponse) => {
        currentTask.value = statusResponse.data
        
        // 如果完成，显示成功信息并跳转到结果步骤
        if (statusResponse.data.status === 'COMPLETED') {
          ElMessage.success('排产完成！')
          currentStep.value = 4
        } else if (statusResponse.data.status === 'FAILED') {
          ElMessage.error('排产失败')
        }
      }
    )
  } catch (error) {
    ElMessage.error('排产状态监控失败')
    console.error('Poll task status error:', error)
  }
}

const viewTaskHistory = () => {
  showTabs.value = true
  activeTab.value = 'history'
}

const viewGanttChart = () => {
  if (currentTask.value) {
    // 跳转到甘特图页面并传递任务信息
    router.push({
      name: 'GanttChart',
      query: {
        task_id: currentTask.value.task_id,
        import_batch_id: currentTask.value.import_batch_id
      }
    })
  } else {
    showTabs.value = true
    activeTab.value = 'gantt'
  }
}

const resetWorkflow = () => {
  currentStep.value = 1
  selectedBatchId.value = ''
  currentTask.value = null
  showTabs.value = false
  refreshBatches()
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

const getBatchStatusType = (status: string) => {
  const statusMap: Record<string, any> = {
    'PARSED': 'success',
    'PROCESSING': 'warning',
    'FAILED': 'danger'
  }
  return statusMap[status] || 'info'
}

const getBatchStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'PARSED': '已解析',
    'PROCESSING': '处理中',
    'FAILED': '失败'
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
  refreshBatches()
})
</script>

<style scoped>
.scheduling-management {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 英雄区域 */
.hero-section {
  padding: 40px 20px;
  text-align: center;
  color: white;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
}

.hero-breadcrumb {
  justify-content: center;
  margin-bottom: 20px;
}

.hero-breadcrumb :deep(.el-breadcrumb__item .el-breadcrumb__inner) {
  color: rgba(255, 255, 255, 0.8);
}

.hero-breadcrumb :deep(.el-breadcrumb__item .el-breadcrumb__inner:hover) {
  color: white;
}

.hero-title {
  font-size: 3rem;
  font-weight: 700;
  margin: 20px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.hero-icon {
  font-size: 3rem;
}

.hero-description {
  font-size: 1.2rem;
  margin: 0;
  opacity: 0.9;
}

/* 工作流步骤 */
.workflow-steps {
  padding: 60px 20px;
  background: white;
}

.steps-container {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: flex-start;
  position: relative;
}

.step-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
}

.step-circle {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #f5f5f5;
  border: 3px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
  color: #999;
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.step-item.active .step-circle {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
  color: white;
}

.step-item.completed .step-circle {
  background: #67c23a;
  border-color: #67c23a;
  color: white;
}

.step-check {
  font-size: 1.5rem;
}

.step-content {
  text-align: center;
}

.step-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #333;
}

.step-item.active .step-title {
  color: #667eea;
}

.step-description {
  font-size: 0.9rem;
  color: #666;
  margin: 0;
  line-height: 1.4;
}

.step-connector {
  position: absolute;
  top: 30px;
  left: 50%;
  right: -50%;
  height: 3px;
  background: #eee;
  z-index: 1;
}

.step-item:last-child .step-connector {
  display: none;
}

.connector-line {
  height: 100%;
  background: #eee;
  transition: all 0.3s ease;
}

.connector-line.active {
  background: linear-gradient(90deg, #67c23a 0%, #85ce61 100%);
}

/* 主内容区域 */
.main-content {
  padding: 0 20px 60px;
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
  align-items: center;
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

/* 响应式设计 */
@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
    flex-direction: column;
    gap: 12px;
  }
  
  .hero-icon {
    font-size: 2rem;
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
</style>