<template>
  <div class="decade-plan-upload">
    <!-- 操作说明 -->
    <el-alert
      title="卷包旬计划录入说明"
      type="info"
      :closable="false"
      class="mb-4"
    >
      <template #default>
        <div class="instruction-content">
          <p>请上传标准的卷包旬计划Excel文件（.xlsx格式），文件大小不超过50MB。</p>
          <p>系统将自动解析文件内容并生成旬计划记录，包括机台组合、生产数量等信息。</p>
        </div>
      </template>
    </el-alert>

    <!-- 上传区域 -->
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <el-icon><UploadFilled /></el-icon>
          <span>文件上传</span>
        </div>
      </template>

      <el-upload
        ref="uploadRef"
        class="upload-dragger"
        drag
        :auto-upload="false"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :on-change="handleFileChange"
        accept=".xlsx,.xls"
      >
        <div class="upload-content">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            <p class="primary-text">将文件拖到此处，或<em>点击上传</em></p>
            <p class="secondary-text">支持 .xlsx、.xls 格式，文件大小不超过 50MB</p>
          </div>
        </div>
      </el-upload>

      <!-- 当前文件信息 -->
      <div v-if="currentFile" class="current-file-info">
        <el-divider />
        
        <div class="file-info">
          <div class="file-basic">
            <el-icon class="file-icon"><Document /></el-icon>
            <div class="file-details">
              <div class="file-name">{{ currentFile.name }}</div>
              <div class="file-size">{{ formatFileSize(currentFile.size) }}</div>
            </div>
            <div class="file-actions">
              <el-button 
                v-if="!isUploading" 
                type="danger" 
                size="small" 
                text
                @click="clearFile"
              >
                <el-icon><Delete /></el-icon>
                移除
              </el-button>
            </div>
          </div>

          <!-- 上传进度 -->
          <div v-if="isUploading || uploadProgress > 0" class="upload-progress">
            <el-progress 
              :percentage="uploadProgress" 
              :status="uploadStatus"
              :stroke-width="8"
            />
            <div class="progress-text">
              {{ getProgressText() }}
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="upload-actions">
            <el-button 
              v-if="!isUploading && uploadProgress === 0"
              type="primary" 
              size="default"
              @click="startUpload"
              :loading="isUploading"
            >
              <el-icon><Upload /></el-icon>
              开始上传
            </el-button>
            
            <el-button 
              v-if="uploadProgress === 100 && uploadResult"
              type="success" 
              size="default"
              @click="startParsing"
              :loading="isParsing"
            >
              <el-icon><Reading /></el-icon>
              {{ isParsing ? '解析中...' : '开始解析' }}
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 解析结果 -->
    <ParseResult 
      v-if="parseResult" 
      :result="parseResult.data" 
      :import-batch-id="uploadResult?.data.import_batch_id || ''"
      @view-details="handleViewDetails"
      class="mt-4"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  UploadFilled, 
  Document, 
  Delete, 
  Upload, 
  Reading 
} from '@element-plus/icons-vue'
import { useDecadePlanStore } from '@/stores/decade-plan'
import DecadePlanAPI from '@/services/api'
import ParseResult from './ParseResult.vue'
import { 
  formatFileSize, 
  validateFileType, 
  validateFileSize, 
  generateId 
} from '@/utils'
import { handleError } from '@/utils/error-handler'
import type { UploadFile } from 'element-plus'
import type { UploadResponse, ParseResponse } from '@/types/api'

// 定义组件事件
const emit = defineEmits<{
  'upload-success': [result: UploadResponse]
  'parse-success': [result: ParseResponse]
  'view-details': [batchId: string]
}>()

// 状态管理
const decadePlanStore = useDecadePlanStore()

// 响应式变量
const uploadRef = ref()
const currentFile = ref<File | null>(null)
const isUploading = ref(false)
const isParsing = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref<UploadResponse | null>(null)
const parseResult = ref<ParseResponse | null>(null)

// 配置常量
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const ALLOWED_TYPES = ['.xlsx', '.xls']

// 计算属性
const uploadStatus = computed(() => {
  if (uploadProgress.value === 100) return 'success'
  if (isUploading.value) return undefined
  return undefined
})

// 方法
const beforeUpload = (file: File): boolean => {
  // 验证文件类型
  if (!validateFileType(file, ALLOWED_TYPES)) {
    ElMessage.error('文件格式不正确！请上传 .xlsx 或 .xls 格式的文件')
    return false
  }

  // 验证文件大小
  if (!validateFileSize(file, MAX_FILE_SIZE)) {
    ElMessage.error(`文件大小不能超过 ${formatFileSize(MAX_FILE_SIZE)}`)
    return false
  }

  return true
}

const handleFileChange = (file: UploadFile) => {
  if (file.raw) {
    // 重置状态
    resetUploadState()
    currentFile.value = file.raw
  }
}

const clearFile = async () => {
  if (isUploading.value) {
    const confirmed = await ElMessageBox.confirm(
      '文件正在上传中，确定要取消吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).catch(() => false)
    
    if (!confirmed) return
  }

  resetUploadState()
  uploadRef.value?.clearFiles()
}

const resetUploadState = () => {
  currentFile.value = null
  isUploading.value = false
  isParsing.value = false
  uploadProgress.value = 0
  uploadResult.value = null
  parseResult.value = null
  decadePlanStore.clearCurrentData()
}

const startUpload = async () => {
  if (!currentFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  try {
    isUploading.value = true
    uploadProgress.value = 0

    // 创建上传记录
    const uploadItem = {
      id: generateId(),
      file: currentFile.value,
      fileName: currentFile.value.name,
      fileSize: currentFile.value.size,
      status: 'uploading' as const,
      progress: 0
    }

    decadePlanStore.addUploadItem(uploadItem)
    decadePlanStore.setCurrentUpload(uploadItem)
    decadePlanStore.setIsUploading(true)

    // 上传文件
    const result = await DecadePlanAPI.uploadFile(
      currentFile.value,
      (progress) => {
        uploadProgress.value = progress
        decadePlanStore.updateUploadItem(uploadItem.id, { progress })
      }
    )

    uploadResult.value = result
    uploadProgress.value = 100

    // 更新状态
    decadePlanStore.updateUploadItem(uploadItem.id, {
      status: 'success',
      progress: 100,
      importBatchId: result.data.import_batch_id,
      uploadTime: result.data.upload_time
    })

    decadePlanStore.setCurrentBatchId(result.data.import_batch_id)

    // Remove duplicate message - let parent component handle it
    emit('upload-success', result)

    // 自动开始解析
    setTimeout(() => {
      startParsing()
    }, 1000)

  } catch (error) {
    handleError(error, '文件上传')
    uploadProgress.value = 0
    
    // 更新状态为失败
    const currentUpload = decadePlanStore.currentUpload
    if (currentUpload) {
      decadePlanStore.updateUploadItem(currentUpload.id, {
        status: 'error',
        progress: 0,
        errorMessage: error instanceof Error ? error.message : '上传失败'
      })
    }
  } finally {
    isUploading.value = false
    decadePlanStore.setIsUploading(false)
  }
}

const startParsing = async () => {
  if (!uploadResult.value) {
    ElMessage.warning('请先上传文件')
    return
  }

  const batchId = uploadResult.value.data.import_batch_id

  try {
    isParsing.value = true
    ElMessage.info('开始解析文件，请稍候...')

    // 开始解析
    const parseResponse = await DecadePlanAPI.parseFile(batchId)
    
    if (parseResponse.code === 200) {
      parseResult.value = parseResponse
      decadePlanStore.setParseResults(parseResponse.data)
      
      // 直接完成解析，不显示消息（由外层处理）
      emit('parse-success', parseResponse)
    } else if (parseResponse.code === 202) {
      // 解析中，开始轮询状态
      ElMessage.info('文件解析中，请稍候...')
      await pollParseStatus(batchId)
    }

  } catch (error) {
    handleError(error, '文件解析')
  } finally {
    isParsing.value = false
  }
}

const pollParseStatus = async (batchId: string) => {
  try {
    await DecadePlanAPI.pollParseStatus(
      batchId,
      (statusResponse) => {
        decadePlanStore.setImportStatus(statusResponse.data)
        
        const status = statusResponse.data.import_status
        if (status === 'COMPLETED') {
          // 解析完成，获取解析结果，但不显示重复的成功消息
          getParseResult(batchId, false)
          // 移除这里的成功消息，由外层统一处理
        }
      }
    )
  } catch (error) {
    console.error('轮询解析状态失败:', error)
    ElMessage.error('获取解析状态失败')
  }
}

const getParseResult = async (batchId: string, showMessage: boolean = true) => {
  try {
    // 先获取状态信息
    const statusResponse = await DecadePlanAPI.getParseStatus(batchId)
    
    // 如果解析完成，尝试获取详细的旬计划数据
    if (statusResponse.data.import_status === 'COMPLETED') {
      try {
        const decadePlansResponse = await DecadePlanAPI.getDecadePlans(batchId)
        
        // 构造完整的解析结果，包含真实数据
        const result: ParseResponse = {
          code: 200,
          message: '解析完成',
          data: {
            import_batch_id: batchId,
            total_records: decadePlansResponse.data.plans.length || statusResponse.data.total_records || 0,
            valid_records: decadePlansResponse.data.plans.filter(p => p.validation_status === 'VALID').length || statusResponse.data.valid_records || 0,
            error_records: decadePlansResponse.data.plans.filter(p => p.validation_status === 'ERROR').length || statusResponse.data.error_records || 0,
            warning_records: decadePlansResponse.data.plans.filter(p => p.validation_status === 'WARNING').length || 0,
            records: decadePlansResponse.data.plans.map(plan => ({
              work_order_nr: plan.work_order_nr,
              article_nr: plan.article_nr,
              package_type: plan.package_type,
              specification: plan.specification,
              feeder_codes: plan.feeder_code ? plan.feeder_code.split(',') : [],
              maker_codes: plan.maker_code ? plan.maker_code.split(',') : [],
              quantity_total: plan.quantity_total,
              final_quantity: plan.final_quantity,
              planned_start: plan.planned_start,
              planned_end: plan.planned_end,
              row_number: plan.row_number,
              validation_status: plan.validation_status,
              validation_message: plan.validation_message
            })),
            errors: [],
            warnings: []
          }
        }
        
        parseResult.value = result
        decadePlanStore.setParseResults(result.data)
        
        console.log('解析结果已获取:', result.data)
        emit('parse-success', result)
        
      } catch (error) {
        console.error('获取旬计划详情失败:', error)
        // 如果获取详情失败，仍然显示基本的解析结果
        const basicParseResult: ParseResponse = {
          code: 200,
          message: '解析完成',
          data: {
            import_batch_id: batchId,
            total_records: statusResponse.data.total_records || 0,
            valid_records: statusResponse.data.valid_records || 0,
            error_records: statusResponse.data.error_records || 0,
            warning_records: 0,
            records: [],
            errors: [],
            warnings: []
          }
        }
        
        parseResult.value = basicParseResult
        decadePlanStore.setParseResults(basicParseResult.data)
        
        console.log('基本解析结果已获取:', basicParseResult.data)
        emit('parse-success', basicParseResult)
      }
    }
    
  } catch (error) {
    console.error('获取解析结果失败:', error)
  }
}

const getProgressText = (): string => {
  if (isUploading.value) {
    return `上传中... ${uploadProgress.value}%`
  } else if (isParsing.value) {
    return '解析中...'
  } else if (uploadProgress.value === 100) {
    return '上传完成'
  }
  return ''
}

const handleViewDetails = (batchId: string) => {
  emit('view-details', batchId)
}
</script>

<style scoped>
.decade-plan-upload {
  max-width: 800px;
  margin: 0 auto;
}

.instruction-content p {
  margin: 4px 0;
  color: #606266;
  font-size: 14px;
}

.upload-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.upload-dragger {
  width: 100%;
}

.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
  height: 180px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text .primary-text {
  font-size: 16px;
  color: #606266;
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

.current-file-info {
  margin-top: 20px;
}

.file-info {
  padding: 16px;
  background-color: #fafafa;
  border-radius: 8px;
}

.file-basic {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.file-icon {
  font-size: 24px;
  color: #409eff;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.file-size {
  font-size: 12px;
  color: #909399;
}

.upload-progress {
  margin-bottom: 16px;
}

.progress-text {
  font-size: 12px;
  color: #606266;
  text-align: center;
  margin-top: 8px;
}

.upload-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.mb-4 {
  margin-bottom: 16px;
}

.mt-4 {
  margin-top: 16px;
}
</style>