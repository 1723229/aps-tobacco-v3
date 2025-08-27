/**
 * 全局错误处理工具
 */

import { ElMessage, ElNotification } from 'element-plus'

/**
 * 错误类型枚举
 */
export enum ErrorType {
  NETWORK = 'NETWORK',
  API = 'API', 
  VALIDATION = 'VALIDATION',
  BUSINESS = 'BUSINESS',
  UNKNOWN = 'UNKNOWN'
}

/**
 * 错误信息接口
 */
export interface ErrorInfo {
  type: ErrorType
  code?: string | number
  message: string
  detail?: any
  timestamp: Date
}

/**
 * 错误处理器类
 */
export class ErrorHandler {
  private static instance: ErrorHandler
  private errorLog: ErrorInfo[] = []

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler()
    }
    return ErrorHandler.instance
  }

  /**
   * 处理错误
   * @param error 错误对象
   * @param context 错误上下文
   */
  handle(error: any, context?: string): ErrorInfo {
    const errorInfo = this.parseError(error, context)
    this.logError(errorInfo)
    this.showError(errorInfo)
    return errorInfo
  }

  /**
   * 解析错误
   * @param error 错误对象
   * @param context 错误上下文
   */
  private parseError(error: any, context?: string): ErrorInfo {
    let errorInfo: ErrorInfo = {
      type: ErrorType.UNKNOWN,
      message: '发生未知错误',
      timestamp: new Date()
    }

    if (error?.response) {
      // HTTP错误
      const { status, data } = error.response
      errorInfo = {
        type: ErrorType.API,
        code: status,
        message: data?.message || data?.detail || `HTTP ${status} 错误`,
        detail: data,
        timestamp: new Date()
      }
    } else if (error?.code === 'NETWORK_ERROR') {
      // 网络错误
      errorInfo = {
        type: ErrorType.NETWORK,
        message: '网络连接失败，请检查网络设置',
        timestamp: new Date()
      }
    } else if (error?.name === 'ValidationError') {
      // 验证错误
      errorInfo = {
        type: ErrorType.VALIDATION,
        message: error.message || '数据验证失败',
        detail: error.details,
        timestamp: new Date()
      }
    } else if (error?.message) {
      // 一般错误
      errorInfo = {
        type: ErrorType.BUSINESS,
        message: error.message,
        detail: error,
        timestamp: new Date()
      }
    }

    if (context) {
      errorInfo.message = `${context}: ${errorInfo.message}`
    }

    return errorInfo
  }

  /**
   * 记录错误
   * @param errorInfo 错误信息
   */
  private logError(errorInfo: ErrorInfo): void {
    // 添加到错误日志
    this.errorLog.unshift(errorInfo)
    
    // 限制日志数量
    if (this.errorLog.length > 100) {
      this.errorLog = this.errorLog.slice(0, 100)
    }

    // 控制台输出
    console.error('[ErrorHandler]', errorInfo)

    // TODO: 发送到日志服务
    // this.sendToLogService(errorInfo)
  }

  /**
   * 显示错误
   * @param errorInfo 错误信息
   */
  private showError(errorInfo: ErrorInfo): void {
    switch (errorInfo.type) {
      case ErrorType.NETWORK:
        ElNotification.error({
          title: '网络错误',
          message: errorInfo.message,
          duration: 5000
        })
        break

      case ErrorType.API:
        if (errorInfo.code === 401) {
          ElMessage.error('登录已过期，请重新登录')
          // TODO: 跳转到登录页
        } else if (errorInfo.code === 403) {
          ElMessage.error('没有权限执行此操作')
        } else {
          ElMessage.error(errorInfo.message)
        }
        break

      case ErrorType.VALIDATION:
        ElMessage.warning(errorInfo.message)
        break

      case ErrorType.BUSINESS:
        ElMessage.error(errorInfo.message)
        break

      default:
        ElMessage.error(errorInfo.message)
    }
  }

  /**
   * 获取错误日志
   */
  getErrorLog(): ErrorInfo[] {
    return [...this.errorLog]
  }

  /**
   * 清空错误日志
   */
  clearErrorLog(): void {
    this.errorLog = []
  }
}

/**
 * 全局错误处理函数
 */
export function handleError(error: any, context?: string): ErrorInfo {
  return ErrorHandler.getInstance().handle(error, context)
}

/**
 * 异步操作错误处理装饰器
 */
export function withErrorHandler<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  context?: string
): T {
  return ((...args: any[]) => {
    return fn(...args).catch((error: any) => {
      handleError(error, context)
      throw error
    })
  }) as T
}

/**
 * 安全执行异步操作
 */
export async function safeAsync<T>(
  operation: () => Promise<T>,
  context?: string,
  defaultValue?: T
): Promise<T | undefined> {
  try {
    return await operation()
  } catch (error) {
    handleError(error, context)
    return defaultValue
  }
}