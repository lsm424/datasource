import { get, post, put } from '@/utils/request'
import type { 
  User, 
  LoginForm, 
  RegisterForm, 
  LoginResponse, 
  RegisterResponse,
  ChangePasswordForm,
  UpdateUserForm,
  ApiResponse
} from '@/types/auth'

export const authApi = {
  // 用户登录
  login: (data: LoginForm): Promise<LoginResponse> => {
    return post<LoginResponse>('/auth/login', data)
  },

  // 用户注册
  register: (data: RegisterForm): Promise<RegisterResponse> => {
    return post<RegisterResponse>('/auth/register', data)
  },

  // 用户登出
  logout: (): Promise<ApiResponse> => {
    return post<ApiResponse>('/auth/logout')
  },

  // 获取当前用户信息
  getCurrentUser: (): Promise<User> => {
    return get<User>('/auth/me')
  },

  // 刷新token
  refreshToken: (refreshToken: string): Promise<{ token: string; refreshToken: string }> => {
    return post('/auth/refresh', { refreshToken })
  },

  // 修改密码
  changePassword: (data: ChangePasswordForm): Promise<ApiResponse> => {
    return put<ApiResponse>('/auth/password', data)
  },

  // 更新用户信息
  updateProfile: (data: UpdateUserForm): Promise<User> => {
    return put<User>('/auth/profile', data)
  },

  // 发送密码重置邮件
  sendResetPasswordEmail: (email: string): Promise<ApiResponse> => {
    return post<ApiResponse>('/auth/reset-password', { email })
  },

  // 重置密码
  resetPassword: (token: string, newPassword: string): Promise<ApiResponse> => {
    return post<ApiResponse>('/auth/reset-password/confirm', { token, newPassword })
  },

  // 验证重置密码token
  validateResetToken: (token: string): Promise<ApiResponse> => {
    return get<ApiResponse>(`/auth/reset-password/validate/${token}`)
  }
}
