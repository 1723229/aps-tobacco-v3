<template>
  <div class="decade-plan-entry">
    <!-- 页面标题区 -->
    <div class="page-title-section">
      <div class="title-content">
        <div class="title-left">
          <div class="title-icon">
            <el-icon><UploadFilled /></el-icon>
          </div>
          <div class="title-text">
            <h1>卷包旬计划录入</h1>
            <p>上传Excel文件进行卷包旬计划数据录入与解析</p>
          </div>
        </div>
        <div class="title-actions">
          <el-button type="primary" @click="goToScheduling">
            <el-icon><Lightning /></el-icon>
            智能排产管理
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 文件上传区域 -->
      <div class="upload-section">
        <el-card class="upload-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon class="header-icon"><Upload /></el-icon>
              <span class="header-title">文件上传</span>
            </div>
          </template>
          
          <DecadePlanUpload 
            @upload-success="handleUploadSuccess"
            @parse-success="handleParseSuccess"
            @view-details="handleViewDetails"
          />
        </el-card>
      </div>

      <!-- 历史记录区域 -->
      <div class="history-section">
        <el-card class="history-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-icon class="header-icon"><Clock /></el-icon>
                <span class="header-title">最近上传记录</span>
              </div>
              <div class="header-actions">
                <el-button 
                  :type="showHistory ? 'primary' : 'default'" 
                  size="small" 
                  @click="toggleHistory"
                  text
                >
                  {{ showHistory ? '收起' : '展开' }}
                  <el-icon class="expand-icon" :class="{ 'expanded': showHistory }">
                    <ArrowDown />
                  </el-icon>
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="history-content">
            <el-table 
              :data="uploadHistory" 
              style="width: 100%" 
              size="default"
              :loading="historyLoading"
              class="modern-table"
            >
              <el-table-column prop="batch_id" label="批次ID" width="160" />
              <el-table-column prop="file_name" label="文件名" show-overflow-tooltip />
              <el-table-column prop="upload_time" label="上传时间" width="160">
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
              <el-table-column label="操作" width="120" align="center">
                <template #default="{ row }">
                  <el-button-group size="small">
                    <el-button text type="primary" @click="viewBatchDetails(row.batch_id)">
                      <el-icon><View /></el-icon>
                    </el-button>
                    <el-button 
                      v-if="row.status === 'FAILED'"
                      text 
                      type="warning" 
                      @click="retryParse(row.batch_id)"
                    >
                      <el-icon><Refresh /></el-icon>
                    </el-button>
                  </el-button-group>
                </template>
              </el-table-column>
            </el-table>
            
            <div v-if="uploadHistory.length === 0 && !historyLoading" class="empty-state">
              <el-empty description="暂无上传记录" />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  UploadFilled, 
  Download, 
  Upload,
  Clock, 
  ArrowDown,
  Refresh,
  View,
  Lightning
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
const showHistory = ref(true) // 默认展示历史记录
const historyLoading = ref(false)
const uploadHistory = ref<HistoryRecord[]>([
  // 示例数据
  {
    batch_id: 'IMPORT_20241201_143052_a1b2c3d4',
    file_name: '卷包生产计划_2024年11月.xlsx',
    file_size: 2048576,
    upload_time: '2024-12-01 14:30:52',
    import_start_time: '2024-12-01 14:30:55',
    import_end_time: '2024-12-01 14:31:15',
    status: 'COMPLETED',
    total_records: 156,
    valid_records: 152,
    error_records: 4,
    error_message: null
  },
  {
    batch_id: 'IMPORT_20241130_101234_e5f6g7h8',
    file_name: '旬计划_第三旬_产品组合.xlsx',
    file_size: 1536789,
    upload_time: '2024-11-30 10:12:34',
    import_start_time: '2024-11-30 10:12:40',
    import_end_time: '2024-11-30 10:13:05',
    status: 'COMPLETED',
    total_records: 89,
    valid_records: 87,
    error_records: 2,
    error_message: null
  },
  {
    batch_id: 'IMPORT_20241129_165543_i9j0k1l2',
    file_name: '生产安排_机台配置_V2.xlsx',
    file_size: 3145728,
    upload_time: '2024-11-29 16:55:43',
    import_start_time: '2024-11-29 16:55:50',
    import_end_time: null,
    status: 'FAILED',
    total_records: 0,
    valid_records: 0,
    error_records: 0,
    error_message: '文件格式不正确，请检查表头字段'
  }
])

// 计算属性 - 移除了不再需要的currentBatchId和步骤相关逻辑

// 方法
const goToScheduling = () => {
  router.push('/scheduling')
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

  // 上传完成后，引导跳转到智能排产管理页面
  router.push('/scheduling')
  
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
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 0;
  border: none !important;
  outline: none !important;
}

/* Remove any yellow borders/outlines globally */
.decade-plan-entry *,
.decade-plan-entry *::before,
.decade-plan-entry *::after {
  border-color: transparent !important;
  outline: none !important;
}

.decade-plan-entry *:focus {
  outline: none !important;
  border-color: #409eff !important;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2) !important;
}

/* 页面标题区 */
.page-title-section {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 40px 0 60px 0;
  position: relative;
  overflow: hidden;
}

.page-title-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='4'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
}

.title-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 40px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  z-index: 1;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
}

.title-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
}

.title-text h1 {
  font-size: 2.5rem;
  font-weight: 700;
  color: #2d3748;
  margin: 0 0 8px 0;
}

.title-text p {
  font-size: 1.1rem;
  color: #4a5568;
  margin: 0;
  font-weight: 400;
}

.title-actions {
  margin-left: auto;
  position: relative;
  z-index: 1;
}

.title-actions .el-button {
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  border: none;
  color: #667eea;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.title-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  background: white;
}

/* 主要内容区域 */
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 40px;
  transform: translateY(-30px);
  position: relative;
  z-index: 2;
}

/* 顶部内容 */
.upload-section {
  margin-bottom: 40px;
}

.upload-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  background: white;
}

.upload-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border-bottom: 1px solid #e8eaed;
  padding: 24px 32px;
}

.upload-card :deep(.el-card__body) {
  padding: 40px 32px;
}

/* 历史记录 */
.history-section {
  margin-bottom: 40px;
}

.history-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  background: white;
}

.history-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #fff8f0 0%, #fff2e6 100%);
  border-bottom: 1px solid #e8eaed;
  padding: 24px 32px;
}

.history-card :deep(.el-card__body) {
  padding: 0;
}

.history-content {
  padding: 32px;
}

/* 卡片头部样式 */
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 16px;
  color: #2d3748;
}

.header-icon {
  font-size: 20px;
  color: #667eea;
}

.header-title {
  flex: 1;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions {
  margin-left: auto;
}

.expand-icon {
  margin-left: 8px;
  transition: transform 0.3s ease;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

/* 表格样式 */
.modern-table {
  border-radius: 12px;
  overflow: hidden;
}

.modern-table :deep(.el-table__header) {
  background: #f8fafc;
}

.modern-table :deep(.el-table__header th) {
  background: #f8fafc;
  color: #4a5568;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}

.modern-table :deep(.el-table__body tr:hover) {
  background: #f7fafc;
}

.modern-table :deep(.el-table td) {
  border-bottom: 1px solid #f1f5f9;
}

/* 空状态 */
.empty-state {
  padding: 60px 20px;
  text-align: center;
}

.empty-state :deep(.el-empty__description) {
  color: #718096;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .title-content {
    padding: 0 20px;
    flex-direction: column;
    text-align: center;
    gap: 30px;
  }
  
  .main-content {
    padding: 0 20px;
  }
}

@media (max-width: 768px) {
  .page-title-section {
    padding: 30px 0 50px 0;
  }
  
  .title-text h1 {
    font-size: 2rem;
  }
  
  .title-icon {
    width: 60px;
    height: 60px;
    font-size: 28px;
  }
}
</style>