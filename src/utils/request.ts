import axios, { type InternalAxiosRequestConfig, type AxiosResponse, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 动态导入auth store避免循环依赖
let authStore: any = null
const getAuthStore = async () => {
  if (!authStore) {
    const { useAuthStore } = await import('@/stores/auth')
    authStore = useAuthStore()
  }
  return authStore
}

// 创建axios实例
const request = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 直接从localStorage获取token，避免Pinia响应式问题
    const token = localStorage.getItem('auth_token')
    
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      }
    }
    
    return config
  },
  (error) => {
    console.error('Request interceptor error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    
    // 如果是直接下载文件等场景，直接返回
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response
    }
    
    // 检查业务状态码
    if (data.code !== undefined && data.code !== 200) {
      console.error('业务错误:', data)
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    
    // 如果响应有包装格式 {code, message, data}，返回内部的data
    // 否则直接返回原数据
    return data.data !== undefined ? data.data : data
  },
  async (error) => {
    console.error('Response interceptor error:', error)
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // 未认证，清除所有认证状态并跳转到登录页
          console.log('🚫 检测到401错误，清除认证状态')
          localStorage.removeItem('auth_token')
          
          // 清除Pinia认证状态
          try {
            const store = await getAuthStore()
            store.clearAuth()
            console.log('✅ 已清除Pinia认证状态')
          } catch (err) {
            console.warn('⚠️ 清除Pinia状态失败:', err)
          }
          
          // 避免重复跳转到登录页
          if (router.currentRoute.value.path !== '/login') {
            router.push('/login')
            ElMessage.error('登录已过期，请重新登录')
          }
          break
        case 403:
          ElMessage.error('没有权限访问该资源')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 422:
          // 表单验证错误
          if (data.message) {
            ElMessage.error(data.message)
          } else if (data.errors && Array.isArray(data.errors)) {
            data.errors.forEach((err: any) => {
              ElMessage.error(err.message || err.msg)
            })
          }
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data?.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default request

// 导出常用的请求方法
export const get = <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.get(url, config)
}

export const post = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  return request.post(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  return request.put(url, data, config)
}

export const patch = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  return request.patch(url, data, config)
}

export const del = <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.delete(url, config)
}
