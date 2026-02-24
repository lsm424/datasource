<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // 初始化应用时检查用户登录状态
  await authStore.initAuth()
})
</script>

<style scoped>
#app {
  height: 100vh;
  width: 100vw;
}
</style>
