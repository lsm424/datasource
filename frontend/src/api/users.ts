import { get, post, put, del } from '@/utils/request'
import type { User, CreateUserForm, UpdateUserForm } from '@/types/auth'
import type { ApiResponse } from '@/types/datasource'

// 列表响应接口
export interface ListResponse<T> {
  code: number
  message: string
  data: T[]
  total: number
  page: number
  limit: number
  total_pages: number
  timestamp: string
}

// 用户查询参数
export interface UserListQuery {
  page?: number
  limit?: number
  search?: string
  role?: string
  role_id?: string
  is_active?: boolean
}

// 用户统计信息
export interface UserStats {
  totalUsers: number
  activeUsers: number
  adminUsers: number
  recentUsers: User[]
}

// 用户API
export const userApi = {
  // 获取用户列表
  getUsers: (query?: UserListQuery): Promise<ListResponse<User>> => {
    return get<ListResponse<User>>('/users/', { params: query })
  },

  // 获取用户统计信息
  getUserStats: async (): Promise<UserStats> => {
    // 获取所有用户来计算统计
    const response = await get<ListResponse<User>>('/users', { 
      params: { limit: 1000 } // 获取足够多的数据用于统计
    })
    
    const users = Array.isArray(response) ? response : response.data || []
    
    return {
      totalUsers: users.length,
      activeUsers: users.filter(user => user.isActive).length,
      adminUsers: users.filter(user => user.role === 'admin').length,
      recentUsers: users
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        .slice(0, 5)
    }
  },

  // 获取当前用户信息
  getCurrentUser: (): Promise<ApiResponse<User>> => {
    return get<ApiResponse<User>>('/users/me')
  },

  // 更新当前用户信息
  updateCurrentUser: (data: UpdateUserForm): Promise<ApiResponse<User>> => {
    return put<ApiResponse<User>>('/users/me', data)
  },

  // 根据ID获取用户
  getUserById: (userId: string): Promise<ApiResponse<User>> => {
    return get<ApiResponse<User>>(`/users/${userId}`)
  },

  // 创建用户（管理员）
  createUser: (data: CreateUserForm): Promise<ApiResponse<User>> => {
    return post<ApiResponse<User>>('/users/', data)
  },

  // 更新用户（管理员）
  updateUser: (userId: string, data: any): Promise<ApiResponse<User>> => {
    return put<ApiResponse<User>>(`/users/${userId}`, data)
  },

  // 删除用户（管理员）
  deleteUser: (userId: string): Promise<ApiResponse<any>> => {
    return del<ApiResponse<any>>(`/users/${userId}`)
  }
}
