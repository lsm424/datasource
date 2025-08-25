import { get, post, put, del } from '@/utils/request'
import type {
  DataSource,
  CreateDataSourceForm,
  UpdateDataSourceForm,
  DataSourceListQuery,
  ConnectionTestResult,
  FileSystemItem,
  DatabaseTable,
  DatabaseColumn,
  DatabaseRecord,
  ObjectStorageObject,
  PaginatedResponse,
  ApiResponse
} from '@/types/datasource'

export const dataSourceApi = {
  // 获取数据源列表
  getDataSources: (params?: DataSourceListQuery): Promise<PaginatedResponse<DataSource>> => {
    return get<PaginatedResponse<DataSource>>('/datasources', { params })
  },

  // 根据ID获取数据源详情
  getDataSourceById: (id: string): Promise<ApiResponse<DataSource>> => {
    return get<ApiResponse<DataSource>>(`/datasources/${id}`)
  },

  // 创建数据源
  createDataSource: (data: CreateDataSourceForm): Promise<ApiResponse<DataSource>> => {
    return post<ApiResponse<DataSource>>('/datasources', data)
  },

  // 更新数据源
  updateDataSource: (id: string, data: UpdateDataSourceForm): Promise<ApiResponse<DataSource>> => {
    return put<ApiResponse<DataSource>>(`/datasources/${id}`, data)
  },

  // 删除数据源
  deleteDataSource: (id: string): Promise<ApiResponse> => {
    return del<ApiResponse>(`/datasources/${id}`)
  },

  // 测试数据源连接
  testConnection: (config: any): Promise<ConnectionTestResult> => {
    return post<ConnectionTestResult>('/datasources/test-connection', config)
  },

  // 获取数据源统计信息
  getStatistics: (): Promise<ApiResponse<any>> => {
    return get<ApiResponse<any>>('/datasources/statistics')
  }
}

// 文件系统浏览相关API
export const filesystemApi = {
  // 获取文件/目录列表
  listFiles: (dataSourceId: string, path = '/'): Promise<ApiResponse<FileSystemItem[]>> => {
    return get<ApiResponse<FileSystemItem[]>>(`/browse/filesystem/${dataSourceId}/list`, {
      params: { path }
    })
  },

  // 下载文件
  downloadFile: (dataSourceId: string, path: string): Promise<Blob> => {
    return get(`/browse/filesystem/${dataSourceId}/download`, {
      params: { path },
      responseType: 'blob'
    })
  },

  // 获取文件内容（预览）
  getFileContent: (dataSourceId: string, path: string): Promise<ApiResponse<string>> => {
    return get<ApiResponse<string>>(`/browse/filesystem/${dataSourceId}/content`, {
      params: { path }
    })
  },

  // 获取文件信息
  getFileInfo: (dataSourceId: string, path: string): Promise<ApiResponse<FileSystemItem>> => {
    return get<ApiResponse<FileSystemItem>>(`/browse/filesystem/${dataSourceId}/info`, {
      params: { path }
    })
  }
}

// 数据库浏览相关API
export const databaseApi = {
  // 获取数据库列表
  getDatabases: (dataSourceId: string): Promise<ApiResponse<string[]>> => {
    return get<ApiResponse<string[]>>(`/browse/database/${dataSourceId}/databases`)
  },

  // 获取表列表
  getTables: (dataSourceId: string, database?: string): Promise<ApiResponse<DatabaseTable[]>> => {
    return get<ApiResponse<DatabaseTable[]>>(`/browse/database/${dataSourceId}/tables`, {
      params: { database }
    })
  },

  // 获取表结构
  getTableSchema: (dataSourceId: string, tableName: string, database?: string): Promise<ApiResponse<DatabaseColumn[]>> => {
    return get<ApiResponse<DatabaseColumn[]>>(`/browse/database/${dataSourceId}/tables/${tableName}/schema`, {
      params: { database }
    })
  },

  // 获取表数据
  getTableData: (
    dataSourceId: string, 
    tableName: string, 
    params?: { database?: string; page?: number; limit?: number; where?: string }
  ): Promise<PaginatedResponse<DatabaseRecord>> => {
    return get<PaginatedResponse<DatabaseRecord>>(`/browse/database/${dataSourceId}/tables/${tableName}/data`, {
      params
    })
  },

  // 插入数据
  insertRecord: (
    dataSourceId: string, 
    tableName: string, 
    data: DatabaseRecord, 
    database?: string
  ): Promise<ApiResponse<DatabaseRecord>> => {
    return post<ApiResponse<DatabaseRecord>>(`/browse/database/${dataSourceId}/tables/${tableName}/records`, data, {
      params: { database }
    })
  },

  // 更新数据
  updateRecord: (
    dataSourceId: string, 
    tableName: string, 
    recordId: string | number, 
    data: DatabaseRecord, 
    database?: string
  ): Promise<ApiResponse<DatabaseRecord>> => {
    return put<ApiResponse<DatabaseRecord>>(`/browse/database/${dataSourceId}/tables/${tableName}/records/${recordId}`, data, {
      params: { database }
    })
  },

  // 删除数据
  deleteRecord: (
    dataSourceId: string, 
    tableName: string, 
    recordId: string | number, 
    database?: string
  ): Promise<ApiResponse> => {
    return del<ApiResponse>(`/browse/database/${dataSourceId}/tables/${tableName}/records/${recordId}`, {
      params: { database }
    })
  },

  // 执行自定义SQL查询
  executeQuery: (
    dataSourceId: string, 
    sql: string, 
    database?: string
  ): Promise<ApiResponse<{ columns: string[]; rows: any[][] }>> => {
    return post<ApiResponse<{ columns: string[]; rows: any[][] }>>(`/browse/database/${dataSourceId}/query`, {
      sql,
      database
    })
  }
}

// 对象存储浏览相关API
export const objectStorageApi = {
  // 获取对象列表
  listObjects: (
    dataSourceId: string, 
    params?: { prefix?: string; delimiter?: string; marker?: string; maxKeys?: number }
  ): Promise<ApiResponse<ObjectStorageObject[]>> => {
    return get<ApiResponse<ObjectStorageObject[]>>(`/browse/objectstorage/${dataSourceId}/objects`, {
      params
    })
  },

  // 上传文件
  uploadFile: (dataSourceId: string, key: string, file: File): Promise<ApiResponse<ObjectStorageObject>> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('key', key)
    
    return post<ApiResponse<ObjectStorageObject>>(`/browse/objectstorage/${dataSourceId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 下载文件
  downloadObject: (dataSourceId: string, key: string): Promise<Blob> => {
    return get(`/browse/objectstorage/${dataSourceId}/download`, {
      params: { key },
      responseType: 'blob'
    })
  },

  // 获取对象预签名URL
  getPresignedUrl: (dataSourceId: string, key: string, expiration = 3600): Promise<ApiResponse<string>> => {
    return get<ApiResponse<string>>(`/browse/objectstorage/${dataSourceId}/presigned-url`, {
      params: { key, expiration }
    })
  },

  // 删除对象
  deleteObject: (dataSourceId: string, key: string): Promise<ApiResponse> => {
    return del<ApiResponse>(`/browse/objectstorage/${dataSourceId}/objects`, {
      params: { key }
    })
  },

  // 获取对象元数据
  getObjectMetadata: (dataSourceId: string, key: string): Promise<ApiResponse<ObjectStorageObject>> => {
    return get<ApiResponse<ObjectStorageObject>>(`/browse/objectstorage/${dataSourceId}/objects/metadata`, {
      params: { key }
    })
  }
}
