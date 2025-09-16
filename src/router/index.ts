import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register', 
    component: () => import('@/views/auth/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardEnhanced.vue'),
        meta: { title: '仪表盘' }
      },
      {
        path: '/datasources',
        name: 'DataSources',
        component: () => import('@/views/datasources/DataSourceList.vue'),
        meta: { title: '数据源管理', requiresAdmin: true }
      },
      {
        path: '/datasources/create',
        name: 'CreateDataSource',
        component: () => import('@/views/datasources/CreateDataSource.vue'),
        meta: { title: '创建数据源', requiresAdmin: true }
      },
      {
        path: '/datasources/:id/edit',
        name: 'EditDataSource',
        component: () => import('@/views/datasources/EditDataSource.vue'),
        meta: { title: '编辑数据源', requiresAdmin: true }
      },
      {
        path: '/browse/filesystem/:id',
        name: 'FilesystemBrowser',
        component: () => import('@/views/browser/FilesystemBrowser.vue'),
        meta: { title: '文件系统浏览' }
      },
      {
        path: '/browse/database/:id',
        name: 'DatabaseBrowser',
        component: () => import('@/views/browser/DatabaseBrowser.vue'),
        meta: { title: '数据库浏览' }
      },
      {
        path: '/browse/object_storage/:id',
        name: 'ObjectStorageBrowser',
        component: () => import('@/views/browser/ObjectStorageBrowser.vue'),
        meta: { title: '对象存储浏览' }
      },
      {
        path: '/users',
        name: 'UserManagement',
        component: () => import('@/views/users/UserList.vue'),
        meta: { title: '用户管理', requiresAdmin: true }
      },
      {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/views/users/Profile.vue'),
        meta: { title: '个人信息' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  
  const authStore = useAuthStore()
  
  // 确保认证状态已初始化（如果有token的话）
  if (localStorage.getItem('auth_token') && !authStore.user) {
    try {
      await authStore.initAuth()
    } catch (error) {
      console.error('❌ 路由守卫: 认证初始化失败', error)
    }
  }
  
  
  // 如果路由需要认证
  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      next('/login')
      return
    }
    
    // 额外检查：验证token有效性
    if (authStore.token && authStore.isTokenExpired()) {
      authStore.clearAuth()
      next('/login')
      return
    }
  }
  
  // 如果路由需要管理员权限
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    ElMessage.error('您没有权限访问该页面')
    next('/dashboard')
    return
  }
  
  // 如果已登录用户访问登录页，重定向到首页
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next('/dashboard')
    return
  }
  
  next()
})

export default router
