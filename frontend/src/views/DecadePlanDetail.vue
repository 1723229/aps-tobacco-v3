<template>
  <div class="decade-plan-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-button text @click="goBack" class="back-button">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h1 class="page-title">
            <el-icon><Grid /></el-icon>
            旬计划详情
          </h1>
          <p class="page-subtitle">批次ID: {{ batchId }}</p>
        </div>
        <div class="header-right">
          <el-button @click="refreshData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-button type="primary" @click="exportData">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
        </div>
      </div>
    </div>

    <!-- 批次信息概览 -->
    <div class="batch-overview">
      <el-card class="modern-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon">
              <el-icon><InfoFilled /></el-icon>
            </div>
            <span class="header-title">批次信息</span>
          </div>
        </template>

        <!-- 主要信息网格 -->
        <div class="info-grid">
          <div class="info-card">
            <div class="info-icon batch-icon">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="info-content">
              <div class="info-label">批次ID</div>
              <div class="info-value">{{ batchInfo?.batch_id || '暂无数据' }}</div>
            </div>
          </div>

          <div class="info-card">
            <div class="info-icon file-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="info-content">
              <div class="info-label">文件名</div>
              <div class="info-value" :title="batchInfo?.file_name">{{ batchInfo?.file_name || '暂无数据' }}</div>
            </div>
          </div>

          <div class="info-card">
            <div class="info-icon time-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="info-content">
              <div class="info-label">上传时间</div>
              <div class="info-value">{{ formatDateTime(batchInfo?.upload_time) || '暂无数据' }}</div>
            </div>
          </div>

          <div class="info-card">
            <div class="info-icon size-icon">
              <el-icon><Folder /></el-icon>
            </div>
            <div class="info-content">
              <div class="info-label">文件大小</div>
              <div class="info-value">{{ batchInfo?.file_size ? formatFileSize(batchInfo.file_size) : '暂无数据' }}</div>
            </div>
          </div>
        </div>

        <!-- 统计数据 -->
        <div class="stats-section">
          <h3 class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            数据统计
          </h3>
          <div class="stats-grid" v-if="statisticsData">
            <div class="stat-card total-card">
              <div class="stat-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statisticsData.total_records || 0 }}</div>
                <div class="stat-label">总记录数</div>
              </div>
            </div>

            <div class="stat-card success-card">
              <div class="stat-icon">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statisticsData.valid_records || 0 }}</div>
                <div class="stat-label">有效记录</div>
              </div>
            </div>

            <div class="stat-card warning-card">
              <div class="stat-icon">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statisticsData.warning_records || 0 }}</div>
                <div class="stat-label">警告记录</div>
              </div>
            </div>

            <div class="stat-card error-card">
              <div class="stat-icon">
                <el-icon><CircleClose /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statisticsData.error_records || 0 }}</div>
                <div class="stat-label">错误记录</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 处理状态 -->
        <div class="status-section">
          <h3 class="section-title">
            <el-icon><Setting /></el-icon>
            处理状态
          </h3>
          <div class="status-content" v-if="batchInfo">
            <div class="status-item-modern">
              <span class="status-label">当前状态</span>
              <el-tag :type="getStatusColor(batchInfo.status)" size="large" class="status-tag">
                {{ getStatusText(batchInfo.status) }}
              </el-tag>
            </div>
            <div v-if="batchInfo.processed_time" class="status-item-modern">
              <span class="status-label">处理时间</span>
              <span class="status-value">{{ formatDateTime(batchInfo.processed_time) }}</span>
            </div>
            <div v-if="batchInfo.processing_duration" class="status-item-modern">
              <span class="status-label">处理耗时</span>
              <span class="status-value">{{ batchInfo.processing_duration }}s</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 旬计划数据表格 -->
    <div class="data-table-section">
      <DecadePlanTable :import-batch-id="batchId" />
    </div>

    <!-- 错误日志 -->
    <div v-if="errorLogs.length > 0" class="error-logs">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-icon><Warning /></el-icon>
            <span>错误日志</span>
            <el-tag type="danger" size="small">{{ errorLogs.length }} 条错误</el-tag>
          </div>
        </template>

        <el-table
          :data="paginatedErrors"
          style="width: 100%"
          size="small"
          stripe
        >
          <el-table-column
            prop="row_number"
            label="行号"
            width="80"
            align="center"
          />
          <el-table-column
            prop="column_name"
            label="列名"
            width="120"
          />
          <el-table-column
            prop="error_type"
            label="错误类型"
            width="120"
          >
            <template #default="{ row }">
              <el-tag type="danger" size="small">{{ row.error_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="error_message"
            label="错误描述"
            show-overflow-tooltip
          />
          <el-table-column
            prop="original_value"
            label="原始值"
            width="150"
            show-overflow-tooltip
          />
        </el-table>

        <!-- 错误日志分页 -->
        <div class="error-pagination">
          <el-pagination
            v-model:current-page="errorPage"
            v-model:page-size="errorPageSize"
            :page-sizes="[10, 20, 50]"
            :small="true"
            layout="total, sizes, prev, pager, next"
            :total="errorLogs.length"
          />
        </div>
      </el-card>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Grid,
  Refresh,
  Download,
  InfoFilled,
  Warning,
  Clock,
  Document,
  Folder,
  DataAnalysis,
  CircleCheck,
  CircleClose,
  Setting
} from '@element-plus/icons-vue'
import DecadePlanTable from '@/components/DecadePlanTable.vue'
import DecadePlanAPI from '@/services/api'
import {
  formatDateTime,
  formatFileSize,
  getStatusColor,
  getStatusText
} from '@/utils'
import type { DecadePlansResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()

// 获取批次ID
const batchId = route.params.batchId as string

// 响应式数据
const loading = ref(false)
const batchInfo = ref<any>(null)
const statisticsData = ref<any>(null)
const errorLogs = ref<any[]>([])
const operationHistory = ref([
  {
    type: 'upload',
    title: '文件上传',
    description: '用户上传了文件 "APS作业计划表（卷包旬计划）--导入.xlsx"',
    timestamp: '2024-12-16 14:30:25',
    user: '系统管理员'
  },
  {
    type: 'parse',
    title: '开始解析',
    description: '系统开始解析上传的Excel文件',
    timestamp: '2024-12-16 14:30:30',
    user: '系统'
  },
  {
    type: 'success',
    title: '解析完成',
    description: '文件解析成功，共处理 156 条记录，其中有效记录 150 条',
    timestamp: '2024-12-16 14:31:05',
    user: '系统'
  }
])

// 错误日志分页
const errorPage = ref(1)
const errorPageSize = ref(20)

const paginatedErrors = computed(() => {
  const start = (errorPage.value - 1) * errorPageSize.value
  const end = start + errorPageSize.value
  return errorLogs.value.slice(start, end)
})

// 方法
const goBack = () => {
  router.go(-1)
}

const loadBatchData = async () => {
  if (!batchId) return

  try {
    loading.value = true

    // 并行加载旬计划数据、状态信息和历史记录（为了获取文件大小）
    const [plansResponse, statusResponse, historyResponse] = await Promise.all([
      DecadePlanAPI.getDecadePlans(batchId),
      DecadePlanAPI.getParseStatus(batchId),
      DecadePlanAPI.getUploadHistory(1, 100).catch(() => ({ data: { records: [] } })) // 获取历史记录来找文件大小
    ])

    if (plansResponse.code === 200) {
      const plans = plansResponse.data.plans || []

      // 计算统计数据
      const total = plans.length
      const valid = plans.filter(p => p.validation_status === 'VALID').length
      const warning = plans.filter(p => p.validation_status === 'WARNING').length
      const error = plans.filter(p => p.validation_status === 'ERROR').length

      statisticsData.value = {
        total_records: total,
        valid_records: valid,
        warning_records: warning,
        error_records: error
      }
    }

    // 使用真实的状态信息
    if (statusResponse.code === 200) {
      const statusData = statusResponse.data
      console.log('Status data received:', statusData)

      // 从历史记录中查找当前批次的文件大小和上传时间
      let fileSize = 0
      let uploadTime = statusData.created_time || ''

      if (historyResponse.data?.records) {
        console.log('History records:', historyResponse.data.records)
        const historyRecord = historyResponse.data.records.find(record => record.batch_id === batchId)
        console.log('Found history record:', historyRecord)
        if (historyRecord) {
          fileSize = historyRecord.file_size || 0
          uploadTime = historyRecord.upload_time || statusData.created_time || ''
        }
      }

      console.log('Final values - fileSize:', fileSize, 'uploadTime:', uploadTime)

      batchInfo.value = {
        batch_id: batchId,
        file_name: statusData.file_name || '未知文件名',
        file_size: fileSize,
        upload_time: uploadTime,
        processed_time: statusData.import_end_time || '',
        processing_duration: statusData.import_start_time && statusData.import_end_time
          ? Math.round((new Date(statusData.import_end_time).getTime() - new Date(statusData.import_start_time).getTime()) / 1000)
          : 0,
        status: statusData.import_status || 'UNKNOWN'
      }

      console.log('Final batchInfo:', batchInfo.value)
    }

    // 如果有错误记录，模拟错误日志（实际应该从API获取）
    if (statisticsData.value?.error_records && statisticsData.value.error_records > 0) {
      errorLogs.value = [
        {
          row_number: 45,
          column_name: '投料总量',
          error_type: 'VALIDATION_ERROR',
          error_message: '数值格式不正确，应为数字',
          original_value: 'ABC123'
        },
        {
          row_number: 78,
          column_name: '计划开始时间',
          error_type: 'FORMAT_ERROR',
          error_message: '日期格式不正确',
          original_value: '2024/12/30'
        }
      ]
    }
  } catch (error) {
    console.error('加载批次数据失败:', error)
    ElMessage.error('加载数据失败，请重试')
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadBatchData()
  ElMessage.success('数据已刷新')
}

const exportData = () => {
  // TODO: 实现数据导出功能
  ElMessage.info('数据导出功能开发中...')
}

const getOperationColor = (type: string): string => {
  switch (type) {
    case 'upload':
      return 'primary'
    case 'parse':
      return 'warning'
    case 'success':
      return 'success'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
}

// 生命周期
onMounted(() => {
  if (!batchId) {
    ElMessage.error('缺少批次ID参数')
    router.push('/')
    return
  }

  loadBatchData()
})
</script>

<style scoped>
.decade-plan-detail {
  padding: 20px;
  max-width: 1400px;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

.header-left .page-subtitle {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.batch-overview {
  margin-bottom: 24px;
}

.modern-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 6px 30px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 24px;
  margin: -20px -24px 24px -24px;
}

.header-icon {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.header-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.info-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid #e8eaed;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.info-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(45deg, #667eea, #764ba2);
}

.info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
  border-color: #667eea;
}

.info-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-right: 16px;
  flex-shrink: 0;
}

.batch-icon {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.file-icon {
  background: linear-gradient(135deg, #f093fb, #f5576c);
  color: white;
}

.time-icon {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  color: white;
}

.size-icon {
  background: linear-gradient(135deg, #43e97b, #38f9d7);
  color: white;
}

.info-content {
  flex: 1;
  min-width: 0;
}

.info-label {
  font-size: 13px;
  color: #8b949e;
  margin-bottom: 6px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 16px;
  color: #24292f;
  font-weight: 700;
  word-break: break-all;
  line-height: 1.4;
}

/* 统计数据部分 */
.stats-section {
  margin-bottom: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #24292f;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f1f3f4;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 24px 20px;
  border-radius: 12px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.total-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border: 1px solid #e1e4e8;
}

.total-card::before {
  background: linear-gradient(90deg, #6c757d, #495057);
}

.success-card {
  background: linear-gradient(135deg, #f0f9f1 0%, #ffffff 100%);
  border: 1px solid #d4edda;
}

.success-card::before {
  background: linear-gradient(90deg, #28a745, #20c997);
}

.warning-card {
  background: linear-gradient(135deg, #fff8e1 0%, #ffffff 100%);
  border: 1px solid #ffeaa7;
}

.warning-card::before {
  background: linear-gradient(90deg, #ffc107, #fd7e14);
}

.error-card {
  background: linear-gradient(135deg, #ffeaea 0%, #ffffff 100%);
  border: 1px solid #f5c6cb;
}

.error-card::before {
  background: linear-gradient(90deg, #dc3545, #e74c3c);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin-right: 16px;
  flex-shrink: 0;
}

.total-card .stat-icon {
  background: linear-gradient(135deg, #6c757d, #495057);
  color: white;
}

.success-card .stat-icon {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
}

.warning-card .stat-icon {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: white;
}

.error-card .stat-icon {
  background: linear-gradient(135deg, #dc3545, #e74c3c);
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6c757d;
  font-weight: 500;
}

/* 状态部分 */
.status-section {
  margin-bottom: 0;
}

.status-content {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid #e8eaed;
}

.status-item-modern {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 150px;
}

.status-label {
  font-size: 13px;
  color: #8b949e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-value {
  font-size: 15px;
  color: #24292f;
  font-weight: 600;
}

.status-tag {
  align-self: flex-start;
  padding: 8px 16px;
  font-weight: 600;
  border-radius: 8px;
}

.data-table-section {
  margin-bottom: 24px;
}

.error-logs {
  margin-bottom: 24px;
}

.error-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.operation-history {
  margin-bottom: 24px;
}

.operation-content {
  padding: 8px 0;
}

.operation-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.operation-description {
  color: #606266;
  font-size: 14px;
  margin-bottom: 4px;
}

.operation-user {
  color: #909399;
  font-size: 12px;
}

.empty-timeline {
  text-align: center;
  padding: 40px 0;
}

:deep(.el-statistic__number) {
  font-size: 20px;
  font-weight: 600;
}

:deep(.el-statistic__title) {
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
