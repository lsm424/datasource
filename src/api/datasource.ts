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
  Bucket,
  PaginatedResponse,
  ApiResponse
} from '@/types/datasource'

export const dataSourceApi = {
  // 获取数据源列表
  getDataSources: (params?: DataSourceListQuery): Promise<PaginatedResponse<DataSource>> => {
    return get<PaginatedResponse<DataSource>>('/datasources/', { params })
  },

  // 根据ID获取数据源详情
  getDataSourceById: (id: string): Promise<ApiResponse<DataSource>> => {
    return get<ApiResponse<DataSource>>(`/datasources/${id}`)
  },

  // 创建数据源
  createDataSource: (data: CreateDataSourceForm): Promise<ApiResponse<DataSource>> => {
    return post<ApiResponse<DataSource>>('/datasources/', data)
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
  listFiles: (
    dataSourceId: string, 
    path = '/', 
    page = 1, 
    limit = 100
  ): Promise<ApiResponse<FileSystemItem[]>> => {
    return get<ApiResponse<FileSystemItem[]>>(`/browse/filesystem/${dataSourceId}/list`, {
      params: { path, page, limit }
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

// 对象存储相关API
export const objectStorageApi = {
  // 获取存储桶列表
  listBuckets: (dataSourceId: string): Promise<ApiResponse<Bucket[]>> => {
    return get<ApiResponse<Bucket[]>>(`/browse/object_storage/${dataSourceId}/buckets`)
  },

  // 创建存储桶
  createBucket: (dataSourceId: string, bucketName: string, region?: string): Promise<ApiResponse<Bucket>> => {
    return post<ApiResponse<Bucket>>(`/browse/object_storage/${dataSourceId}/buckets`, {
      name: bucketName,
      region: region || 'us-east-1'
    })
  },

  // 删除存储桶
  deleteBucket: (dataSourceId: string, bucketName: string): Promise<ApiResponse> => {
    return del<ApiResponse>(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}`)
  },

  // 获取对象列表
  listObjects: (
    dataSourceId: string, 
    bucketName: string,
    params?: { prefix?: string; delimiter?: string; max_keys?: number }
  ): Promise<ApiResponse<ObjectStorageObject[]>> => {
    return get<ApiResponse<ObjectStorageObject[]>>(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}/objects`, {
      params
    })
  },

  // 上传文件
  uploadFile: (dataSourceId: string, bucketName: string, objectName: string, file: File): Promise<ApiResponse<any>> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('object_name', objectName)
    
    return post<ApiResponse<any>>(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}/objects`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 下载文件
  downloadObject: (dataSourceId: string, bucketName: string, objectName: string): Promise<Blob> => {
    return get(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}/objects/${objectName}`, {
      responseType: 'blob'
    })
  },

  // 删除对象
  deleteObject: (dataSourceId: string, bucketName: string, objectName: string): Promise<ApiResponse> => {
    return del<ApiResponse>(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}/objects/${objectName}`)
  },

  // 获取对象信息
  getObjectInfo: (dataSourceId: string, bucketName: string, objectName: string): Promise<ApiResponse<ObjectStorageObject>> => {
    return get<ApiResponse<ObjectStorageObject>>(`/browse/object_storage/${dataSourceId}/buckets/${bucketName}/objects/${objectName}/info`)
  },

  // 测试连接
  testConnection: (dataSourceId: string): Promise<ApiResponse<any>> => {
    return post<ApiResponse<any>>(`/browse/object_storage/${dataSourceId}/test`)
  }
}
