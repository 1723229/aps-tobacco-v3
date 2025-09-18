<template>
  <div class="monthly-plan-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-text">
          <div class="breadcrumb">
            <el-breadcrumb separator=">">
              <el-breadcrumb-item @click="$router.push('/monthly-plan/entry')">月度计划录入</el-breadcrumb-item>
              <el-breadcrumb-item>{{ batchId }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <h1>
            <i class="fas fa-file-alt"></i>
            月度计划详情
          </h1>
          <p class="page-description">
            查看月度计划导入详情、数据质量分析和处理结果
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" icon="Setting" @click="goToScheduling" :disabled="!canSchedule">
            开始排产
          </el-button>
          <el-button icon="Refresh" @click="refreshData">
            刷新
          </el-button>
        </div>
      </div>
    </div>

    <!-- 导入概况卡片 -->
    <div class="overview-section">
      <div class="overview-cards">
        <div class="overview-card file-info">
          <div class="card-icon">
            <i class="fas fa-file-excel"></i>
          </div>
          <div class="card-content">
            <h3>文件信息</h3>
            <div class="file-details">
              <div class="detail-item">
                <span class="label">文件名：</span>
                <span class="value">{{ importDetail.file_name }}</span>
              </div>
              <div class="detail-item">
                <span class="label">文件大小：</span>
                <span class="value">{{ formatFileSize(importDetail.file_size) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">上传时间：</span>
                <span class="value">{{ formatDateTime(importDetail.upload_time) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="overview-card status-info">
          <div class="card-icon">
            <i class="fas fa-chart-pie"></i>
          </div>
          <div class="card-content">
            <h3>处理状态</h3>
            <div class="status-details">
              <div class="status-item">
                <el-tag :type="getStatusColor(importDetail.status)" size="large">
                  {{ getStatusText(importDetail.status) }}
                </el-tag>
              </div>
              <div class="progress-info">
                <span class="label">数据质量评分：</span>
                <el-progress 
                  :percentage="importDetail.processing_summary?.data_quality_score || 0"
                  :color="getQualityColor(importDetail.processing_summary?.data_quality_score)"
                  :stroke-width="8"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="overview-card records-info">
          <div class="card-icon">
            <i class="fas fa-database"></i>
          </div>
          <div class="card-content">
            <h3>记录统计</h3>
            <div class="records-stats">
              <div class="stat-item">
                <span class="number">{{ importDetail.total_records }}</span>
                <span class="label">总记录数</span>
              </div>
              <div class="stat-item valid">
                <span class="number">{{ importDetail.valid_records }}</span>
                <span class="label">有效记录</span>
              </div>
              <div class="stat-item error" v-if="importDetail.error_records > 0">
                <span class="number">{{ importDetail.error_records }}</span>
                <span class="label">错误记录</span>
              </div>
              <div class="stat-item warning" v-if="importDetail.warning_records > 0">
                <span class="number">{{ importDetail.warning_records }}</span>
                <span class="label">警告记录</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 处理摘要 -->
    <div class="summary-section">
      <el-card>
        <template #header>
          <h3>
            <i class="fas fa-analytics"></i>
            处理摘要
          </h3>
        </template>
        <div class="summary-content">
          <div class="summary-grid">
            <div class="summary-item">
              <div class="summary-label">解析用时：</div>
              <div class="summary-value">{{ importDetail.processing_summary?.parsing_duration || '未知' }}</div>
            </div>
            <div class="summary-item">
              <div class="summary-label">验证错误：</div>
              <div class="summary-value">{{ importDetail.processing_summary?.validation_errors || 0 }} 个</div>
            </div>
            <div class="summary-item">
              <div class="summary-label">数据质量：</div>
              <div class="summary-value">{{ importDetail.processing_summary?.data_quality_score || 0 }}%</div>
            </div>
          </div>
          
          <div v-if="importDetail.processing_summary?.recommended_actions?.length" class="recommendations">
            <h4>建议操作：</h4>
            <ul>
              <li v-for="action in importDetail.processing_summary.recommended_actions" :key="action">
                {{ action }}
              </li>
            </ul>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 错误详情 -->
    <div v-if="importDetail.error_records > 0" class="errors-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <h3>
              <i class="fas fa-exclamation-triangle"></i>
              错误详情 ({{ importDetail.error_records }} 个)
            </h3>
            <el-button type="text" icon="Download" @click="exportErrors">
              导出错误报告
            </el-button>
          </div>
        </template>
        <el-table
          :data="importDetail.error_details"
          style="width: 100%"
        >
          <el-table-column prop="row_number" label="行号" width="80" />
          <el-table-column prop="work_order_nr" label="工单号" width="150" />
          <el-table-column prop="error_message" label="错误信息" min-width="300" />
        </el-table>
      </el-card>
    </div>

    <!-- 警告详情 -->
    <div v-if="importDetail.warning_records > 0" class="warnings-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <h3>
              <i class="fas fa-exclamation-circle"></i>
              警告详情 ({{ importDetail.warning_records }} 个)
            </h3>
          </div>
        </template>
        <el-table
          :data="importDetail.warning_details"
          style="width: 100%"
        >
          <el-table-column prop="row_number" label="行号" width="80" />
          <el-table-column prop="work_order_nr" label="工单号" width="150" />
          <el-table-column prop="warning_message" label="警告信息" min-width="300" />
        </el-table>
      </el-card>
    </div>

    <!-- 月度计划数据预览 -->
    <div class="data-preview-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <h3>
              <i class="fas fa-table"></i>
              数据预览
            </h3>
            <div class="header-actions">
              <el-button type="text" icon="View" @click="viewFullData">
                查看完整数据
              </el-button>
            </div>
          </div>
        </template>
        
        <div v-loading="loadingPreview">
          <el-table
            :data="previewData"
            style="width: 100%"
            :empty-text="previewData.length === 0 ? '暂无数据' : ''"
          >
            <el-table-column prop="monthly_work_order_nr" label="工单号" width="150" />
            <el-table-column prop="monthly_product_name" label="产品名称" min-width="200" />
            <el-table-column prop="monthly_machine_code" label="机台编码" width="120" />
            <el-table-column prop="monthly_target_quantity" label="目标产量" width="120">
              <template #default="scope">
                {{ formatNumber(scope.row.monthly_target_quantity) }}
              </template>
            </el-table-column>
            <el-table-column prop="monthly_plan_start_date" label="计划开始" width="120">
              <template #default="scope">
                {{ formatDate(scope.row.monthly_plan_start_date) }}
              </template>
            </el-table-column>
            <el-table-column prop="monthly_plan_end_date" label="计划结束" width="120">
              <template #default="scope">
                {{ formatDate(scope.row.monthly_plan_end_date) }}
              </template>
            </el-table-column>
            <el-table-column prop="monthly_validation_status" label="状态" width="100">
              <template #default="scope">
                <el-tag
                  size="small"
                  :type="getValidationStatusColor(scope.row.monthly_validation_status)"
                >
                  {{ getValidationStatusText(scope.row.monthly_validation_status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 预览分页 -->
          <div class="preview-pagination">
            <el-pagination
              v-model:current-page="previewPagination.page"
              v-model:page-size="previewPagination.pageSize"
              :page-sizes="[10, 20, 50]"
              :total="previewPagination.total"
              layout="total, sizes, prev, pager, next"
              @size-change="handlePreviewSizeChange"
              @current-change="handlePreviewCurrentChange"
            />
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const loadingPreview = ref(false)
const importDetail = ref<any>({})
const previewData = ref<any[]>([])

// 获取批次ID
const batchId = computed(() => route.params.batchId as string)

// 预览分页
const previewPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 计算属性
const canSchedule = computed(() => {
  return importDetail.value.status === 'COMPLETED' && importDetail.value.valid_records > 0
})

// 生命周期
onMounted(() => {
  loadImportDetail()
  loadPreviewData()
})

// 方法
const loadImportDetail = async () => {
  loading.value = true
  try {
    const response = await api.get(`/api/v1/monthly-data/imports/${batchId.value}`)
    
    if (response.data.code === 200) {
      importDetail.value = response.data.data
    } else {
      throw new Error(response.data.message || '加载详情失败')
    }
  } catch (error: any) {
    console.error('加载导入详情失败:', error)
    ElMessage.error('加载导入详情失败: ' + (error.message || '请检查网络连接'))
  } finally {
    loading.value = false
  }
}

const loadPreviewData = async () => {
  loadingPreview.value = true
  try {
    const response = await api.get('/api/v1/monthly-plans', {
      params: {
        batch_id: batchId.value,
        page: previewPagination.page,
        page_size: previewPagination.pageSize
      }
    })

    if (response.data.code === 200) {
      previewData.value = response.data.data.plans || []
      previewPagination.total = response.data.data.pagination?.total_count || 0
    }
  } catch (error) {
    console.error('加载预览数据失败:', error)
  } finally {
    loadingPreview.value = false
  }
}

const refreshData = () => {
  loadImportDetail()
  loadPreviewData()
}

const goToScheduling = () => {
  router.push(`/monthly-scheduling?batch_id=${batchId.value}`)
}

const exportErrors = () => {
  ElMessage.info('错误报告导出功能开发中...')
}

const viewFullData = () => {
  // 打开新页面查看完整数据
  const routeData = router.resolve({
    path: '/monthly-plan/data',
    query: { batch_id: batchId.value }
  })
  window.open(routeData.href, '_blank')
}

// 预览分页处理
const handlePreviewSizeChange = (val: number) => {
  previewPagination.pageSize = val
  loadPreviewData()
}

const handlePreviewCurrentChange = (val: number) => {
  previewPagination.page = val
  loadPreviewData()
}

// 辅助方法
const formatFileSize = (bytes: number) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return date.split('T')[0]
}

const formatNumber = (num: number) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'UPLOADED': 'info',
    'PARSING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger'
  }
  return colors[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'UPLOADED': '已上传',
    'PARSING': '解析中',
    'COMPLETED': '已完成',
    'FAILED': '失败'
  }
  return texts[status] || status
}

const getQualityColor = (score: number) => {
  if (score >= 90) return '#67c23a'
  if (score >= 70) return '#e6a23c'
  return '#f56c6c'
}

const getValidationStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'VALID': 'success',
    'WARNING': 'warning',
    'ERROR': 'danger'
  }
  return colors[status] || 'info'
}

const getValidationStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'VALID': '有效',
    'WARNING': '警告',
    'ERROR': '错误'
  }
  return texts[status] || status
}
</script>

<style scoped>
.monthly-plan-detail {
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

.breadcrumb {
  margin-bottom: 8px;
}

.breadcrumb :deep(.el-breadcrumb__item) {
  cursor: pointer;
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

.overview-section {
  margin-bottom: 32px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 24px;
}

.overview-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  transition: all 0.3s ease;
}

.overview-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #fff;
  flex-shrink: 0;
}

.file-info .card-icon {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.status-info .card-icon {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.records-info .card-icon {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
}

.card-content {
  flex: 1;
}

.card-content h3 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.file-details, .status-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
}

.detail-item .label {
  color: #909399;
  font-size: 14px;
  min-width: 80px;
}

.detail-item .value {
  color: #303133;
  font-size: 14px;
  font-weight: 500;
}

.status-item {
  margin-bottom: 12px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-info .label {
  color: #909399;
  font-size: 14px;
  min-width: 100px;
}

.records-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.stat-item.valid {
  background: #f0f9ff;
  border: 1px solid #67c23a;
}

.stat-item.error {
  background: #fef0f0;
  border: 1px solid #f56c6c;
}

.stat-item.warning {
  background: #fdf6ec;
  border: 1px solid #e6a23c;
}

.stat-item .number {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.stat-item .label {
  font-size: 12px;
  color: #909399;
}

.summary-section, .errors-section, .warnings-section, .data-preview-section {
  margin-bottom: 32px;
}

.summary-content {
  padding: 16px 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.summary-item {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.summary-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.summary-value {
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.recommendations {
  background: #f0f9ff;
  border: 1px solid #409eff;
  border-radius: 8px;
  padding: 16px;
}

.recommendations h4 {
  margin: 0 0 12px 0;
  color: #409eff;
  font-size: 16px;
}

.recommendations ul {
  margin: 0;
  padding-left: 20px;
}

.recommendations li {
  color: #606266;
  margin-bottom: 4px;
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

.header-actions {
  display: flex;
  gap: 12px;
}

.preview-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .monthly-plan-detail {
    padding: 16px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .overview-cards {
    grid-template-columns: 1fr;
  }
  
  .overview-card {
    padding: 20px;
  }
  
  .card-icon {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }
  
  .records-stats {
    grid-template-columns: 1fr;
  }
  
  .summary-grid {
    grid-template-columns: 1fr;
  }
  
  .section-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}
</style>