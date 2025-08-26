import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginForm, RegisterForm } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string>('')
  const isLoading = ref(false)
  const isInitializing = ref(false)
  
  // 存储初始化Promise，用于等待
  let initPromise: Promise<void> | null = null

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => {
    const userRole = user.value?.role
    // 处理两种可能的角色格式：字符串 "admin" 或枚举对象 UserRole.ADMIN
    return userRole === 'admin' || 
           (userRole && typeof userRole === 'object' && 
            (userRole.toString() === 'UserRole.ADMIN' || userRole.value === 'admin'))
  })
  const currentUser = computed(() => user.value)

  // 初始化认证状态
  const initAuth = async () => {
    // 如果正在初始化，等待完成
    if (isInitializing.value && initPromise) {
      console.log('⏳ Auth Store: 认证正在初始化中，等待完成...')
      await initPromise
      console.log('✅ Auth Store: 等待的认证初始化已完成')
      return
    }
    
    // 如果已经有用户信息，跳过初始化
    if (user.value && token.value) {
      console.log('✅ Auth Store: 认证状态已存在，跳过初始化')
      return
    }
    
    // 创建初始化Promise
    initPromise = (async () => {
      isInitializing.value = true
      console.log('🔄 Auth Store: 开始初始化认证状态...')
      
      try {
        const savedToken = localStorage.getItem('auth_token')
        console.log('🔐 Auth Store: 本地Token状态:', savedToken ? `存在(${savedToken.length}字符)` : '不存在')
        
        if (savedToken) {
          // 检查token是否过期
          if (isTokenExpired()) {
            console.log('⏰ Auth Store: 检测到token已过期，清除认证状态')
            clearAuth()
            return
          }
          
          token.value = savedToken
          console.log('✅ Auth Store: Token已设置到store')
          
          try {
            console.log('🌐 Auth Store: 调用getCurrentUser API...')
            const userData = await authApi.getCurrentUser()
            console.log('📨 Auth Store: getCurrentUser响应:', userData)
            console.log('🔍 Auth Store: 响应数据类型:', typeof userData, Array.isArray(userData))
            
            user.value = userData
            console.log('✅ Auth Store: 用户信息已设置:', user.value)
            console.log('🔐 Auth Store: 认证状态检查 - token:', !!token.value, 'user:', !!user.value, 'isAuthenticated:', isAuthenticated.value)
          } catch (error) {
            console.error('❌ Auth Store: getCurrentUser失败:', error)
            // Token可能已过期，清除本地存储
            clearAuth()
          }
        } else {
          console.log('ℹ️ Auth Store: 没有保存的token，跳过认证初始化')
        }
      } finally {
        isInitializing.value = false
        initPromise = null
      }
    })()
    
    await initPromise
  }

  // 登录
  const login = async (loginForm: LoginForm) => {
    console.log('🏪 Auth Store: 开始登录...')
    isLoading.value = true
    try {
      console.log('🌐 Auth Store: 调用登录API...')
      const response = await authApi.login(loginForm)
      console.log('📨 Auth Store: API响应:', response)
      
      // 处理后端返回的数据格式：{code, message, data: {token, user}}
      const loginData = response.data || response
      token.value = loginData.token.access_token // 修复：提取access_token字符串
      user.value = loginData.user
      
      console.log('🔧 解析后的登录数据:', {
        access_token: loginData.token.access_token ? '存在' : '不存在',
        token_type: loginData.token.token_type,
        user: loginData.user
      })
      
      // 保存到本地存储
      if (loginData.token.access_token) {
        localStorage.setItem('auth_token', loginData.token.access_token)
        localStorage.setItem('auth_token_timestamp', Date.now().toString())
        console.log('💾 Auth Store: Token已保存到localStorage')
      } else {
        console.error('❌ Auth Store: 登录响应中没有access_token!')
      }
      
      console.log('✅ Auth Store: 登录状态更新完成:', {
        user: user.value,
        isAuthenticated: isAuthenticated.value,
        tokenExists: !!token.value
      })
      
      return loginData
    } catch (error) {
      console.error('❌ Auth Store: 登录失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // 注册
  const register = async (registerForm: RegisterForm) => {
    isLoading.value = true
    try {
      const response = await authApi.register(registerForm)
      
      // 处理后端返回的数据格式：{code, message, data: {token, user}}
      const registerData = response.data || response
      token.value = registerData.token.access_token // 修复：提取access_token字符串
      user.value = registerData.user
      
      // 保存到本地存储
      if (registerData.token.access_token) {
        localStorage.setItem('auth_token', registerData.token.access_token)
        localStorage.setItem('auth_token_timestamp', Date.now().toString())
      }
      
      return registerData
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  const logout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuth()
    }
  }

  // 验证token有效性
  const validateToken = async () => {
    if (!token.value) {
      return false
    }
    
    try {
      // 尝试获取当前用户信息来验证token
      const userData = await authApi.getCurrentUser()
      if (userData) {
        // 更新用户信息（可能有变化）
        user.value = userData
        return true
      }
      return false
    } catch (error) {
      console.warn('⚠️ Token验证失败:', error)
      // Token无效，清除认证状态
      clearAuth()
      return false
    }
  }

  // 检查token是否过期（基于localStorage的时间戳）
  const isTokenExpired = () => {
    const tokenTimestamp = localStorage.getItem('auth_token_timestamp')
    if (!tokenTimestamp) {
      return true
    }
    
    // 假设token有效期为60分钟（可以从后端配置获取）
    const tokenValidityPeriod = 60 * 60 * 1000 // 60分钟
    const now = Date.now()
    const tokenAge = now - parseInt(tokenTimestamp)
    
    return tokenAge > tokenValidityPeriod
  }

  // 清除认证状态
  const clearAuth = () => {
    console.log('🧹 清除认证状态')
    user.value = null
    token.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_token_timestamp')
    isInitializing.value = false
    initPromise = null
  }

  // 更新用户信息
  const updateUser = (userData: Partial<User>) => {
    if (user.value) {
      user.value = { ...user.value, ...userData }
    }
  }

  return {
    // 状态
    user: readonly(user),
    token: readonly(token),
    isLoading: readonly(isLoading),
    isInitializing: readonly(isInitializing),
    
    // 计算属性
    isAuthenticated,
    isAdmin,
    currentUser,
    
    // 方法
    initAuth,
    login,
    register,
    logout,
    clearAuth,
    updateUser,
    validateToken,
    isTokenExpired
  }
})
