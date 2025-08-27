import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { UploadItem, ParseResult, DecadePlan, ImportStatus } from '@/types/api'

export const useDecadePlanStore = defineStore('decadePlan', () => {
  // 状态
  const uploadList = ref<UploadItem[]>([])
  const currentUpload = ref<UploadItem | null>(null)
  const isUploading = ref(false)
  const parseResults = ref<ParseResult | null>(null)
  const decadePlans = ref<DecadePlan[]>([])
  const currentBatchId = ref<string>('')
  const importStatus = ref<ImportStatus | null>(null)

  // 计算属性
  const hasUploadHistory = computed(() => uploadList.value.length > 0)
  const currentUploadProgress = computed(() => currentUpload.value?.progress || 0)
  const successfulUploads = computed(() => 
    uploadList.value.filter(item => item.status === 'success')
  )

  // 方法
  function addUploadItem(item: UploadItem) {
    uploadList.value.unshift(item)
  }

  function updateUploadItem(id: string, updates: Partial<UploadItem>) {
    const index = uploadList.value.findIndex(item => item.id === id)
    if (index !== -1) {
      uploadList.value[index] = { ...uploadList.value[index], ...updates }
    }
    if (currentUpload.value?.id === id) {
      currentUpload.value = { ...currentUpload.value, ...updates }
    }
  }

  function setCurrentUpload(item: UploadItem | null) {
    currentUpload.value = item
  }

  function setIsUploading(status: boolean) {
    isUploading.value = status
  }

  function setParseResults(results: ParseResult | null) {
    parseResults.value = results
  }

  function setDecadePlans(plans: DecadePlan[]) {
    decadePlans.value = plans
  }

  function setCurrentBatchId(batchId: string) {
    currentBatchId.value = batchId
  }

  function setImportStatus(status: ImportStatus | null) {
    importStatus.value = status
  }

  function clearCurrentData() {
    currentUpload.value = null
    parseResults.value = null
    decadePlans.value = []
    currentBatchId.value = ''
    importStatus.value = null
  }

  return {
    // 状态
    uploadList,
    currentUpload,
    isUploading,
    parseResults,
    decadePlans,
    currentBatchId,
    importStatus,
    
    // 计算属性
    hasUploadHistory,
    currentUploadProgress,
    successfulUploads,
    
    // 方法
    addUploadItem,
    updateUploadItem,
    setCurrentUpload,
    setIsUploading,
    setParseResults,
    setDecadePlans,
    setCurrentBatchId,
    setImportStatus,
    clearCurrentData
  }
})