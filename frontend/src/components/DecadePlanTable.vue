<template>
  <div class="decade-plan-table">
    <el-card>
      <template #header>
        <div class="table-header">
          <div class="header-left">
            <el-icon><Grid /></el-icon>
            <span>旬计划记录</span>
            <el-tag v-if="totalCount > 0" type="info" size="small">
              共 {{ totalCount }} 条记录
            </el-tag>
          </div>
          <div class="header-right">
            <el-button-group>
              <el-button 
                size="small" 
                @click="refreshData"
                :loading="loading"
              >
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button 
                size="small" 
                @click="exportData"
                :disabled="tableData.length === 0"
              >
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-input
              v-model="filterForm.articleNr"
              placeholder="成品烟牌号"
              clearable
              size="small"
              @input="handleFilter"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="6">
            <el-input
              v-model="filterForm.feederCode"
              placeholder="喂丝机代码"
              clearable
              size="small"
              @input="handleFilter"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="6">
            <el-input
              v-model="filterForm.makerCode"
              placeholder="卷包机代码"
              clearable
              size="small"
              @input="handleFilter"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="filterForm.validationStatus"
              placeholder="验证状态"
              clearable
              size="small"
              @change="handleFilter"
            >
              <el-option label="全部" value="" />
              <el-option label="有效" value="VALID" />
              <el-option label="警告" value="WARNING" />
              <el-option label="错误" value="ERROR" />
            </el-select>
          </el-col>
        </el-row>
        
        <!-- 快速筛选按钮 -->
        <div class="quick-filters">
          <el-button-group size="small">
            <el-button 
              :type="activeFilter === 'all' ? 'primary' : ''"
              @click="setQuickFilter('all')"
            >
              全部 ({{ totalCount }})
            </el-button>
            <el-button 
              :type="activeFilter === 'valid' ? 'success' : ''"
              @click="setQuickFilter('valid')"
            >
              有效 ({{ validCount }})
            </el-button>
            <el-button 
              :type="activeFilter === 'warning' ? 'warning' : ''"
              @click="setQuickFilter('warning')"
            >
              警告 ({{ warningCount }})
            </el-button>
            <el-button 
              :type="activeFilter === 'error' ? 'danger' : ''"
              @click="setQuickFilter('error')"
            >
              错误 ({{ errorCount }})
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table
        ref="tableRef"
        :data="paginatedData"
        style="width: 100%"
        stripe
        border
        size="small"
        :loading="loading"
        @sort-change="handleSortChange"
        row-key="work_order_nr"
      >
        <el-table-column 
          type="index" 
          label="序号" 
          width="60"
          align="center"
          :index="getRowIndex"
        />
        
        <el-table-column 
          prop="work_order_nr" 
          label="工单号" 
          width="140"
          show-overflow-tooltip
          sortable="custom"
        />
        
        <el-table-column 
          prop="article_nr" 
          label="成品烟牌号" 
          width="160"
          show-overflow-tooltip
          sortable="custom"
        />
        
        <el-table-column 
          prop="package_type" 
          label="包装类型" 
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <span>{{ row.package_type || '-' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="specification" 
          label="规格" 
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <span>{{ row.specification || '-' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="feeder_code" 
          label="喂丝机代码" 
          width="140"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <el-tag 
              v-for="code in formatMachineCodes(row.feeder_code)"
              :key="code"
              size="small"
              type="info"
              class="machine-tag"
            >
              {{ code }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="maker_code" 
          label="卷包机代码" 
          width="140"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <el-tag 
              v-for="code in formatMachineCodes(row.maker_code)"
              :key="code"
              size="small"
              type="success"
              class="machine-tag"
            >
              {{ code }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="quantity_total" 
          label="投料总量(箱)" 
          width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="number-cell">
              {{ formatNumber(row.quantity_total) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="final_quantity" 
          label="成品数量(箱)" 
          width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="number-cell">
              {{ formatNumber(row.final_quantity) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="planned_start" 
          label="计划开始时间" 
          width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ formatDateTime(row.planned_start) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="planned_end" 
          label="计划结束时间" 
          width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ formatDateTime(row.planned_end) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="validation_status" 
          label="验证状态" 
          width="100"
          align="center"
          sortable="custom"
        >
          <template #default="{ row }">
            <el-tag 
              :type="getStatusColor(row.validation_status)"
              size="small"
            >
              {{ getStatusText(row.validation_status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column 
          prop="validation_message" 
          label="验证消息" 
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span 
              v-if="row.validation_message"
              :class="getMessageClass(row.validation_status)"
            >
              {{ row.validation_message }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[20, 50, 100, 200]"
          :small="false"
          :disabled="loading"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredData.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Grid, 
  Refresh, 
  Download, 
  Search 
} from '@element-plus/icons-vue'
import { useDecadePlanStore } from '@/stores/decade-plan'
import DecadePlanAPI from '@/services/api'
import { 
  formatNumber, 
  formatDateTime, 
  getStatusColor, 
  getStatusText,
  debounce 
} from '@/utils'
import { handleError } from '@/utils/error-handler'
import type { DecadePlan } from '@/types/api'

// 定义组件属性
interface Props {
  importBatchId: string
}

const props = defineProps<Props>()

// 状态管理
const decadePlanStore = useDecadePlanStore()

// 响应式变量
const tableRef = ref()
const loading = ref(false)
const tableData = ref<DecadePlan[]>([])
const activeFilter = ref('all')

// 筛选表单
const filterForm = ref({
  articleNr: '',
  feederCode: '',
  makerCode: '',
  validationStatus: ''
})

// 分页配置
const pagination = ref({
  page: 1,
  size: 50
})

// 排序配置
const sortConfig = ref({
  prop: '',
  order: ''
})

// 计算属性
const totalCount = computed(() => tableData.value.length)

const validCount = computed(() => 
  tableData.value.filter(item => item.validation_status === 'VALID').length
)

const warningCount = computed(() => 
  tableData.value.filter(item => item.validation_status === 'WARNING').length
)

const errorCount = computed(() => 
  tableData.value.filter(item => item.validation_status === 'ERROR').length
)

const filteredData = computed(() => {
  let data = tableData.value

  // 文本筛选
  if (filterForm.value.articleNr) {
    data = data.filter(item => 
      item.article_nr?.toLowerCase().includes(filterForm.value.articleNr.toLowerCase())
    )
  }

  if (filterForm.value.feederCode) {
    data = data.filter(item => 
      item.feeder_code?.toLowerCase().includes(filterForm.value.feederCode.toLowerCase())
    )
  }

  if (filterForm.value.makerCode) {
    data = data.filter(item => 
      item.maker_code?.toLowerCase().includes(filterForm.value.makerCode.toLowerCase())
    )
  }

  if (filterForm.value.validationStatus) {
    data = data.filter(item => item.validation_status === filterForm.value.validationStatus)
  }

  // 快速筛选
  if (activeFilter.value !== 'all') {
    const statusMap = {
      'valid': 'VALID',
      'warning': 'WARNING',
      'error': 'ERROR'
    }
    const status = statusMap[activeFilter.value as keyof typeof statusMap]
    if (status) {
      data = data.filter(item => item.validation_status === status)
    }
  }

  // 排序
  if (sortConfig.value.prop && sortConfig.value.order) {
    data = [...data].sort((a, b) => {
      const prop = sortConfig.value.prop as keyof DecadePlan
      const aVal = a[prop]
      const bVal = b[prop]
      
      let result = 0
      if (aVal !== undefined && bVal !== undefined) {
        if (aVal < bVal) result = -1
        else if (aVal > bVal) result = 1
      } else if (aVal === undefined && bVal !== undefined) {
        result = 1
      } else if (aVal !== undefined && bVal === undefined) {
        result = -1
      }
      
      return sortConfig.value.order === 'ascending' ? result : -result
    })
  }

  return data
})

const paginatedData = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.size
  const end = start + pagination.value.size
  return filteredData.value.slice(start, end)
})

// 方法
const loadData = async () => {
  if (!props.importBatchId) return

  try {
    loading.value = true
    const response = await DecadePlanAPI.getDecadePlans(props.importBatchId)
    
    if (response.code === 200 && response.data.plans) {
      tableData.value = response.data.plans
      decadePlanStore.setDecadePlans(response.data.plans)
    } else {
      tableData.value = []
      ElMessage.warning('没有找到旬计划记录')
    }
  } catch (error) {
    handleError(error, '加载旬计划数据')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

const handleFilter = debounce(() => {
  pagination.value.page = 1
}, 300)

const setQuickFilter = (filter: string) => {
  activeFilter.value = filter
  
  // 清除状态筛选，因为快速筛选会覆盖它
  if (filter !== 'all') {
    filterForm.value.validationStatus = ''
  }
  
  pagination.value.page = 1
}

const handleSortChange = ({ prop, order }: { prop: string, order: string }) => {
  sortConfig.value.prop = prop
  sortConfig.value.order = order
  pagination.value.page = 1
}

const handleSizeChange = (size: number) => {
  pagination.value.size = size
  pagination.value.page = 1
}

const handleCurrentChange = (page: number) => {
  pagination.value.page = page
}

const getRowIndex = (index: number): number => {
  return (pagination.value.page - 1) * pagination.value.size + index + 1
}

const formatMachineCodes = (codes: string): string[] => {
  if (!codes) return []
  return codes.split(',').map(code => code.trim()).filter(code => code)
}

const getMessageClass = (status: string): string => {
  switch (status) {
    case 'WARNING':
      return 'text-warning'
    case 'ERROR':
      return 'text-danger'
    default:
      return 'text-muted'
  }
}

const exportData = () => {
  if (filteredData.value.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }

  try {
    // 构造CSV内容
    const headers = [
      '工单号', '成品烟牌号', '包装类型', '规格', '喂丝机代码', '卷包机代码',
      '投料总量', '成品数量', '计划开始时间', '计划结束时间', '验证状态', '验证消息'
    ]
    
    const csvContent = [
      headers.join(','),
      ...filteredData.value.map(row => [
        row.work_order_nr,
        row.article_nr,
        row.package_type || '',
        row.specification || '',
        row.feeder_code,
        row.maker_code,
        row.quantity_total,
        row.final_quantity,
        formatDateTime(row.planned_start || ''),
        formatDateTime(row.planned_end || ''),
        getStatusText(row.validation_status),
        `"${row.validation_message || ''}"`
      ].join(','))
    ].join('\n')

    // 创建Blob并下载
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `旬计划记录_${props.importBatchId}.csv`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('数据导出成功')
  } catch (error) {
    console.error('导出数据失败:', error)
    ElMessage.error('导出失败，请重试')
  }
}

// 生命周期
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.decade-plan-table {
  width: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.filter-section {
  margin-bottom: 16px;
}

.quick-filters {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

.machine-tag {
  margin-right: 4px;
  margin-bottom: 2px;
}

.number-cell {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-weight: 500;
}

.text-warning {
  color: #e6a23c;
}

.text-danger {
  color: #f56c6c;
}

.text-muted {
  color: #909399;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table .cell) {
  padding-left: 8px;
  padding-right: 8px;
}

:deep(.el-table__header-wrapper th) {
  background-color: #fafafa;
  color: #303133;
  font-weight: 600;
}

:deep(.el-table__row:hover > .el-table__cell) {
  background-color: #f5f7fa;
}
</style>