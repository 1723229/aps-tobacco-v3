<template>
  <div class="parse-result">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><Document /></el-icon>
          <span>解析结果</span>
        </div>
      </template>

      <!-- 统计信息 -->
      <div class="result-summary">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-statistic 
              title="总记录数" 
              :value="result.total_records"
              class="stat-item"
            >
              <template #suffix>
                <span class="stat-suffix">条</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic 
              title="有效记录" 
              :value="result.valid_records"
              class="stat-item stat-success"
            >
              <template #suffix>
                <span class="stat-suffix">条</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic 
              title="警告记录" 
              :value="result.warning_records"
              class="stat-item stat-warning"
            >
              <template #suffix>
                <span class="stat-suffix">条</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic 
              title="错误记录" 
              :value="result.error_records"
              class="stat-item stat-danger"
            >
              <template #suffix>
                <span class="stat-suffix">条</span>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 操作按钮 -->
      <div class="result-actions">
        <el-button 
          type="primary" 
          size="default"
          @click="handleViewDetails"
          :disabled="result.total_records === 0"
        >
          <el-icon><View /></el-icon>
          查看旬计划详情
        </el-button>
        
        <el-button 
          v-if="result.error_records > 0"
          type="warning" 
          size="default"
          @click="showErrorDetails = true"
        >
          <el-icon><Warning /></el-icon>
          查看错误详情 ({{ result.error_records }})
        </el-button>

        <el-button 
          type="success" 
          size="default"
          @click="downloadTemplate"
          plain
        >
          <el-icon><Download /></el-icon>
          下载模板
        </el-button>
      </div>

      <!-- 数据预览表格 -->
      <div v-if="result.records && result.records.length > 0" class="data-preview">
        <el-divider>
          <span class="divider-text">数据预览（前10条记录）</span>
        </el-divider>
        
        <el-table 
          :data="previewData" 
          style="width: 100%"
          stripe
          size="small"
          max-height="400"
        >
          <el-table-column 
            prop="row_number" 
            label="行号" 
            width="60"
            align="center"
          />
          <el-table-column 
            prop="work_order_nr" 
            label="工单号" 
            width="120"
            show-overflow-tooltip
          />
          <el-table-column 
            prop="article_nr" 
            label="成品烟牌号" 
            width="150"
            show-overflow-tooltip
          />
          <el-table-column 
            prop="package_type" 
            label="包装类型" 
            width="80"
            align="center"
          />
          <el-table-column 
            prop="specification" 
            label="规格" 
            width="80"
            align="center"
          />
          <el-table-column 
            prop="feeder_codes" 
            label="喂丝机代码" 
            width="120"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span v-if="Array.isArray(row.feeder_codes)">
                {{ row.feeder_codes.join(', ') }}
              </span>
              <span v-else>{{ row.feeder_codes || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column 
            prop="maker_codes" 
            label="卷包机代码" 
            width="120"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span v-if="Array.isArray(row.maker_codes)">
                {{ row.maker_codes.join(', ') }}
              </span>
              <span v-else>{{ row.maker_codes || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column 
            prop="quantity_total" 
            label="投料总量" 
            width="100"
            align="right"
          >
            <template #default="{ row }">
              <span>{{ formatNumber(row.quantity_total) }}</span>
            </template>
          </el-table-column>
          <el-table-column 
            prop="final_quantity" 
            label="成品数量" 
            width="100"
            align="right"
          >
            <template #default="{ row }">
              <span>{{ formatNumber(row.final_quantity) }}</span>
            </template>
          </el-table-column>
          <el-table-column 
            prop="validation_status" 
            label="状态" 
            width="80"
            align="center"
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
        </el-table>
      </div>

      <!-- 错误详情对话框 -->
      <el-dialog
        v-model="showErrorDetails"
        title="错误详情"
        width="80%"
        destroy-on-close
      >
        <el-table 
          :data="result.errors" 
          style="width: 100%"
          stripe
          size="small"
          max-height="500"
        >
          <el-table-column 
            prop="row_number" 
            label="行号" 
            width="60"
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
          />
          <el-table-column 
            prop="error_message" 
            label="错误描述" 
            show-overflow-tooltip
          />
          <el-table-column 
            prop="original_value" 
            label="原始值" 
            width="120"
            show-overflow-tooltip
          />
        </el-table>
        
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showErrorDetails = false">关闭</el-button>
            <el-button type="primary" @click="exportErrors">导出错误报告</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Document, 
  View, 
  Warning, 
  Download 
} from '@element-plus/icons-vue'
import { getStatusColor, getStatusText } from '@/utils'
import type { ParseResult } from '@/types/api'

// 定义组件属性
interface Props {
  result: ParseResult
  importBatchId: string
}

const props = defineProps<Props>()

// 定义组件事件
const emit = defineEmits<{
  'view-details': [batchId: string]
}>()

// 响应式变量
const showErrorDetails = ref(false)

// 计算属性
const previewData = computed(() => {
  return props.result.records?.slice(0, 10) || []
})

// 方法
const handleViewDetails = () => {
  emit('view-details', props.importBatchId)
}

const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString()
}

const downloadTemplate = () => {
  // TODO: 实现模板下载功能
  ElMessage.info('模板下载功能开发中...')
}

const exportErrors = () => {
  if (!props.result.errors || props.result.errors.length === 0) {
    ElMessage.warning('没有错误记录可导出')
    return
  }

  try {
    // 构造CSV内容
    const headers = ['行号', '列名', '错误类型', '错误描述', '原始值']
    const csvContent = [
      headers.join(','),
      ...props.result.errors.map(error => [
        error.row_number,
        error.column_name,
        error.error_type,
        `"${error.error_message}"`,
        `"${error.original_value || ''}"`
      ].join(','))
    ].join('\n')

    // 创建Blob并下载
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `错误报告_${props.importBatchId}.csv`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('错误报告导出成功')
  } catch (error) {
    console.error('导出错误报告失败:', error)
    ElMessage.error('导出失败，请重试')
  }
}
</script>

<style scoped>
.parse-result {
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.result-summary {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  border-radius: 8px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-success {
  background-color: #f0f9ff;
  border-color: #67c23a;
}

.stat-success :deep(.el-statistic__number) {
  color: #67c23a;
}

.stat-warning {
  background-color: #fdf6ec;
  border-color: #e6a23c;
}

.stat-warning :deep(.el-statistic__number) {
  color: #e6a23c;
}

.stat-danger {
  background-color: #fef0f0;
  border-color: #f56c6c;
}

.stat-danger :deep(.el-statistic__number) {
  color: #f56c6c;
}

.stat-suffix {
  font-size: 14px;
  color: #909399;
  margin-left: 4px;
}

.result-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 20px;
}

.data-preview {
  margin-top: 20px;
}

.divider-text {
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table .cell) {
  padding-left: 8px;
  padding-right: 8px;
}

:deep(.el-statistic__head) {
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

:deep(.el-statistic__number) {
  font-size: 24px;
  font-weight: 600;
}
</style>