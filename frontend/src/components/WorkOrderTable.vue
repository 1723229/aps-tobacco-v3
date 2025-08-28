<template>
  <div class="work-order-table">
    <el-table
      :data="workOrders"
      :loading="loading"
      stripe
      style="width: 100%"
      max-height="600"
    >
      <el-table-column
        prop="work_order_nr"
        label="工单号"
        width="160"
        fixed="left"
      />
      <el-table-column
        prop="work_order_type"
        label="工单类型"
        width="100"
      >
        <template #default="scope">
          <el-tag 
            :type="scope.row.work_order_type === 'HJB' ? 'primary' : 'success'"
            size="small"
          >
            {{ getOrderTypeText(scope.row.work_order_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="machine_type"
        label="机台类型"
        width="100"
      />
      <el-table-column
        prop="machine_code"
        label="机台代码"
        width="100"
      />
      <el-table-column
        prop="product_code"
        label="产品代码"
        width="150"
        show-overflow-tooltip
      />
      <el-table-column
        prop="plan_quantity"
        label="计划数量"
        width="100"
        align="right"
      >
        <template #default="scope">
          {{ formatNumber(scope.row.plan_quantity) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="safety_stock"
        label="安全库存"
        width="100"
        align="right"
        v-if="hasFeederOrders"
      >
        <template #default="scope">
          {{ formatNumber(scope.row.safety_stock) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="work_order_status"
        label="工单状态"
        width="100"
      >
        <template #default="scope">
          <el-tag 
            :type="getStatusType(scope.row.work_order_status)"
            size="small"
          >
            {{ getStatusText(scope.row.work_order_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="planned_start_time"
        label="计划开始时间"
        width="160"
      >
        <template #default="scope">
          {{ formatDateTime(scope.row.planned_start_time) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="planned_end_time"
        label="计划结束时间"
        width="160"
      >
        <template #default="scope">
          {{ formatDateTime(scope.row.planned_end_time) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="created_time"
        label="创建时间"
        width="160"
      >
        <template #default="scope">
          {{ formatDateTime(scope.row.created_time) }}
        </template>
      </el-table-column>
      <el-table-column
        label="操作"
        width="120"
        fixed="right"
      >
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="viewDetails(scope.row)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="pagination.total > 0">
      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, prev, pager, next, jumper"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 工单详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="工单详情"
      width="60%"
      :before-close="handleCloseDetail"
    >
      <div v-if="selectedOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="工单号">
            {{ selectedOrder.work_order_nr }}
          </el-descriptions-item>
          <el-descriptions-item label="工单类型">
            <el-tag 
              :type="selectedOrder.work_order_type === 'HJB' ? 'primary' : 'success'"
            >
              {{ getOrderTypeText(selectedOrder.work_order_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="机台类型">
            {{ selectedOrder.machine_type }}
          </el-descriptions-item>
          <el-descriptions-item label="机台代码">
            {{ selectedOrder.machine_code }}
          </el-descriptions-item>
          <el-descriptions-item label="产品代码" :span="2">
            {{ selectedOrder.product_code }}
          </el-descriptions-item>
          <el-descriptions-item label="计划数量">
            {{ formatNumber(selectedOrder.plan_quantity) }}
          </el-descriptions-item>
          <el-descriptions-item label="安全库存" v-if="selectedOrder.safety_stock">
            {{ formatNumber(selectedOrder.safety_stock) }}
          </el-descriptions-item>
          <el-descriptions-item label="工单状态">
            <el-tag 
              :type="getStatusType(selectedOrder.work_order_status)"
            >
              {{ getStatusText(selectedOrder.work_order_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="计划开始时间">
            {{ formatDateTime(selectedOrder.planned_start_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="计划结束时间">
            {{ formatDateTime(selectedOrder.planned_end_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(selectedOrder.created_time) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits } from 'vue'
import type { WorkOrder } from '@/services/api'

// 组件属性
interface Props {
  workOrders: WorkOrder[]
  loading?: boolean
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// 组件事件
const emit = defineEmits<{
  'page-change': [page: number]
}>()

// 响应式数据
const detailDialogVisible = ref(false)
const selectedOrder = ref<WorkOrder | null>(null)

// 计算属性
const hasFeederOrders = computed(() => {
  return props.workOrders.some(order => order.work_order_type === 'HWS')
})

// 方法定义
const getOrderTypeText = (type: string) => {
  const typeMap: Record<string, string> = {
    'HJB': '卷包机',
    'HWS': '喂丝机'
  }
  return typeMap[type] || type
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, any> = {
    'PENDING': 'warning',
    'IN_PROGRESS': 'primary',
    'COMPLETED': 'success',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'PENDING': '待执行',
    'IN_PROGRESS': '执行中',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const formatNumber = (value?: number) => {
  if (value === undefined || value === null) return '--'
  return value.toLocaleString()
}

const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return '--'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const handlePageChange = (page: number) => {
  emit('page-change', page)
}

const viewDetails = (order: WorkOrder) => {
  selectedOrder.value = order
  detailDialogVisible.value = true
}

const handleCloseDetail = (done: Function) => {
  selectedOrder.value = null
  done()
}
</script>

<style scoped>
.work-order-table {
  width: 100%;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.el-descriptions {
  margin-top: 20px;
}

.el-tag {
  margin-right: 8px;
}
</style>