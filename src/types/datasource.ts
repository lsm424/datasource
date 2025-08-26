// 数据源类型枚举
export enum DataSourceType {
  FILESYSTEM = 'filesystem',
  DATABASE = 'database',
  OBJECT_STORAGE = 'object_storage'
}

// 数据库类型枚举
export enum DatabaseType {
  MYSQL = 'MySQL',
  POSTGRESQL = 'PostgreSQL',
  SQLITE = 'SQLite',
  ORACLE = 'Oracle',
  SQLSERVER = 'SQLServer'
}

// 基础数据源接口
export interface BaseDataSource {
  id: string
  name: string
  cname: string
  company: string
  source: string
  type: DataSourceType
  desc: string
  num: number
  size: number
  created_at: string
  updated_at: string
  is_active: boolean
  is_connected?: boolean
  last_test_at?: string
  last_test_status?: string
  last_test_message?: string
}

// 文件系统数据源配置
export interface FilesystemConfig {
  path: string
  encoding?: string
  extensions?: string[]
}

// 数据库数据源配置
export interface DatabaseConfig {
  db_type: DatabaseType
  host: string
  port: number
  database: string
  user: string
  password: string
  charset?: string
  ssl?: boolean
  connectionTimeout?: number
}

// 对象存储数据源配置
export interface ObjectStorageConfig {
  bucket: string
  endpoint: string
  accessKey: string
  secretKey: string
  region?: string
  ssl?: boolean
}

// 数据源接口（联合类型）
export interface DataSource extends BaseDataSource {
  config: FilesystemConfig | DatabaseConfig | ObjectStorageConfig
}

// 创建数据源表单接口
export interface CreateDataSourceForm {
  name: string
  cname: string
  company: string
  source: string
  type: DataSourceType
  desc: string
  config: FilesystemConfig | DatabaseConfig | ObjectStorageConfig
}

// 更新数据源表单接口
export interface UpdateDataSourceForm {
  name?: string
  cname?: string
  company?: string
  source?: string
  desc?: string
  config?: FilesystemConfig | DatabaseConfig | ObjectStorageConfig
  isActive?: boolean
}

// 数据源列表查询参数
export interface DataSourceListQuery {
  page?: number
  limit?: number
  type?: DataSourceType
  isActive?: boolean
  search?: string
}

// 连接测试结果
export interface ConnectionTestResult {
  success: boolean
  message: string
  details?: any
}

// 文件系统项目接口
export interface FileSystemItem {
  name: string
  path: string
  type: 'file' | 'directory'
  size: number
  modifiedAt: string
  permissions?: string
  extension?: string
}

// 数据库表接口
export interface DatabaseTable {
  name: string
  schema?: string
  rowCount: number
  comment?: string
}

// 数据库列接口
export interface DatabaseColumn {
  name: string
  type: string
  nullable: boolean
  defaultValue?: string
  comment?: string
  isPrimaryKey: boolean
  isAutoIncrement: boolean
}

// 数据库记录接口
export interface DatabaseRecord {
  [key: string]: any
}

// 存储桶接口
export interface Bucket {
  name: string
  creation_date?: string
  region: string
}

// 对象存储对象接口
export interface ObjectStorageObject {
  key: string
  size: number
  last_modified?: string
  etag: string
  content_type?: string
  is_dir?: boolean
  metadata?: Record<string, any>
}

// 分页响应接口
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

// API响应接口
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  timestamp: number
}
