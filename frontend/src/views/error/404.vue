<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-illustration">
        <div class="error-number">404</div>
        <div class="error-icon">
          <el-icon :size="120">
            <WarningFilled />
          </el-icon>
        </div>
      </div>
      
      <div class="error-text">
        <h1>页面不存在</h1>
        <p>抱歉，您访问的页面不存在或已被移除。</p>
        <p class="error-url">访问地址：{{ $route.fullPath }}</p>
      </div>
      
      <div class="error-actions">
        <el-button type="primary" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          回到首页
        </el-button>
        
        <el-button @click="goBack">
          <el-icon><Back /></el-icon>
          返回上页
        </el-button>
        
        <el-button @click="reload">
          <el-icon><Refresh /></el-icon>
          刷新页面
        </el-button>
      </div>
    </div>
    
    <!-- 背景装饰 -->
    <div class="error-bg">
      <div class="bg-circle circle-1"></div>
      <div class="bg-circle circle-2"></div>
      <div class="bg-circle circle-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  WarningFilled,
  HomeFilled,
  Back,
  Refresh
} from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => {
  router.push('/dashboard')
}

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/dashboard')
  }
}

const reload = () => {
  window.location.reload()
}

// 页面标题
document.title = '页面不存在 - 数据浏览系统'
</script>

<style scoped>
.error-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.error-content {
  text-align: center;
  color: white;
  position: relative;
  z-index: 10;
  max-width: 600px;
  padding: 40px 20px;
}

.error-illustration {
  position: relative;
  margin-bottom: 40px;
}

.error-number {
  font-size: 120px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 20px;
  background: linear-gradient(45deg, #ff6b6b, #feca57);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.error-icon {
  color: rgba(255, 255, 255, 0.8);
  animation: float 3s ease-in-out infinite;
}

.error-text h1 {
  font-size: 32px;
  font-weight: 600;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.error-text p {
  font-size: 16px;
  margin: 8px 0;
  opacity: 0.9;
}

.error-url {
  font-size: 14px;
  font-family: 'Courier New', monospace;
  background: rgba(255, 255, 255, 0.1);
  padding: 8px 16px;
  border-radius: 20px;
  display: inline-block;
  margin: 16px 0;
  word-break: break-all;
}

.error-actions {
  margin-top: 40px;
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.error-actions .el-button {
  min-width: 120px;
  height: 44px;
  font-size: 14px;
  border-radius: 22px;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  transition: all 0.3s;
}

.error-actions .el-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.error-actions .el-button.el-button--primary {
  background: rgba(255, 255, 255, 0.9);
  color: var(--el-color-primary);
}

.error-actions .el-button.el-button--primary:hover {
  background: white;
}

/* 背景装饰 */
.error-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  animation: float 6s ease-in-out infinite;
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -150px;
  left: -150px;
  animation-delay: 0s;
}

.circle-2 {
  width: 200px;
  height: 200px;
  top: 50%;
  right: -100px;
  animation-delay: 2s;
}

.circle-3 {
  width: 150px;
  height: 150px;
  bottom: -75px;
  left: 30%;
  animation-delay: 4s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .error-content {
    padding: 20px 16px;
  }
  
  .error-number {
    font-size: 80px;
  }
  
  .error-text h1 {
    font-size: 24px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .error-actions .el-button {
    width: 100%;
    max-width: 200px;
  }
}

@media (max-width: 480px) {
  .error-number {
    font-size: 60px;
  }
  
  .error-text h1 {
    font-size: 20px;
  }
  
  .error-text p {
    font-size: 14px;
  }
  
  .error-url {
    font-size: 12px;
    padding: 6px 12px;
  }
}
</style>
