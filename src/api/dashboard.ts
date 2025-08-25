import { get, post } from '@/utils/request'
import type { ApiResponse } from '@/types/datasource'

// 仪表盘统计数据接口
export interface DashboardStats {
  total_datasources: number
  total_users: number
  total_data_size: number
  total_files: number
  total_records: number
  stats_date?: string
  is_admin: boolean
}

// 系统状态接口
export interface SystemStatus {
  database: boolean
  cache: boolean
  version: string
  scheduler: {
    status: string
    jobs: Array<{
      id: string
      name: string
      next_run_time: string | null
      trigger: string
    }>
  }
  last_stats_task: {
    status: string
    date: string | null
    duration: number | null
  } | null
}

// 数据类型分布接口
export interface TypeDistribution {
  name: string
  value: number
  count: number
  type: string
}

// 数据源分布接口
export interface DataSourceDistribution {
  name: string
  type: string
  size: number
  records: number
  files: number
}

// 历史统计数据接口
export interface HistoryStats {
  date: string
  total_datasources: number
  total_data_size: number
  total_files: number
  total_records: number
  filesystem_size: number
  database_size: number
  object_storage_size: number
}

// 仪表盘API
export const dashboardApi = {
  // 获取仪表盘统计数据
  getStats: (): Promise<ApiResponse<DashboardStats>> => {
    return get<ApiResponse<DashboardStats>>('/dashboard/stats')
  },

  // 获取系统状态
  getSystemStatus: (): Promise<ApiResponse<SystemStatus>> => {
    return get<ApiResponse<SystemStatus>>('/dashboard/system-status')
  },

  // 获取数据类型分布
  getTypeDistribution: (): Promise<ApiResponse<{distribution: TypeDistribution[], stats_date: string | null}>> => {
    return get<ApiResponse<{distribution: TypeDistribution[], stats_date: string | null}>>('/dashboard/type-distribution')
  },

  // 获取数据源分布
  getDataSourceDistribution: (limit: number = 10): Promise<ApiResponse<{distribution: DataSourceDistribution[], stats_date: string | null}>> => {
    return get<ApiResponse<{distribution: DataSourceDistribution[], stats_date: string | null}>>('/dashboard/datasource-distribution', { limit })
  },

  // 获取历史统计数据
  getStatsHistory: (days: number = 30): Promise<ApiResponse<HistoryStats[]>> => {
    return get<ApiResponse<HistoryStats[]>>('/dashboard/stats-history', { days })
  },

  // 手动执行统计任务（仅管理员）
  runManualStats: (targetDate?: string): Promise<ApiResponse<{target_date: string, status: string}>> => {
    const params = targetDate ? { target_date: targetDate } : {}
    return post<ApiResponse<{target_date: string, status: string}>>('/dashboard/run-stats', {}, params)
  }
}
