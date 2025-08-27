import httpClient from '@/utils/http'
import type {
  UploadResponse,
  ParseResponse,
  StatusResponse,
  DecadePlansResponse,
  HistoryResponse,
  StatisticsResponse
} from '@/types/api'

// API路径前缀
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1'

export class DecadePlanAPI {
  /**
   * 上传旬计划文件
   * @param file Excel文件
   * @param onProgress 上传进度回调
   * @returns 上传结果
   */
  static async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await httpClient.post<UploadResponse>(
      `${API_PREFIX}/plans/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            onProgress(progress)
          }
        },
      }
    )
    
    return response.data
  }

  /**
   * 解析旬计划文件
   * @param importBatchId 导入批次ID
   * @param forceReparse 是否强制重新解析
   * @returns 解析结果
   */
  static async parseFile(
    importBatchId: string,
    forceReparse: boolean = false
  ): Promise<ParseResponse> {
    const response = await httpClient.post<ParseResponse>(
      `${API_PREFIX}/plans/${importBatchId}/parse`,
      {},
      {
        params: {
          force_reparse: forceReparse
        }
      }
    )
    
    return response.data
  }

  /**
   * 查询解析状态
   * @param importBatchId 导入批次ID
   * @returns 状态信息
   */
  static async getParseStatus(importBatchId: string): Promise<StatusResponse> {
    const response = await httpClient.get<StatusResponse>(
      `${API_PREFIX}/plans/${importBatchId}/status`
    )
    
    return response.data
  }

  /**
   * 查询旬计划记录
   * @param importBatchId 导入批次ID
   * @returns 旬计划记录列表
   */
  static async getDecadePlans(importBatchId: string): Promise<DecadePlansResponse> {
    const response = await httpClient.get<DecadePlansResponse>(
      `${API_PREFIX}/plans/${importBatchId}/decade-plans`
    )
    
    return response.data
  }

  /**
   * 轮询解析状态直到完成
   * @param importBatchId 导入批次ID
   * @param onStatusUpdate 状态更新回调
   * @param maxAttempts 最大轮询次数
   * @param interval 轮询间隔(毫秒)
   * @returns 最终状态
   */
  static async pollParseStatus(
    importBatchId: string,
    onStatusUpdate?: (status: StatusResponse) => void,
    maxAttempts: number = 30,
    interval: number = 2000
  ): Promise<StatusResponse> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const statusResponse = await this.getParseStatus(importBatchId)
        
        if (onStatusUpdate) {
          onStatusUpdate(statusResponse)
        }
        
        const status = statusResponse.data.import_status
        
        // 如果解析完成或失败，返回结果
        if (status === 'COMPLETED' || status === 'FAILED') {
          return statusResponse
        }
        
        // 等待下次轮询
        if (attempt < maxAttempts - 1) {
          await new Promise(resolve => setTimeout(resolve, interval))
        }
      } catch (error) {
        console.error('轮询解析状态失败:', error)
        
        // 如果是最后一次尝试，抛出错误
        if (attempt === maxAttempts - 1) {
          throw error
        }
        
        // 否则等待重试
        await new Promise(resolve => setTimeout(resolve, interval))
      }
    }
    
    throw new Error('解析状态轮询超时')
  }

  /**
   * 获取上传历史记录
   * @param page 页码，从1开始
   * @param pageSize 每页大小
   * @param status 过滤状态
   * @returns 历史记录列表
   */
  static async getUploadHistory(
    page: number = 1,
    pageSize: number = 20,
    status?: string
  ): Promise<HistoryResponse> {
    const params: any = {
      page,
      page_size: pageSize
    }
    
    if (status) {
      params.status = status
    }
    
    const response = await httpClient.get<HistoryResponse>(
      `${API_PREFIX}/plans/history`,
      { params }
    )
    
    return response.data
  }

  /**
   * 获取统计信息
   * @returns 统计数据
   */
  static async getStatistics(): Promise<StatisticsResponse> {
    const response = await httpClient.get<StatisticsResponse>(
      `${API_PREFIX}/plans/statistics`
    )
    
    return response.data
  }
}

export default DecadePlanAPI