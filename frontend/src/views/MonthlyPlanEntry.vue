<template>
  <div class="monthly-plan-entry">
    <!-- 页面标题区 -->
    <div class="page-title-section">
      <div class="title-content">
        <div class="title-left">
          <div class="title-icon">
            <el-icon><Calendar /></el-icon>
          </div>
          <div class="title-text">
            <h1>月度生产计划录入</h1>
            <p>上传Excel文件进行月度生产计划数据录入与解析，支持完整的月度排产功能</p>
          </div>
        </div>
        <div class="title-actions">
          <el-button type="primary" @click="$router.push('/monthly-scheduling')">
            <el-icon><Setting /></el-icon>
            月度排产管理
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
              <span class="header-title">月度计划文件上传</span>
            </div>
          </template>

          <!-- 文件上传提示 -->
          <div class="upload-notice">
            <el-alert
              title="月度计划录入说明"
              type="info"
              :closable="false"
              show-icon
            >
              <div class="notice-content">
                <p>请上传标准的月度计划Excel文件（.xlsx格式），文件大小不超过50MB。</p>
                <p>系统将自动解析文件内容并生成月度计划记录，包括产品信息、产量目标等信息。</p>
              </div>
            </el-alert>
          </div>

        <!-- 文件上传组件 -->
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            class="monthly-upload"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
            :accept="'.xlsx,.xls'"
            :multiple="false"
            :show-file-list="false"
          >
            <div class="upload-content">
              <div class="upload-icon">
                <i class="fas fa-file-excel"></i>
              </div>
              <div class="upload-text">
                <p class="primary-text">将月度计划文件拖到此处，或<em>点击上传</em></p>
                <p class="secondary-text">支持 .xlsx、.xls 格式，文件大小不超过 50MB</p>
              </div>
            </div>
          </el-upload>

          <!-- 选中的文件信息 -->
          <div v-if="selectedFile" class="file-info">
            <div class="file-card">
              <div class="file-icon">
                <i class="fas fa-file-excel"></i>
              </div>
              <div class="file-details">
                <div class="file-name">{{ selectedFile.name }}</div>
                <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
              </div>
              <div class="file-actions">
                <el-button type="danger" size="small" icon="Delete" @click="removeFile">
                  移除
                </el-button>
              </div>
            </div>

            <!-- 上传进度 -->
            <div v-if="uploadProgress.show" class="upload-progress">
              <el-progress
                :percentage="uploadProgress.percentage"
                :status="uploadProgress.status"
                :stroke-width="8"
                :format="(percent: number) => `${percent.toFixed(2)}%`"
              />
              <div class="progress-text">{{ uploadProgress.text }}</div>
            </div>

            <!-- 上传按钮 -->
            <div v-if="!uploadProgress.show" class="upload-actions">
              <el-button
                type="primary"
                size="large"
                icon="Upload"
                :loading="uploading"
                @click="startUpload"
              >
                开始上传
              </el-button>
            </div>
          </div>
        </div>
        </el-card>
      </div>

      <!-- 最近上传记录 -->
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
                  type="text"
                  icon="Refresh"
                  @click="loadRecentUploads"
                  :loading="loadingRecords"
                  size="small"
                >
                  刷新
                </el-button>
                <el-button
                  :type="showHistory ? 'primary' : 'default'"
                  @click="toggleHistory"
                  size="small"
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

          <div v-loading="loadingRecords" v-show="showHistory" class="history-content">
            <el-table
              :data="recentUploads"
              style="width: 100%"
              :empty-text="recentUploads.length === 0 ? '暂无月度计划上传记录' : ''"
              class="modern-table"
              size="default"
            >
            <el-table-column prop="batch_id" label="批次ID" width="200">
              <template #default="scope">
                <el-tag size="small" type="info">{{ scope.row.batch_id }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="file_name" label="文件名" min-width="250">
              <template #default="scope">
                <div class="file-cell">
                  <i class="fas fa-file-excel file-icon"></i>
                  <span>{{ scope.row.file_name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="upload_time" label="上传时间" width="180">
              <template #default="scope">
                {{ formatDateTime(scope.row.upload_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="file_size" label="文件大小" width="120">
              <template #default="scope">
                {{ formatFileSize(scope.row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="record_count" label="记录数" width="100">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.record_count > 0 ? 'success' : 'warning'">
                  {{ scope.row.record_count }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="scope">
                <el-tag
                  size="small"
                  :type="getStatusColor(scope.row.status)"
                >
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <div class="action-buttons">
                  <el-button
                    size="small"
                    type="primary"
                    icon="View"
                    @click="viewDetails(scope.row)"
                  >
                    查看详情
                  </el-button>
                  <el-button
                    v-if="scope.row.status === 'completed' && scope.row.record_count > 0"
                    size="small"
                    type="success"
                    icon="Setting"
                    @click="goToScheduling(scope.row)"
                  >
                    月度排产
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

            <div v-if="recentUploads.length === 0 && !loadingRecords" class="empty-state">
              <el-empty description="暂无上传记录" />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Calendar, Setting, Upload, Clock } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()

// 响应式数据
const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const loadingRecords = ref(false)
const recentUploads = ref<any[]>([])
const showHistory = ref(true) // 默认展示历史记录

// 上传进度
const uploadProgress = reactive({
  show: false,
  percentage: 0,
  status: '' as any,
  text: ''
})

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 生命周期
onMounted(() => {
  loadRecentUploads()
})

// 文件处理方法
const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file: File) => {
  const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                 file.type === 'application/vnd.ms-excel'
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isExcel) {
    ElMessage.error('只能上传Excel文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('上传文件大小不能超过50MB!')
    return false
  }
  return true
}

const removeFile = () => {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}

const startUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.show = true
  uploadProgress.percentage = 0
  uploadProgress.status = ''
  uploadProgress.text = '准备上传...'

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.percentage < 90) {
        const increment = Math.random() * 10 + 2 // 2-12之间的随机增量
        uploadProgress.percentage = Math.min(90, Number((uploadProgress.percentage + increment).toFixed(2)))
      }
    }, 300)

    uploadProgress.text = '正在上传文件...'

    // 调用月度计划上传API
    const response = await api.post('/api/v1/monthly-data/uploads', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    clearInterval(progressInterval)
    uploadProgress.percentage = 100.00
    uploadProgress.status = 'success'
    uploadProgress.text = '上传成功！'

    if (response.data.code === 200) {
      ElMessage.success('月度计划文件上传成功！')

      // 重置状态
      setTimeout(() => {
        selectedFile.value = null
        uploadProgress.show = false
        uploadRef.value?.clearFiles()
        loadRecentUploads()
      }, 2000)
    } else {
      throw new Error(response.data.message || '上传失败')
    }

  } catch (error: any) {
    console.error('上传失败:', error)
    uploadProgress.status = 'exception'

    // 处理重复文件名等400错误
    if (error?.response?.status === 400) {
      const errorMessage = error.response.data?.detail || error.response.data?.message || '上传失败'
      uploadProgress.text = '上传失败: ' + errorMessage
      ElMessage.error(errorMessage)
    } else {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '网络错误'
      uploadProgress.text = '上传失败: ' + errorMessage
      ElMessage.error('文件上传失败: ' + errorMessage)
    }
  } finally {
    uploading.value = false
  }
}

// 数据加载方法
const loadRecentUploads = async () => {
  loadingRecords.value = true
  try {
    const response = await api.get('/api/v1/monthly-data/imports', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        sort_by: 'created_time',
        sort_order: 'desc'
      }
    })

    if (response.data.code === 200) {
      recentUploads.value = response.data.data.imports || []
      pagination.total = response.data.data.pagination?.total_count || 0

      // 映射字段名称以匹配前端表格显示
      recentUploads.value = recentUploads.value.map((item: any) => ({
        ...item,
        batch_id: item.monthly_batch_id,
        record_count: item.total_records
      }))
    }
  } catch (error) {
    console.error('加载上传记录失败:', error)
    ElMessage.error('加载上传记录失败')
  } finally {
    loadingRecords.value = false
  }
}

// 分页处理
const handleSizeChange = (val: number) => {
  pagination.pageSize = val
  loadRecentUploads()
}

const handleCurrentChange = (val: number) => {
  pagination.page = val
  loadRecentUploads()
}

// 操作方法
const viewDetails = (row: any) => {
  router.push(`/monthly-plan/detail/${row.batch_id}`)
}

const goToScheduling = (row: any) => {
  router.push(`/monthly-scheduling?batch_id=${row.batch_id}`)
}

// 展开/收起控制
const toggleHistory = () => {
  showHistory.value = !showHistory.value
  if (showHistory.value && recentUploads.value.length === 0) {
    loadRecentUploads()
  }
}

// 辅助方法
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'pending': 'warning',
    'processing': 'primary',
    'completed': 'success',
    'failed': 'danger'
  }
  return colors[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return texts[status] || status
}
</script>

<style scoped>
.monthly-plan-entry {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 0;
  border: none !important;
  outline: none !important;
}

/* Remove any yellow borders/outlines globally */
.monthly-plan-entry *,
.monthly-plan-entry *::before,
.monthly-plan-entry *::after {
  border-color: transparent !important;
  outline: none !important;
}

.monthly-plan-entry *:focus {
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
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 展开/收起图标样式 */
.expand-icon {
  transition: transform 0.3s ease;
  margin-left: 4px;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.upload-notice {
  margin-bottom: 24px;
}

.notice-content p {
  margin: 4px 0;
  line-height: 1.6;
}

.upload-area {
  text-align: center;
}

.monthly-upload {
  width: 100%;
}

.upload-content {
  padding: 40px 20px;
}

.upload-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

.upload-text .primary-text {
  font-size: 16px;
  color: #303133;
  margin: 0 0 8px 0;
}

.upload-text .primary-text em {
  color: #409eff;
  font-style: normal;
}

.upload-text .secondary-text {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.file-info {
  margin-top: 24px;
  text-align: left;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.file-icon {
  font-size: 32px;
  color: #67c23a;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.file-size {
  color: #909399;
  font-size: 14px;
}

.upload-progress {
  margin-bottom: 16px;
}

.progress-text {
  text-align: center;
  margin-top: 8px;
  color: #606266;
  font-size: 14px;
}

.upload-actions {
  text-align: center;
}

.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-cell .file-icon {
  color: #67c23a;
  font-size: 16px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
}

/* 表格样式 */
.modern-table {
  border-radius: 12px;
  overflow: hidden;
}

.modern-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
}

.modern-table :deep(.el-table__header) {
  background: transparent;
}

.modern-table :deep(.el-table__header th) {
  background: transparent;
  border-bottom: 1px solid #e8eaed;
  color: #2d3748;
  font-weight: 600;
}

.modern-table :deep(.el-table__row) {
  transition: all 0.3s ease;
}

.modern-table :deep(.el-table__row:hover > td) {
  background-color: #f8f9ff !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .monthly-plan-entry {
    padding: 0;
  }

  .title-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
    padding: 0 20px;
  }

  .title-left {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .title-icon {
    width: 60px;
    height: 60px;
    font-size: 24px;
    align-self: center;
  }

  .title-text h1 {
    font-size: 1.8rem;
  }

  .title-text p {
    font-size: 1rem;
  }

  .main-content {
    padding: 0 20px;
    transform: translateY(-20px);
  }

  .upload-card :deep(.el-card__body) {
    padding: 24px 20px;
  }

  .history-content {
    padding: 20px;
  }

  .file-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .page-title-section {
    background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  }

  .title-text h1 {
    color: #f7fafc;
  }

  .title-text p {
    color: #e2e8f0;
  }

  .upload-card,
  .history-card {
    background: #2d3748;
    color: #f7fafc;
  }

  .file-card {
    background: #4a5568;
  }
}
</style>
