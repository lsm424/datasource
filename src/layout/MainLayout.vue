<template>
  <el-container class="layout-container">
    <!-- 顶部导航 -->
    <el-header class="main-header">
      <div class="header-content">
        <div class="header-left">
          <el-icon class="menu-icon" @click="toggleSidebar" v-if="isMobile">
            <Menu />
          </el-icon>
          <h1 class="app-title">{{ settings.PROJECT_NAME || '数据浏览系统' }}</h1>
        </div>
        
        <div class="header-right">
          <!-- 用户信息和菜单 -->
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar 
                :src="authStore.currentUser?.avatar" 
                :size="32"
              >
                {{ authStore.currentUser?.name?.charAt(0) }}
              </el-avatar>
              <span class="username">{{ authStore.currentUser?.name }}</span>
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  系统设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>

    <el-container>
      <!-- 侧边栏 -->
      <el-aside 
        :width="sidebarWidth" 
        class="main-aside"
        :class="{ 'sidebar-collapsed': isCollapsed }"
      >
        <div class="sidebar-content">
          <!-- 侧边栏菜单 -->
          <el-menu
            :default-active="$route.path"
            :collapse="isCollapsed"
            :unique-opened="true"
            router
            class="sidebar-menu"
            :key="menuKey"
          >
            <el-menu-item index="/dashboard">
              <el-icon><Odometer /></el-icon>
              <template #title>仪表盘</template>
            </el-menu-item>

            <!-- 数据源管理 -->
            <el-sub-menu index="datasources" v-if="authStore.isAdmin">
              <template #title>
                <el-icon><DataBoard /></el-icon>
                <span>数据源管理</span>
              </template>
              <el-menu-item index="/datasources">
                <el-icon><List /></el-icon>
                <template #title>数据源列表</template>
              </el-menu-item>
              <el-menu-item index="/datasources/create">
                <el-icon><Plus /></el-icon>
                <template #title>添加数据源</template>
              </el-menu-item>
            </el-sub-menu>

            <!-- 数据浏览 -->
            <el-sub-menu index="browse" v-if="availableDataSources && availableDataSources.length > 0">
              <template #title>
                <el-icon><View /></el-icon>
                <span>数据浏览</span>
              </template>
              <el-menu-item 
                v-for="datasource in availableDataSources" 
                :key="`datasource-${datasource.id}`"
                :index="`/browse/${datasource.type}/${datasource.id}`"
              >
                <el-icon>
                  <Folder v-if="datasource.type === 'filesystem'" />
                  <Coin v-else-if="datasource.type === 'database'" />
                  <Box v-else />
                </el-icon>
                <template #title>{{ datasource.cname || datasource.name }}</template>
              </el-menu-item>
            </el-sub-menu>

            <!-- 用户管理 -->
            <el-menu-item index="/users" v-if="authStore.isAdmin">
              <el-icon><UserFilled /></el-icon>
              <template #title>用户管理</template>
            </el-menu-item>

            <!-- 个人中心 -->
            <el-menu-item index="/profile">
              <el-icon><User /></el-icon>
              <template #title>个人中心</template>
            </el-menu-item>
          </el-menu>
        </div>

        <!-- 侧边栏折叠按钮 -->
        <div class="sidebar-toggle" @click="toggleSidebar" v-if="!isMobile">
          <el-icon>
            <Expand v-if="isCollapsed" />
            <Fold v-else />
          </el-icon>
        </div>
      </el-aside>

      <!-- 主内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Menu,
  ArrowDown,
  User,
  Setting,
  SwitchButton,
  Odometer,
  DataBoard,
  List,
  Plus,
  View,
  Folder,
  Coin,
  Box,
  UserFilled,
  Expand,
  Fold
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'

const router = useRouter()
const authStore = useAuthStore()
const dataSourceStore = useDataSourceStore()

// 响应式数据
const isCollapsed = ref(false)
const isMobile = ref(false)
const menuKey = ref(0)

// 计算属性
const sidebarWidth = computed(() => {
  if (isMobile.value && !isCollapsed.value) return '200px'
  return isCollapsed.value ? '64px' : '200px'
})

const availableDataSources = computed(() => {
  // 安全检查：确保dataSources是数组
  if (!dataSourceStore.dataSources || !Array.isArray(dataSourceStore.dataSources)) {
    return []
  }
  return dataSourceStore.dataSources.filter(ds => ds && ds.is_active)
})

const settings = {
  PROJECT_NAME: '数据浏览系统'
}

// 方法
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const handleCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      ElMessage.info('系统设置功能开发中...')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '确认退出',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        await authStore.logout()
        ElMessage.success('已成功退出登录')
        router.push('/login')
      } catch (error) {
        // 用户取消或其他错误
        console.error('Logout error:', error)
      }
      break
  }
}

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    isCollapsed.value = true
  }
}

// 生命周期
onMounted(async () => {
  checkIsMobile()
  window.addEventListener('resize', checkIsMobile)
  
  // 等待认证状态初始化完成后再获取数据源列表
  if (authStore.isAuthenticated) {
    try {
      await dataSourceStore.fetchDataSources()
    } catch (error) {
      console.error('❌ MainLayout: 获取数据源列表失败:', error)
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile)
})

// 监听数据源变化，强制菜单重新渲染以避免slot警告
watch(
  () => dataSourceStore.dataSources,
  () => {
    menuKey.value++
  },
  { deep: true }
)

// 监听认证状态变化
watch(
  () => authStore.isAuthenticated,
  (isAuth) => {
    if (isAuth) {
      menuKey.value++
    }
  }
)
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.main-header {
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  padding: 0;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-icon {
  font-size: 20px;
  cursor: pointer;
  color: var(--el-text-color-regular);
}

.app-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: var(--el-fill-color-light);
}

.username {
  font-size: 14px;
  color: var(--el-text-color-regular);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-aside {
  background: #fff;
  border-right: 1px solid var(--el-border-color-light);
  transition: width 0.3s ease;
  position: relative;
}

.sidebar-content {
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.sidebar-toggle {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 100;
}

.sidebar-toggle:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.main-content {
  background: var(--el-bg-color-page);
  overflow: auto;
  padding: 0;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .header-content {
    padding: 0 16px;
  }
  
  .app-title {
    font-size: 16px;
  }
  
  .username {
    display: none;
  }
  
  .sidebar-collapsed .main-aside {
    width: 0 !important;
    overflow: hidden;
  }
}

/* 暗色主题适配 */
html.dark .main-header {
  background: var(--el-bg-color);
  border-bottom-color: var(--el-border-color);
}

html.dark .main-aside {
  background: var(--el-bg-color);
  border-right-color: var(--el-border-color);
}
</style>
