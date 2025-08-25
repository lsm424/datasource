<template>
  <div class="register-container">
    <div class="register-box">
      <div class="register-header">
        <h1 class="register-title">创建账户</h1>
        <p class="register-subtitle">加入数据浏览系统，开始您的数据探索之旅</p>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="register-form"
        label-position="top"
      >
        <div class="form-row">
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item label="邮箱地址" prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱地址"
              size="large"
              :prefix-icon="Message"
              clearable
            />
          </el-form-item>
        </div>

        <el-form-item label="真实姓名" prop="name">
          <el-input
            v-model="registerForm.name"
            placeholder="请输入真实姓名"
            size="large"
            :prefix-icon="UserFilled"
            clearable
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item label="手机号" prop="phone">
            <el-input
              v-model="registerForm.phone"
              placeholder="请输入手机号（可选）"
              size="large"
              :prefix-icon="Phone"
              clearable
            />
          </el-form-item>

          <el-form-item label="公司/组织" prop="company">
            <el-input
              v-model="registerForm.company"
              placeholder="请输入公司或组织（可选）"
              size="large"
              :prefix-icon="OfficeBuilding"
              clearable
            />
          </el-form-item>
        </div>

        <div class="form-row">
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请确认密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
        </div>

        <el-form-item label="个人简介" prop="bio">
          <el-input
            v-model="registerForm.bio"
            type="textarea"
            placeholder="简单介绍一下自己（可选）"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="agreedToTerms" :disabled="authStore.isLoading">
            我已阅读并同意
            <el-link type="primary">《用户协议》</el-link>
            和
            <el-link type="primary">《隐私政策》</el-link>
          </el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.isLoading"
            :disabled="!agreedToTerms"
            @click="handleRegister"
            class="register-button"
          >
            <span v-if="!authStore.isLoading">创建账户</span>
            <span v-else>创建中...</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <p>
          已有账户？
          <el-link type="primary" @click="$router.push('/login')">
            立即登录
          </el-link>
        </p>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="register-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
      <div class="bg-shape shape-4"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  User,
  UserFilled,
  Message,
  Phone,
  OfficeBuilding,
  Lock
} from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import type { RegisterForm } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const registerFormRef = ref<FormInstance>()

// 注册表单数据
const registerForm = reactive<RegisterForm>({
  username: '',
  email: '',
  name: '',
  phone: '',
  company: '',
  password: '',
  confirmPassword: '',
  bio: ''
})

// 同意条款
const agreedToTerms = ref(false)

// 自定义验证函数
const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validatePassword = (rule: any, value: string, callback: any) => {
  if (value.length < 8) {
    callback(new Error('密码长度至少8位'))
  } else if (!/[A-Z]/.test(value)) {
    callback(new Error('密码必须包含至少一个大写字母'))
  } else if (!/[a-z]/.test(value)) {
    callback(new Error('密码必须包含至少一个小写字母'))
  } else if (!/\d/.test(value)) {
    callback(new Error('密码必须包含至少一个数字'))
  } else {
    callback()
  }
}

// 表单验证规则
const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度应在 3 到 50 个字符之间', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '用户名只能包含字母、数字、下划线和横线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 1, max: 100, message: '姓名长度应在 1 到 100 个字符之间', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await authStore.register(registerForm)
        ElMessage.success('注册成功，欢迎加入！')
        
        // 注册成功后跳转到首页
        router.push('/dashboard')
      } catch (error: any) {
        console.error('Register error:', error)
        ElMessage.error(error.message || '注册失败，请稍后重试')
      }
    }
  })
}

// 页面标题
document.title = '注册 - 数据浏览系统'
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.register-box {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 600px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 10;
}

.register-header {
  text-align: center;
  margin-bottom: 32px;
}

.register-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.register-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.register-form {
  width: 100%;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.register-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #333;
  padding-bottom: 8px;
}

.register-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.register-button {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.register-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

.register-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #eee;
}

.register-footer p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

/* 背景装饰 */
.register-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  z-index: 1;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 8s ease-in-out infinite;
}

.shape-1 {
  width: 200px;
  height: 200px;
  top: -100px;
  left: -100px;
  animation-delay: 0s;
}

.shape-2 {
  width: 150px;
  height: 150px;
  top: 20%;
  right: -75px;
  animation-delay: 2s;
}

.shape-3 {
  width: 100px;
  height: 100px;
  bottom: -50px;
  left: 30%;
  animation-delay: 4s;
}

.shape-4 {
  width: 120px;
  height: 120px;
  top: 60%;
  left: -60px;
  animation-delay: 6s;
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
  .register-container {
    padding: 16px;
  }
  
  .register-box {
    padding: 24px;
    border-radius: 12px;
  }
  
  .register-title {
    font-size: 24px;
  }
  
  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

/* 暗色主题适配 */
@media (prefers-color-scheme: dark) {
  .register-box {
    background: rgba(26, 26, 26, 0.95);
    color: #fff;
  }
  
  .register-title {
    color: #fff;
  }
  
  .register-subtitle {
    color: #999;
  }
  
  .register-footer {
    border-top-color: #333;
  }
  
  .register-footer p {
    color: #999;
  }
}
</style>
