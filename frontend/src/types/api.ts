// API响应基础类型
export interface BaseResponse<T = any> {
  code: number
  message: string
  data?: T
}

export interface SuccessResponse<T = any> extends BaseResponse<T> {
  code: 200
  data: T
}

export interface ErrorResponse extends BaseResponse {
  code: number
  message: string
}

// 文件上传相关类型
export interface ImportBatchInfo {
  import_batch_id: string
  file_name: string
  file_size: number
  upload_time: string
}

export interface UploadResponse extends SuccessResponse<ImportBatchInfo> {}

// 解析结果类型
export interface ParseResultRecord {
  work_order_nr?: string
  article_nr?: string
  package_type?: string
  specification?: string
  feeder_codes?: string[]
  maker_codes?: string[]
  quantity_total?: number
  final_quantity?: number
  planned_start?: string
  planned_end?: string
  production_date_range?: string
  row_number?: number
  validation_status?: 'VALID' | 'WARNING' | 'ERROR'
  validation_message?: string
}

export interface ParseErrorInfo {
  row_number: number
  column_name: string
  error_type: string
  error_message: string
  original_value?: any
}

export interface ParseResult {
  import_batch_id: string
  total_records: number
  valid_records: number
  error_records: number
  warning_records: number
  records: ParseResultRecord[]
  errors: ParseErrorInfo[]
  warnings: ParseErrorInfo[]
}

export interface ParseResponse extends SuccessResponse<ParseResult> {}

// 解析状态类型
export interface ImportStatus {
  import_batch_id: string
  file_name: string
  import_status: 'UPLOADING' | 'PARSING' | 'COMPLETED' | 'FAILED'
  total_records?: number
  valid_records?: number
  error_records?: number
  import_start_time?: string
  import_end_time?: string
  error_message?: string
  created_time: string
}

export interface StatusResponse extends SuccessResponse<ImportStatus> {}

// 旬计划记录类型
export interface DecadePlan {
  work_order_nr: string
  article_nr: string
  package_type?: string
  specification?: string
  feeder_code: string
  maker_code: string
  quantity_total: number
  final_quantity: number
  planned_start?: string
  planned_end?: string
  production_date_range?: string
  row_number?: number
  validation_status: 'VALID' | 'WARNING' | 'ERROR'
  validation_message?: string
}

export interface DecadePlansData {
  import_batch_id: string
  total_plans: number
  plans: DecadePlan[]
}

export interface DecadePlansResponse extends SuccessResponse<DecadePlansData> {}

// 历史记录相关类型
export interface HistoryRecord {
  batch_id: string
  file_name: string
  file_size: number
  upload_time: string
  import_start_time?: string
  import_end_time?: string
  status: string
  total_records?: number
  valid_records?: number
  error_records?: number
  error_message?: string
}

export interface HistoryPagination {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface HistoryResponse {
  code: number
  message: string
  data: {
    records: HistoryRecord[]
    pagination: HistoryPagination
  }
}

// 统计信息类型
export interface StatisticsData {
  today_uploads: number
  monthly_processed: number
  success_rate: number
  active_batches: number
}

export interface StatisticsResponse {
  code: number
  message: string
  data: StatisticsData
}

// 上传项目类型
export interface UploadItem {
  id: string
  file: File | null
  fileName: string
  fileSize: number
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  importBatchId?: string
  uploadTime?: string
  errorMessage?: string
}