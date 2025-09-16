<template>
  <div class="simple-dashboard">
    <div class="dashboard-header">
      <h1>数据浏览系统仪表盘 - 简化版</h1>
      <p>欢迎回来，{{ authStore.currentUser?.name || '用户' }}</p>
    </div>

    <div class="dashboard-content">
      <el-card>
        <h2>🎉 登录成功！</h2>
        <p>恭喜您成功登录到数据浏览系统。</p>
        <div class="user-info">
          <p><strong>用户名:</strong> {{ authStore.currentUser?.username }}</p>
          <p><strong>邮箱:</strong> {{ authStore.currentUser?.email }}</p>
          <p><strong>角色:</strong> {{ authStore.currentUser?.role }}</p>
          <p><strong>认证状态:</strong> {{ authStore.isAuthenticated ? '已认证' : '未认证' }}</p>
        </div>
        
        <div class="actions">
          <el-button v-if="authStore.isAdmin" type="primary" @click="$router.push('/datasources')">
            管理数据源
          </el-button>
          <el-button @click="$router.push('/profile')">
            个人设置
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  document.title = '仪表盘 - 数据浏览系统'
})
</script>

<style scoped>
.simple-dashboard {
  padding: 24px;
  min-height: calc(100vh - 60px);
}

.dashboard-header {
  margin-bottom: 24px;
}

.dashboard-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}

.dashboard-header p {
  color: var(--el-text-color-regular);
  margin: 0;
}

.dashboard-content {
  max-width: 600px;
}

.user-info {
  background: var(--el-fill-color-lighter);
  padding: 16px;
  border-radius: 8px;
  margin: 16px 0;
}

.user-info p {
  margin: 8px 0;
}

.actions {
  margin-top: 16px;
}

.actions .el-button {
  margin-right: 12px;
}
</style>
