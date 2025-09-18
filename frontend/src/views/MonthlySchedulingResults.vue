<template>
  <div class="monthly-scheduling-results">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">月度排产结果</h1>
      <div class="header-actions">
        <el-button @click="goBack" icon="ArrowLeft">返回</el-button>
        <el-button @click="refreshData" icon="Refresh">刷新</el-button>
        <el-button @click="exportResults" type="primary" icon="Download">导出结果</el-button>
      </div>
    </div>

    <!-- 任务信息摘要 -->
    <el-card v-if="taskDetail" class="task-summary" style="margin-bottom: 20px;">
      <template #header>
        <div class="card-header">
          <span>任务信息</span>
          <el-tag :type="getStatusType(taskDetail.status)">
            {{ getStatusText(taskDetail.status) }}
          </el-tag>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">任务ID</div>
            <div class="value">{{ taskDetail.task_id }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">批次ID</div>
            <div class="value">{{ taskDetail.batch_id }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">排产计划数</div>
            <div class="value">{{ taskDetail.scheduled_plans || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">进度</div>
            <div class="value">{{ taskDetail.progress || 0 }}%</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card" style="margin-bottom: 20px;">
      <el-form :model="filters" inline>
        <el-form-item label="工单号">
          <el-input
            v-model="filters.work_order_nr"
            placeholder="请输入工单号"
            clearable
            style="width: 200px;"
          />
        </el-form-item>
        <el-form-item label="机台代码">
          <el-input
            v-model="filters.machine_code"
            placeholder="请输入机台代码"
            clearable
            style="width: 200px;"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="请选择状态"
            clearable
            style="width: 150px;"
          >
            <el-option label="已排产" value="SCHEDULED" />
            <el-option label="已优化" value="OPTIMIZED" />
            <el-option label="已确认" value="CONFIRMED" />
            <el-option label="执行中" value="EXECUTED" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="searchResults" type="primary" icon="Search">
            查询
          </el-button>
          <el-button @click="resetFilters" icon="Refresh">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 排产结果表格 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>排产结果列表</span>
          <span v-if="pagination.total" class="count-info">
            共 {{ pagination.total }} 条记录
          </span>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="scheduleResults"
        stripe
        border
        style="width: 100%"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="work_order_nr" label="工单号" width="150" sortable />
        <el-table-column prop="article_nr" label="品牌规格" width="180" />
        <el-table-column label="机台组合" width="200">
          <template #default="scope">
            <div>
              <div v-if="scope.row.assigned_feeder_code">
                <el-tag size="small" type="success">
                  喂丝机: {{ scope.row.assigned_feeder_code }}
                </el-tag>
              </div>
              <div v-if="scope.row.assigned_maker_code" style="margin-top: 4px;">
                <el-tag size="small" type="primary">
                  卷包机: {{ scope.row.assigned_maker_code }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="排产时间" width="300">
          <template #default="scope">
            <div>
              <div>开始: {{ formatDateTime(scope.row.scheduled_start_time) }}</div>
              <div>结束: {{ formatDateTime(scope.row.scheduled_end_time) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_duration_hours" label="时长(小时)" width="100" />
        <el-table-column prop="allocated_boxes" label="产量(箱)" width="120" />
        <el-table-column prop="estimated_speed" label="速度(箱/时)" width="120" />
        <el-table-column prop="schedule_status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.schedule_status)">
              {{ getStatusText(scope.row.schedule_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button @click="viewDetail(scope.row)" type="primary" size="small">
              详情
            </el-button>
            <el-button @click="editSchedule(scope.row)" size="small">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

// 路由相关
const route = useRoute()
const router = useRouter()
const taskId = computed(() => route.params.taskId as string)

// 响应式数据
const loading = ref(false)
const taskDetail = ref<any>(null)
const scheduleResults = ref<any[]>([])

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 筛选条件
const filters = ref({
  work_order_nr: '',
  machine_code: '',
  status: ''
})

// 生命周期
onMounted(() => {
  loadTaskDetail()
  loadScheduleResults()
})

// 方法
const loadTaskDetail = async () => {
  try {
    const response = await api.get(`/api/v1/monthly-scheduling/tasks/${taskId.value}`)
    if (response.data.code === 200) {
      taskDetail.value = response.data.data
    }
  } catch (error) {
    console.error('加载任务详情失败:', error)
    ElMessage.error('加载任务详情失败')
  }
}

const loadScheduleResults = async () => {
  loading.value = true
  try {
    const params: any = {
      task_id: taskId.value,
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }

    // 添加筛选条件
    if (filters.value.work_order_nr) {
      params.work_order_nr = filters.value.work_order_nr
    }
    if (filters.value.machine_code) {
      params.machine_code = filters.value.machine_code
    }
    if (filters.value.status) {
      params.status = filters.value.status
    }

    const response = await api.get('/api/v1/monthly-work-orders/schedule', { params })
    
    if (response.data.code === 200) {
      scheduleResults.value = response.data.data.work_orders || []
      pagination.value.total = response.data.data.pagination?.total_count || 0
    }
  } catch (error) {
    console.error('加载排产结果失败:', error)
    ElMessage.error('加载排产结果失败')
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadTaskDetail()
  loadScheduleResults()
}

const searchResults = () => {
  pagination.value.page = 1
  loadScheduleResults()
}

const resetFilters = () => {
  filters.value = {
    work_order_nr: '',
    machine_code: '',
    status: ''
  }
  searchResults()
}

const handleSizeChange = (val: number) => {
  pagination.value.pageSize = val
  loadScheduleResults()
}

const handleCurrentChange = (val: number) => {
  pagination.value.page = val
  loadScheduleResults()
}

const handleSortChange = (sortInfo: any) => {
  // 处理排序逻辑
  console.log('排序变化:', sortInfo)
  // 可以在这里添加排序的API调用
}

const viewDetail = (row: any) => {
  ElMessage.info('查看详情功能开发中...')
}

const editSchedule = (row: any) => {
  ElMessage.info('编辑排产功能开发中...')
}

const exportResults = () => {
  ElMessage.info('导出结果功能开发中...')
}

const goBack = () => {
  router.back()
}

// 辅助方法
const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'SCHEDULED': 'info',
    'OPTIMIZED': 'warning',
    'CONFIRMED': 'success',
    'EXECUTED': 'primary',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'SCHEDULED': '已排产',
    'OPTIMIZED': '已优化',
    'CONFIRMED': '已确认',
    'EXECUTED': '执行中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}
</script>

<style scoped>
.monthly-scheduling-results {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.count-info {
  color: #909399;
  font-size: 14px;
}

.task-summary .summary-item {
  text-align: center;
}

.task-summary .summary-item .label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.task-summary .summary-item .value {
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.filter-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  margin-top: 20px;
  text-align: right;
}
</style>
