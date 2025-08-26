import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 初始化认证状态
const initApp = async () => {
  const authStore = useAuthStore()
  await authStore.initAuth()
  
  // 设置定期检查token有效性
  setInterval(() => {
    if (authStore.isAuthenticated && authStore.isTokenExpired()) {
      console.log('⏰ 定时检查：Token已过期，清除认证状态')
      authStore.clearAuth()
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
  }, 5 * 60 * 1000) // 每5分钟检查一次
  
  app.mount('#app')
}

initApp()
