// 用户角色枚举
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user'
}

// 用户信息接口
export interface User {
  id: string
  username: string
  email: string
  name: string
  role: UserRole
  createdAt: string
  updatedAt: string
  lastLoginAt?: string
  isActive: boolean
}

// 登录表单接口
export interface LoginForm {
  username: string
  password: string
  remember?: boolean
}

// 注册表单接口
export interface RegisterForm {
  username: string
  email: string
  name: string
  password: string
  confirmPassword: string
}

// Token接口
export interface Token {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string
}

// 登录响应接口
export interface LoginResponse {
  user: User
  token: Token
}

// 注册响应接口
export interface RegisterResponse {
  user: User
  token: Token
}

// 密码修改表单接口
export interface ChangePasswordForm {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

// 用户更新表单接口
export interface UpdateUserForm {
  name?: string
  email?: string
}

// 用户创建表单接口（管理员用）
export interface CreateUserForm {
  username: string
  email: string
  name: string
  password: string
  role: UserRole
}

// 用户更新表单接口（管理员用）
export interface AdminUpdateUserForm {
  name?: string
  email?: string
  role?: UserRole
  isActive?: boolean
}

// 用户列表查询参数
export interface UserListQuery {
  page?: number
  limit?: number
  role?: UserRole
  isActive?: boolean
  search?: string
}

// API响应接口
export interface ApiResponse {
  code?: number
  message: string
  data?: any
}

// Token数据接口
export interface TokenData {
  userId: string
  username: string
  role: UserRole
}
