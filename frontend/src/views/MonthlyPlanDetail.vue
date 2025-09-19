<template>
  <div class="monthly-plan-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-button text @click="goBack" class="back-button">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h1 class="page-title">
            <el-icon><Calendar /></el-icon>
            月度计划详情
          </h1>
          <p class="page-subtitle">批次ID: {{ batchInfo?.monthly_batch_id || batchId || '暂无数据' }}</p>
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
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="info-content">
              <div class="info-label">批次ID</div>
              <div class="info-value">{{ batchInfo?.monthly_batch_id || batchId || '暂无数据' }}</div>
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
            <el-icon><Operation /></el-icon>
            处理状态
          </h3>
          <div class="status-content">
            <el-tag 
              :type="getStatusType(batchInfo?.status)" 
              size="large" 
              class="status-tag"
            >
              {{ getStatusText(batchInfo?.status) }}
            </el-tag>
            <span class="status-time">
              最后更新: {{ formatDateTime(batchInfo?.updated_time) || '暂无数据' }}
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 计划数据表格 -->
    <div class="data-table-section">
      <el-card class="modern-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon">
              <el-icon><Grid /></el-icon>
            </div>
            <span class="header-title">月度计划记录</span>
            <div class="header-actions">
              <el-button 
                @click="refreshTableData" 
                :loading="tableLoading"
                size="small"
              >
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button 
                type="primary" 
                @click="exportTableData"
                size="small"
              >
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </div>
        </template>

        <div class="table-container">
          <el-table
            :data="tableData"
            :loading="tableLoading"
            stripe
            border
            height="500"
            class="modern-table"
          >
            <el-table-column type="index" label="序号" width="60" />
            <el-table-column prop="article_nr" label="品牌规格" min-width="180" show-overflow-tooltip />
            <el-table-column prop="article_name" label="规格名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="target_quantity_boxes" label="原计划(箱)" width="120" align="right">
              <template #default="{ row }">
                <span class="number-value">{{ formatNumber(row.target_quantity_boxes) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="hard_pack_boxes" label="硬包(箱)" width="100" align="right">
              <template #default="{ row }">
                <span class="number-value">{{ formatNumber(row.hard_pack_boxes) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="soft_pack_boxes" label="软包(箱)" width="100" align="right">
              <template #default="{ row }">
                <span class="number-value">{{ formatNumber(row.soft_pack_boxes) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="计划时间" width="120" align="center">
              <template #default="{ row }">
                <span>{{ row.plan_year }}-{{ String(row.plan_month).padStart(2, '0') }}</span>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="pagination.currentPage"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
              class="modern-pagination"
            />
          </div>
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
  Calendar,
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
  Operation,
  Grid
} from '@element-plus/icons-vue'
import api from '@/services/api'

// 路由和响应式数据
const route = useRoute()
const router = useRouter()
const batchId = ref<string>('')
const loading = ref(false)
const tableLoading = ref(false)

// 批次信息
const batchInfo = ref<any>(null)
const statisticsData = ref<any>(null)

// 表格数据
const tableData = ref<any[]>([])
const pagination = ref({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 获取批次ID
batchId.value = route.params.batchId as string

// 工具方法
const goBack = () => {
  router.push('/monthly-plan/entry')
}

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return '暂无数据'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatFileSize = (size: number | null | undefined) => {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let index = 0
  let fileSize = size
  while (fileSize >= 1024 && index < units.length - 1) {
    fileSize /= 1024
    index++
  }
  return `${fileSize.toFixed(2)} ${units[index]}`
}

const formatNumber = (num: number | null | undefined) => {
  if (num === null || num === undefined) return '0'
  return num.toLocaleString()
}

const getStatusType = (status: string | undefined) => {
  switch (status) {
    case 'COMPLETED': return 'success'
    case 'FAILED': return 'danger'
    case 'PARSING': return 'warning'
    default: return 'info'
  }
}

const getStatusText = (status: string | undefined) => {
  switch (status) {
    case 'COMPLETED': return '已完成'
    case 'FAILED': return '失败'
    case 'PARSING': return '解析中'
    case 'UPLOADING': return '上传中'
    default: return '未知'
  }
}

// 加载批次信息
const loadBatchInfo = async () => {
  try {
    loading.value = true
    const response = await api.get(`/api/v1/monthly-data/imports/${batchId.value}`)
    if (response.data.code === 200) {
      batchInfo.value = response.data.data
      statisticsData.value = {
        total_records: response.data.data.total_records,
        valid_records: response.data.data.valid_records,
        error_records: response.data.data.error_records,
        warning_records: response.data.data.warning_records
      }
    }
  } catch (error: any) {
    console.error('加载批次信息失败:', error)
    ElMessage.error('加载批次信息失败: ' + (error.message || '请检查网络连接'))
  } finally {
    loading.value = false
  }
}

// 加载表格数据
const loadTableData = async () => {
  try {
    tableLoading.value = true
    const response = await api.get('/api/v1/monthly-plans', {
      params: {
        batch_id: batchId.value,
        page: pagination.value.currentPage,
        page_size: pagination.value.pageSize
      }
    })
    if (response.data.code === 200) {
      tableData.value = response.data.data.plans || []
      pagination.value.total = response.data.data.pagination?.total || 0
    }
  } catch (error: any) {
    console.error('加载表格数据失败:', error)
    ElMessage.error('加载表格数据失败: ' + (error.message || '请检查网络连接'))
  } finally {
    tableLoading.value = false
  }
}

// 刷新数据
const refreshData = async () => {
  await Promise.all([loadBatchInfo(), loadTableData()])
  ElMessage.success('数据已刷新')
}

const refreshTableData = () => {
  loadTableData()
}

// 导出数据
const exportData = () => {
  ElMessage.info('导出功能正在开发中')
}

const exportTableData = () => {
  ElMessage.info('表格导出功能正在开发中')
}

// 分页处理
const handleSizeChange = (val: number) => {
  pagination.value.pageSize = val
  pagination.value.currentPage = 1
  loadTableData()
}

const handleCurrentChange = (val: number) => {
  pagination.value.currentPage = val
  loadTableData()
}

// 组件挂载
onMounted(() => {
  loadBatchInfo()
  loadTableData()
})
</script>

<style scoped>
.monthly-plan-detail {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
  background-color: #f5f7fa;
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
  font-weight: 600;
  color: #1f2937;
}

.header-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 6px;
  color: white;
}

.header-title {
  flex: 1;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.info-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  color: white;
  font-size: 18px;
}

.batch-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.file-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.time-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.size-icon {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

.info-content {
  flex: 1;
}

.info-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
  font-weight: 500;
}

.info-value {
  font-size: 16px;
  color: #1e293b;
  font-weight: 600;
  word-break: break-all;
}

.stats-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.total-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.success-card {
  background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
  color: white;
  border: none;
}

.warning-card {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  border: none;
}

.error-card {
  background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%);
  color: white;
  border: none;
}

.stat-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  font-size: 18px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
  font-weight: 500;
}

.status-section {
  margin-bottom: 24px;
}

.status-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.status-tag {
  font-weight: 600;
}

.status-time {
  color: #64748b;
  font-size: 14px;
}

.data-table-section {
  margin-bottom: 24px;
}

.table-container {
  padding: 0;
}

.modern-table {
  border-radius: 12px;
  overflow: hidden;
}

.number-value {
  font-weight: 600;
  color: #1f2937;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  border-top: 1px solid #e5e7eb;
  margin-top: 20px;
}

.modern-pagination {
  background: white;
}
</style>