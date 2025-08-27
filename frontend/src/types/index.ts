// 全局类型定义
export interface MenuItem {
  key: string
  title: string
  path: string
  icon?: string
}

export interface TableColumn {
  prop: string
  label: string
  width?: number
  minWidth?: number
  fixed?: boolean | 'left' | 'right'
  sortable?: boolean
  formatter?: (row: any, column: any, cellValue: any) => string
}

// 分页相关
export interface PaginationConfig {
  page: number
  size: number
  total: number
}

// 环境变量类型
export interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_PREFIX: string
}

export interface ImportMeta {
  readonly env: ImportMetaEnv
}