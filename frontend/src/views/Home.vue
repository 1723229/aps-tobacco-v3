<template>
  <div class="home-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><DataAnalysis /></el-icon>
            APS 烟草生产计划系统
          </h1>
          <p class="page-subtitle">Advanced Planning and Scheduling System</p>
        </div>

      </div>
    </div>

    <!-- 系统概览统计 -->
    <div class="overview-section">
      <el-row :gutter="24" justify="center">
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-header">
              <el-icon class="stat-icon upload-icon"><Upload /></el-icon>
              <span class="stat-title">今日上传</span>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ monthlyStatistics.today_uploads || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-header">
              <el-icon class="stat-icon process-icon"><DataLine /></el-icon>
              <span class="stat-title">本月处理</span>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ monthlyStatistics.monthly_processed || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-header">
              <el-icon class="stat-icon task-icon"><TrendCharts /></el-icon>
              <span class="stat-title">排产任务</span>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ monthlyStatistics.scheduling_tasks || 0 }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <el-row :gutter="24" justify="center">
        <el-col :span="12">
           <el-card class="action-card scheduling-card" @click="goToMonthlyPlan">
            <div class="card-header">
              <div class="header-logo">
                <el-icon><Lightning /></el-icon>
              </div>
              <div class="header-menu">
                <el-icon><DataAnalysis /></el-icon>
                <span>月度计划数据录入</span>
              </div>
            </div>
            <div class="action-content">
              <div class="action-icon scheduling-action">
                <el-icon><Lightning /></el-icon>
              </div>
              <div class="action-text">
                <h3>月度计划排产</h3>
                <p>上传Excel文件进行月度计划数据录入，执行排产管理</p>
              </div>
              <div class="action-arrow">
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="action-card machine-config-card" @click="goToMachineConfig">
            <div class="card-header">
              <div class="header-logo">
                <el-icon><Grid /></el-icon>
              </div>
              <div class="header-menu">
                <el-icon><Setting /></el-icon>
                <span>配置管理</span>
              </div>
            </div>
            <div class="action-content">
              <div class="action-icon config-action">
                <el-icon><Grid /></el-icon>
              </div>
              <div class="action-text">
                <h3>机台配置管理</h3>
                <p>管理机台信息、关系配置、速度设置、维护计划和班次</p>
              </div>
              <div class="action-arrow">
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 最近活动 -->
    <div class="recent-activity">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span>最近活动</span>
            <div class="header-actions">
              <el-button size="small" text @click="refreshActivity">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="recentActivity"
          style="width: 100%"
          size="small"
          :loading="activityLoading"
        >
          <el-table-column prop="batch_id" label="批次ID" width="150" />
          <el-table-column prop="file_name" label="文件名" min-width="200">
            <template #default="{ row }">
              <span>{{ row.file_name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="upload_time" label="上传时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.upload_time || row.import_end_time) }}
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
              <el-button
                size="small"
                text
                @click="viewDetails(row.batch_id, row.plan_type)"
              >
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="recentActivity.length === 0 && !activityLoading" class="empty-state">
          <el-empty description="暂无最近活动记录" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Plus,
  Upload,
  DataLine,
  CircleCheck,
  Grid,
  Lightning,
  UploadFilled,
  Clock,
  Download,
  ArrowRight,
  List,
  Refresh,
  Setting,
  Document,
  Box,
  Operation,
  TrendCharts,
  Calendar
} from '@element-plus/icons-vue'
import { formatDateTime, getStatusColor, getStatusText } from '@/utils'
import type { HistoryRecord } from '@/types/api'

const router = useRouter()

// 响应式数据
const monthlyStatistics = ref({
  today_uploads: 0,
  monthly_processed: 0,
  total_work_orders: 0,
  scheduling_tasks: 0
})

const recentActivity = ref<HistoryRecord[]>([])

const activityLoading = ref(false)

// 方法
const goToMachineConfig = () => {
  router.push('/machine-config')
}

const goToMonthlyPlan = () => {
  router.push('/monthly-scheduling')
}

const viewDetails = (batchId: string, planType?: string) => {
  if (planType === 'monthly') {
    // 跳转到月度计划详情页
    router.push(`/monthly-plan/detail/${batchId}`)
  }
}

const refreshActivity = async () => {
  activityLoading.value = true
  try {
    const monthlyResponse = await fetch('/api/v1/monthly-data/imports?page=1&page_size=10').then(res => res.json())
    
    const activities: any[] = []
    // 添加月度计划记录
    if (monthlyResponse.code === 200 && monthlyResponse.data?.imports) {
      monthlyResponse.data.imports.forEach((record: any) => {
        activities.push({
          batch_id: record.monthly_batch_id,
          file_name: record.file_name || '月度计划文件',
          total_records: record.total_records,
          valid_records: record.valid_records,
          import_end_time: record.updated_time || record.created_time,
          status: record.status,
          plan_type: 'monthly',
          display_name: record.file_name || '月度计划文件',
          upload_time: record.upload_time || record.created_time
        })
      })
    }

    recentActivity.value = activities.slice(0, 5)
    ElMessage.success('数据已刷新')
  } catch (error) {
    console.error('刷新数据失败:', error)
    ElMessage.error('刷新数据失败')
  } finally {
    activityLoading.value = false
  }
}

// 加载统计数据
const loadStatistics = async () => {
  try {
    console.log('📊 开始加载统计数据...')

    // 加载月度计划的统计数据
    await loadMonthlyStatistics()

    console.log('✅ 统计数据加载完成')
  } catch (error) {
    console.error('❌ 加载统计数据失败:', error)
    ElMessage.error('统计数据加载失败')
  }
}


// 加载月度计划统计数据
const loadMonthlyStatistics = async () => {
  try {
    const [monthlyDataResponse, monthlyTasksResponse] = await Promise.all([
      fetch('/api/v1/monthly-data/imports?page=1&page_size=1000').then(res => res.json()),
      fetch('/api/v1/monthly-scheduling/tasks?page=1&page_size=100').then(res => res.json())
    ])

    const today = new Date().toISOString().split('T')[0]
    const currentMonth = new Date().toISOString().substring(0, 7)

    let todayUploads = 0
    let monthlyProcessed = 0

    if (monthlyDataResponse.code === 200 && monthlyDataResponse.data?.imports) {
      const imports = monthlyDataResponse.data.imports
      todayUploads = imports.filter((item: any) =>
        item.upload_time?.startsWith(today)
      ).length

      monthlyProcessed = imports.filter((item: any) =>
        item.created_time?.startsWith(currentMonth)
      ).length
    }

    monthlyStatistics.value = {
      today_uploads: todayUploads,
      monthly_processed: monthlyProcessed,
      total_work_orders: 0, // 月度工单数暂时设为0，后续可以从排产结果计算
      scheduling_tasks: monthlyTasksResponse.code === 200 ? (monthlyTasksResponse.data?.pagination?.total_count || 0) : 0
    }

    console.log('✅ 月度计划统计:', monthlyStatistics.value)
  } catch (error) {
    console.error('❌ 月度计划统计加载失败:', error)
    monthlyStatistics.value = { today_uploads: 0, monthly_processed: 0, total_work_orders: 0, scheduling_tasks: 0 }
  }
}

// 加载最近活动
const loadRecentActivity = async () => {
  try {
    activityLoading.value = true

    // 加载月度计划的活动记录
    const monthlyResponse = await fetch('/api/v1/monthly-data/imports?page=1&page_size=10').then(res => res.json())

    const activities: any[] = []

    // 添加月度计划记录
    if (monthlyResponse.code === 200 && monthlyResponse.data?.imports) {
      monthlyResponse.data.imports.forEach((record: any) => {
        activities.push({
          batch_id: record.monthly_batch_id,
          file_name: record.file_name || '月度计划文件',
          total_records: record.total_records,
          valid_records: record.valid_records,
          import_end_time: record.updated_time || record.created_time,
          status: record.status,
          plan_type: 'monthly', // 标记为月度计划
          display_name: record.file_name || '月度计划文件',
          upload_time: record.upload_time || record.created_time
        })
      })
    }

    // 按上传时间排序，最新的在前面
    activities.sort((a, b) => {
      const timeA = new Date(a.upload_time || a.import_end_time || 0).getTime()
      const timeB = new Date(b.upload_time || b.import_end_time || 0).getTime()
      return timeB - timeA
    })

    // 只保留最近5条记录
    recentActivity.value = activities.slice(0, 5)

    console.log('✅ 最近活动记录加载完成:', recentActivity.value.length, '条')

  } catch (error) {
    console.error('加载最近活动失败:', error)
    recentActivity.value = []
  } finally {
    activityLoading.value = false
  }
}

// 生命周期
onMounted(async () => {
  console.log('Home page mounted')

  // 并行加载数据
  await Promise.all([
    loadStatistics(),
    loadRecentActivity()
  ])
})
</script>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
}

.header-left .page-title {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 0 0 12px 0;
  font-size: 32px;
  font-weight: 700;
}

.header-left .page-subtitle {
  margin: 0;
  opacity: 0.9;
  font-size: 16px;
  font-weight: 300;
}

.overview-section {
  margin-bottom: 32px;
}

.stat-card {
  transition: all 0.3s ease;
  border-radius: 16px;
  border: 1px solid #e8eaed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  height: 140px;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: rgba(64, 158, 255, 0.3);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.stat-title {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  letter-spacing: 0.5px;
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-icon {
  font-size: 20px;
}

.upload-icon {
  color: #409eff;
}

.process-icon {
  color: #67c23a;
}

.task-icon {
  color: #e6a23c;
}

.quick-actions {
  margin-bottom: 32px;
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

.action-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
  height: 180px; /* 增加高度以适应header */
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: #409eff;
}

.action-content {
  display: flex;
  align-items: center;
  padding: 24px;
  min-height: 100px;
}

.action-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  font-size: 24px;
  color: white;
  flex-shrink: 0;
}

.upload-action {
  background: linear-gradient(135deg, #409eff, #67c23a);
}

.history-action {
  background: linear-gradient(135deg, #e6a23c, #f56c6c);
}

.action-text {
  flex: 1;
}

.action-text h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #303133;
  font-weight: 600;
}

.action-text p {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.action-arrow {
  font-size: 20px;
  color: #c0c4cc;
  transition: color 0.3s ease;
}

.action-card:hover .action-arrow {
  color: #409eff;
}

.recent-activity {
  margin-bottom: 32px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

:deep(.el-statistic__number) {
  font-size: 24px;
  font-weight: 600;
}

:deep(.el-statistic__title) {
  margin-bottom: 8px;
  font-size: 14px;
}

:deep(.el-card) {
  border-radius: 8px;
}

:deep(.el-card__body) {
  padding: 20px;
}

/* 快速操作卡片图标样式 */
.upload-action {
  background: linear-gradient(135deg, #e6f0ff 0%, #d9e8ff 100%);
  color: #606266;
}

.config-action {
  background: linear-gradient(135deg, #fad4d1 0%, #f8c8c8 100%);
  color: #606266;
}

.scheduling-action {
  background: linear-gradient(135deg, #e8f5e8 0%, #d4f1d4 100%);
  color: #606266;
}

/* 机台配置卡片特殊样式 */
.machine-config-card {
  position: relative;
  overflow: hidden;
}

.machine-config-card .card-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(135deg, #fad4d1 0%, #f8c8c8 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  color: #606266;
  font-size: 12px;
  z-index: 1;
  border-radius: 8px 8px 0 0;
}

.machine-config-card .header-logo {
  display: flex;
  align-items: center;
  font-weight: 600;
}

.machine-config-card .header-menu {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.machine-config-card .action-content {
  margin-top: 40px;
  padding: 16px 24px 24px 24px; /* 减少上方padding来补偿header高度 */
  min-height: 100px; /* 调整最小高度 */
}


/* 智能排产管理卡片特殊样式 */
.scheduling-card {
  position: relative;
  overflow: hidden;
}

.scheduling-card .card-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(135deg, #e8f5e8 0%, #d4f1d4 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  color: #606266;
  font-size: 12px;
  z-index: 1;
  border-radius: 8px 8px 0 0;
}

.scheduling-card .header-logo {
  display: flex;
  align-items: center;
  font-weight: 600;
}

.scheduling-card .header-menu {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.scheduling-card .action-content {
  margin-top: 40px;
  padding: 16px 24px 24px 24px;
  min-height: 100px;
}
</style>
