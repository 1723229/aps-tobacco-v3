<template>
  <div class="decade-plan-entry">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-button text @click="goBack" class="back-button">
            <el-icon><ArrowLeft /></el-icon>
            返回首页
          </el-button>
          <h1 class="page-title">
            <el-icon><UploadFilled /></el-icon>
            卷包旬计划录入
          </h1>
          <p class="page-description">上传Excel文件进行卷包旬计划数据录入与解析</p>
        </div>
        <div class="header-right">
          <el-button @click="downloadTemplate" plain>
            <el-icon><Download /></el-icon>
            下载模板
          </el-button>
        </div>
      </div>
    </div>

    <!-- 当前上传状态概览 -->
    <div v-if="currentBatchId" class="current-status">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>当前批次: {{ currentBatchId }}</span>
            <el-tag v-if="uploadStatus" :type="getStatusColor(uploadStatus)" size="small">
              {{ getStatusText(uploadStatus) }}
            </el-tag>
          </div>
        </template>
        
        <el-steps :active="currentStep" align-center>
          <el-step title="文件上传" :icon="UploadFilled" />
          <el-step title="数据解析" :icon="Reading" />
          <el-step title="结果展示" :icon="View" />
          <el-step title="记录查看" :icon="Grid" />
        </el-steps>
      </el-card>
    </div>

    <!-- 文件上传组件 -->
    <div class="upload-section">
      <DecadePlanUpload 
        @upload-success="handleUploadSuccess"
        @parse-success="handleParseSuccess"
        @view-details="handleViewDetails"
      />
    </div>

    <!-- 历史上传记录 -->
    <div class="history-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span>最近上传记录</span>
            <div class="header-actions">
              <el-button size="small" @click="toggleHistory">
                {{ showHistory ? '收起' : '展开' }}
              </el-button>
            </div>
          </div>
        </template>
        
        <div v-show="showHistory">
          <el-table 
          :data="uploadHistory" 
          style="width: 100%" 
          size="small"
          :loading="historyLoading"
        >
          <el-table-column prop="batch_id" label="批次ID" width="160" />
          <el-table-column prop="file_name" label="文件名" show-overflow-tooltip />
          <el-table-column prop="upload_time" label="上传时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.upload_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="file_size" label="文件大小" width="100" align="right">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="total_records" label="记录数" width="100" align="right" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusColor(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center">
            <template #default="{ row }">
              <el-button-group size="small">
                <el-button text @click="viewBatchDetails(row.batch_id)">
                  <el-icon><View /></el-icon>
                  查看
                </el-button>
                <el-button 
                  v-if="row.status === 'FAILED'"
                  text 
                  type="warning" 
                  @click="retryParse(row.batch_id)"
                >
                  <el-icon><Refresh /></el-icon>
                  重试
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
        
        <div v-if="uploadHistory.length === 0 && !historyLoading && showHistory" class="empty-state">
          <el-empty description="暂无上传记录" />
        </div>
        </div>
      </el-card>
    </div>

    <!-- 使用说明 -->
    <div class="help-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-icon><QuestionFilled /></el-icon>
            <span>使用说明</span>
          </div>
        </template>
        
        <div class="help-content">
          <el-row :gutter="24">
            <el-col :span="8">
              <div class="help-item">
                <div class="help-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <h4>文件格式要求</h4>
                <ul>
                  <li>支持 .xlsx 或 .xls 格式</li>
                  <li>文件大小不超过 50MB</li>
                  <li>请使用标准模板格式</li>
                </ul>
              </div>
            </el-col>
            
            <el-col :span="8">
              <div class="help-item">
                <div class="help-icon">
                  <el-icon><Setting /></el-icon>
                </div>
                <h4>数据字段说明</h4>
                <ul>
                  <li>工单号：必填，唯一标识</li>
                  <li>成品烟牌号：产品代码</li>
                  <li>机台代码：喂丝机/卷包机</li>
                  <li>数量信息：投料量/成品量</li>
                </ul>
              </div>
            </el-col>
            
            <el-col :span="8">
              <div class="help-item">
                <div class="help-icon">
                  <el-icon><Warning /></el-icon>
                </div>
                <h4>注意事项</h4>
                <ul>
                  <li>上传前请检查数据完整性</li>
                  <li>重复上传会覆盖之前数据</li>
                  <li>解析失败请检查格式</li>
                </ul>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft,
  UploadFilled, 
  Download, 
  Clock, 
  InfoFilled,
  Reading,
  View,
  Grid,
  List,
  QuestionFilled,
  Document,
  Setting,
  Warning,
  Refresh
} from '@element-plus/icons-vue'
import DecadePlanUpload from '@/components/DecadePlanUpload.vue'
import { useDecadePlanStore } from '@/stores/decade-plan'
import { formatDateTime, formatFileSize, getStatusColor, getStatusText } from '@/utils'
import DecadePlanAPI from '@/services/api'
import type { UploadResponse, ParseResponse, HistoryRecord } from '@/types/api'

const router = useRouter()
const route = useRoute()
const decadePlanStore = useDecadePlanStore()

// 响应式数据
const showHistory = ref(route.query.tab === 'history')
const historyLoading = ref(false)
const uploadHistory = ref<HistoryRecord[]>([])

// 计算属性
const currentBatchId = computed(() => decadePlanStore.currentBatchId)
const uploadStatus = computed(() => decadePlanStore.importStatus?.import_status)

const currentStep = computed(() => {
  const status = uploadStatus.value
  switch (status) {
    case 'UPLOADING':
      return 0
    case 'PARSING':
      return 1
    case 'COMPLETED':
      return 3
    case 'FAILED':
      return 1
    default:
      return 0
  }
})

// 方法
const goBack = () => {
  router.push('/')
}

const downloadTemplate = () => {
  // TODO: 实现模板下载
  ElMessage.info('模板下载功能开发中...')
}

const viewHistory = () => {
  showHistory.value = !showHistory.value
  if (showHistory.value && uploadHistory.value.length === 0) {
    loadUploadHistory()
  }
}

const toggleHistory = () => {
  showHistory.value = !showHistory.value
  
  // 更新URL参数
  const query = { ...route.query }
  if (showHistory.value) {
    query.tab = 'history'
  } else {
    delete query.tab
  }
  router.replace({ query })
}

const handleUploadSuccess = (result: UploadResponse) => {
  ElMessage.success('文件上传成功！')
  decadePlanStore.setCurrentBatchId(result.data.import_batch_id)
  
  // 刷新历史记录
  if (showHistory.value) {
    loadUploadHistory()
  }
}

const handleParseSuccess = (result: ParseResponse) => {
  ElMessage.success('文件解析完成！')
  
  // 刷新历史记录
  if (showHistory.value) {
    loadUploadHistory()
  }
}

const handleViewDetails = (batchId: string) => {
  router.push(`/decade-plan/detail/${batchId}`)
}

const viewBatchDetails = (batchId: string) => {
  router.push(`/decade-plan/detail/${batchId}`)
}

const retryParse = async (batchId: string) => {
  try {
    ElMessage.info('重新解析中...')
    await DecadePlanAPI.parseFile(batchId, true)
    ElMessage.success('重新解析成功！')
    loadUploadHistory()
  } catch (error) {
    console.error('重新解析失败:', error)
    ElMessage.error('重新解析失败，请稍后重试')
  }
}

const loadUploadHistory = async () => {
  try {
    historyLoading.value = true
    const historyResponse = await DecadePlanAPI.getUploadHistory(1, 10)
    uploadHistory.value = historyResponse.data.records
  } catch (error) {
    console.error('加载历史记录失败:', error)
    ElMessage.error('加载历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

// 生命周期
onMounted(() => {
  console.log('DecadePlan Entry page mounted')
  
  // 如果是历史模式，加载历史记录
  if (showHistory.value) {
    loadUploadHistory()
  }
})
</script>

<style scoped>
.decade-plan-entry {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-radius: 12px;
  color: white;
}

.back-button {
  color: white !important;
  padding: 4px 8px;
  margin-bottom: 8px;
}

.back-button:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

.header-left .page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.header-left .page-description {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.current-status {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.header-actions {
  margin-left: auto;
}

.upload-section {
  margin-bottom: 24px;
}

.history-section {
  margin-bottom: 24px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.help-section {
  margin-bottom: 24px;
}

.help-content {
  padding: 16px;
}

.help-item {
  text-align: center;
  padding: 20px;
}

.help-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #67c23a);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 24px;
  color: white;
}

.help-item h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #303133;
}

.help-item ul {
  text-align: left;
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.help-item li {
  margin-bottom: 4px;
}

:deep(.el-steps) {
  margin: 20px 0;
}

:deep(.el-step__title) {
  font-size: 14px;
}
</style>