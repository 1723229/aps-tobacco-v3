<template>
  <div class="monthly-plan-entry">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-text">
          <h1>
            <i class="fas fa-calendar-plus"></i>
            月度生产计划录入
          </h1>
          <p class="page-description">
            上传Excel文件进行月度生产计划数据录入与解析，支持完整的月度排产功能
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" icon="List" @click="$router.push('/monthly-scheduling')">
            月度排产管理
          </el-button>
        </div>
      </div>
    </div>

    <!-- 月度计划录入区域 -->
    <div class="upload-section">
      <el-card class="upload-card">
        <template #header>
          <div class="upload-header">
            <div class="header-icon">
              <i class="fas fa-cloud-upload-alt"></i>
            </div>
            <div class="header-info">
              <h2>月度计划文件上传</h2>
              <p>请上传标准的月度生产计划Excel文件</p>
            </div>
          </div>
        </template>

        <!-- 文件上传提示 -->
        <div class="upload-notice">
          <el-alert
            title="月度生产计划上传说明"
            type="info"
            :closable="false"
            show-icon
          >
            <div class="notice-content">
              <p><strong>支持的文件格式：</strong>.xlsx、.xls（文件大小不超过50MB）</p>
              <p><strong>文件内容要求：</strong>包含月度生产任务、产品信息、产量目标、机台安排等</p>
              <p><strong>处理功能：</strong>系统将自动解析文件并进行月度容量分析、工作日历匹配、资源优化分配</p>
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

    <!-- 月度计划功能介绍 -->
    <div class="features-section">
      <el-card>
        <template #header>
          <h3>
            <i class="fas fa-star"></i>
            月度计划功能特色
          </h3>
        </template>
        <div class="features-grid">
          <div class="feature-item">
            <div class="feature-icon calendar">
              <i class="fas fa-calendar-check"></i>
            </div>
            <div class="feature-content">
              <h4>工作日历集成</h4>
              <p>自动匹配工作日历，识别工作日、节假日和维护日，精确计算可用工时</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon capacity">
              <i class="fas fa-chart-line"></i>
            </div>
            <div class="feature-content">
              <h4>产能分析</h4>
              <p>智能分析月度产能需求，计算机台负荷，提供产能预警和优化建议</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon optimization">
              <i class="fas fa-cogs"></i>
            </div>
            <div class="feature-content">
              <h4>资源优化</h4>
              <p>基于约束条件进行资源优化分配，确保生产任务合理分布和机台高效利用</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon timeline">
              <i class="fas fa-clock"></i>
            </div>
            <div class="feature-content">
              <h4>时间线规划</h4>
              <p>生成详细的月度生产时间线，支持甘特图可视化和进度跟踪</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 最近上传记录 -->
    <div class="recent-uploads">
      <el-card>
        <template #header>
          <div class="section-header">
            <div class="header-left">
              <h3>
                <i class="fas fa-history"></i>
                最近上传记录
              </h3>
            </div>
            <div class="header-right">
              <el-button 
                type="text" 
                icon="Refresh" 
                @click="loadRecentUploads"
                :loading="loadingRecords"
              >
                刷新
              </el-button>
            </div>
          </div>
        </template>

        <div v-loading="loadingRecords">
          <el-table
            :data="recentUploads"
            style="width: 100%"
            :empty-text="recentUploads.length === 0 ? '暂无月度计划上传记录' : ''"
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
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()

// 响应式数据
const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const loadingRecords = ref(false)
const recentUploads = ref<any[]>([])

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
        uploadProgress.percentage += Math.random() * 20
        if (uploadProgress.percentage > 90) {
          uploadProgress.percentage = 90
        }
      }
    }, 200)

    uploadProgress.text = '正在上传文件...'

    // 调用月度计划上传API
    const response = await api.post('/api/v1/monthly-plans/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    clearInterval(progressInterval)
    uploadProgress.percentage = 100
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
    uploadProgress.text = '上传失败: ' + (error.message || '网络错误')
    ElMessage.error('文件上传失败: ' + (error.message || '请检查网络连接'))
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
  max-width: 1200px;
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

.upload-section {
  margin-bottom: 32px;
}

.upload-card {
  border-radius: 12px;
  overflow: hidden;
}

.upload-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.header-info h2 {
  margin: 0 0 4px 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.header-info p {
  margin: 0;
  color: #909399;
  font-size: 14px;
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

.features-section {
  margin-bottom: 32px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: #f0f2f5;
  transform: translateY(-2px);
}

.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  flex-shrink: 0;
}

.feature-icon.calendar {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.feature-icon.capacity {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.feature-icon.optimization {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
}

.feature-icon.timeline {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.feature-content h4 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.feature-content p {
  margin: 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.recent-uploads {
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

/* 响应式设计 */
@media (max-width: 768px) {
  .monthly-plan-entry {
    padding: 16px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .feature-item {
    padding: 16px;
  }
  
  .upload-content {
    padding: 24px 16px;
  }
  
  .upload-icon {
    font-size: 36px;
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
  .feature-item {
    background: #2d3748;
  }
  
  .feature-item:hover {
    background: #4a5568;
  }
  
  .file-card {
    background: #2d3748;
  }
}
</style>