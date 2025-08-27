/**
 * 工具函数集合
 */

/**
 * 生成唯一ID
 * @returns 唯一字符串ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/**
 * 格式化文件大小
 * @param bytes 字节数
 * @returns 格式化后的文件大小字符串
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * 格式化日期时间
 * @param date 日期字符串或Date对象
 * @param format 格式化模式
 * @returns 格式化后的日期字符串
 */
export function formatDateTime(
  date: string | Date,
  format: 'date' | 'datetime' | 'time' = 'datetime'
): string {
  if (!date) return '-'
  
  const d = typeof date === 'string' ? new Date(date) : date
  
  if (isNaN(d.getTime())) return '-'
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  switch (format) {
    case 'date':
      return `${year}-${month}-${day}`
    case 'time':
      return `${hours}:${minutes}:${seconds}`
    case 'datetime':
    default:
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }
}

/**
 * 验证文件类型
 * @param file 文件对象
 * @param allowedTypes 允许的文件类型数组
 * @returns 是否为允许的文件类型
 */
export function validateFileType(file: File, allowedTypes: string[]): boolean {
  const fileExtension = file.name.split('.').pop()?.toLowerCase()
  if (!fileExtension) return false
  
  return allowedTypes.some(type => {
    // 移除可能的点号前缀
    const cleanType = type.startsWith('.') ? type.substring(1) : type
    return cleanType.toLowerCase() === fileExtension
  })
}

/**
 * 验证文件大小
 * @param file 文件对象
 * @param maxSizeInBytes 最大文件大小（字节）
 * @returns 是否在允许的大小范围内
 */
export function validateFileSize(file: File, maxSizeInBytes: number): boolean {
  return file.size <= maxSizeInBytes
}

/**
 * 防抖函数
 * @param func 要防抖的函数
 * @param delay 延迟时间（毫秒）
 * @returns 防抖后的函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  
  return function(...args: Parameters<T>) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func(...args), delay)
  }
}

/**
 * 节流函数
 * @param func 要节流的函数
 * @param delay 延迟时间（毫秒）
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0
  
  return function(...args: Parameters<T>) {
    const now = Date.now()
    if (now - lastCall >= delay) {
      lastCall = now
      func(...args)
    }
  }
}

/**
 * 深拷贝对象
 * @param obj 要拷贝的对象
 * @returns 深拷贝后的对象
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  
  if (typeof obj === 'object') {
    const clonedObj = {} as T
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }
  
  return obj
}

/**
 * 获取状态对应的颜色
 * @param status 状态字符串
 * @returns Element Plus对应的类型颜色
 */
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'valid':
    case 'success':
    case 'completed':
      return 'success'
    case 'warning':
    case 'pending':
      return 'warning'
    case 'error':
    case 'failed':
      return 'danger'
    case 'uploading':
    case 'parsing':
    case 'in_progress':
      return 'primary'
    default:
      return 'info'
  }
}

/**
 * 获取状态对应的中文显示
 * @param status 状态字符串
 * @returns 中文状态描述
 */
export function getStatusText(status: string): string {
  switch (status.toLowerCase()) {
    case 'valid':
      return '有效'
    case 'warning':
      return '警告'
    case 'error':
      return '错误'
    case 'pending':
      return '待处理'
    case 'uploading':
      return '上传中'
    case 'parsing':
      return '解析中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'success':
      return '成功'
    default:
      return status
  }
}

/**
 * 格式化数字显示
 * @param num 数字
 * @returns 格式化后的数字字符串
 */
export function formatNumber(num: number | undefined | null): string {
  if (num === undefined || num === null || isNaN(num)) return '-'
  return num.toLocaleString()
}