<template>
  <div class="page-container">
    <div class="page-header">
      <h1>个人中心</h1>
      <p>管理您的个人信息和账户设置</p>
    </div>

    <div class="profile-content">
      <!-- 个人信息卡片 -->
      <el-card class="profile-card">
        <template #header>
          <div class="card-header">
            <span>个人信息</span>
            <el-button text @click="editMode = !editMode">
              <el-icon><Edit /></el-icon>
              {{ editMode ? '取消编辑' : '编辑信息' }}
            </el-button>
          </div>
        </template>

        <div class="profile-form">
          <div class="avatar-section">
            <el-avatar :src="profileForm.avatar" :size="80">
              {{ profileForm.name?.charAt(0) }}
            </el-avatar>
            <div class="avatar-actions" v-if="editMode">
              <el-button size="small" @click="changeAvatar">
                <el-icon><Camera /></el-icon>
                更换头像
              </el-button>
            </div>
          </div>

          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-position="top"
            :disabled="!editMode"
          >
            <div class="form-row">
              <el-form-item label="用户名">
                <el-input v-model="profileForm.username" disabled />
              </el-form-item>

              <el-form-item label="邮箱地址" prop="email">
                <el-input
                  v-model="profileForm.email"
                  placeholder="请输入邮箱地址"
                />
                <div class="form-tip" v-if="!profileForm.isVerified">
                  <el-icon><Warning /></el-icon>
                  邮箱未验证
                  <el-button text type="primary" @click="sendVerificationEmail">
                    发送验证邮件
                  </el-button>
                </div>
              </el-form-item>
            </div>

            <div class="form-row">
              <el-form-item label="真实姓名" prop="name">
                <el-input
                  v-model="profileForm.name"
                  placeholder="请输入真实姓名"
                />
              </el-form-item>

              <el-form-item label="手机号码">
                <el-input
                  v-model="profileForm.phone"
                  placeholder="请输入手机号码"
                />
              </el-form-item>
            </div>

            <el-form-item label="公司/组织">
              <el-input
                v-model="profileForm.company"
                placeholder="请输入公司或组织名称"
              />
            </el-form-item>

            <el-form-item label="个人简介">
              <el-input
                v-model="profileForm.bio"
                type="textarea"
                placeholder="简单介绍一下自己"
                :rows="3"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>

            <el-form-item v-if="editMode">
              <el-button type="primary" @click="saveProfile" :loading="isSaving">
                保存更改
              </el-button>
              <el-button @click="resetForm">
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-card>

      <!-- 安全设置卡片 -->
      <el-card class="security-card">
        <template #header>
          <div class="card-header">
            <span>安全设置</span>
          </div>
        </template>

        <div class="security-items">
          <div class="security-item">
            <div class="security-info">
              <h4>登录密码</h4>
              <p>定期更换密码可以提高账户安全性</p>
            </div>
            <el-button @click="showPasswordDialog = true">
              修改密码
            </el-button>
          </div>

          <div class="security-item">
            <div class="security-info">
              <h4>登录设备</h4>
              <p>管理已登录的设备，及时清理可疑登录</p>
            </div>
            <el-button @click="showDevicesDialog = true">
              查看设备
            </el-button>
          </div>

          <div class="security-item">
            <div class="security-info">
              <h4>操作日志</h4>
              <p>查看账户的重要操作记录</p>
            </div>
            <el-button @click="showLogsDialog = true">
              查看日志
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 账户统计卡片 -->
      <el-card class="stats-card">
        <template #header>
          <div class="card-header">
            <span>账户统计</span>
          </div>
        </template>

        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">{{ stats.loginCount }}</div>
            <div class="stat-label">总登录次数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ stats.dataSourceAccess }}</div>
            <div class="stat-label">访问数据源</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ formatDate(authStore.currentUser?.createdAt) }}</div>
            <div class="stat-label">注册时间</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ formatDate(authStore.currentUser?.lastLoginAt) }}</div>
            <div class="stat-label">最后登录</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="500px">
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
      >
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input
            v-model="passwordForm.currentPassword"
            type="password"
            placeholder="请输入当前密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="changePassword" :loading="isChangingPassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 登录设备对话框 -->
    <el-dialog v-model="showDevicesDialog" title="登录设备" width="700px">
      <el-table :data="loginDevices" stripe>
        <el-table-column prop="device" label="设备" width="150">
          <template #default="{ row }">
            <el-icon class="device-icon">
              <Monitor v-if="row.type === 'desktop'" />
              <Cellphone v-else />
            </el-icon>
            {{ row.device }}
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" width="120" />
        <el-table-column prop="ip" label="IP地址" width="130" />
        <el-table-column prop="loginTime" label="登录时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.loginTime) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.current ? 'success' : 'info'" size="small">
              {{ row.current ? '当前' : '历史' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="!row.current"
              text
              type="danger"
              size="small"
              @click="revokeDevice(row)"
            >
              撤销
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 操作日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="操作日志" width="800px">
      <el-table :data="operationLogs" stripe>
        <el-table-column prop="action" label="操作" width="120" />
        <el-table-column prop="resource" label="资源" width="150" />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
              {{ row.result === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="130" />
        <el-table-column prop="userAgent" label="用户代理" show-overflow-tooltip />
        <el-table-column prop="timestamp" label="时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.timestamp) }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 上传头像 -->
    <input
      ref="avatarInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleAvatarChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Edit,
  Camera,
  Warning,
  Monitor,
  Cellphone
} from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/auth'

const authStore = useAuthStore()

// 表单引用
const profileFormRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()
const avatarInput = ref<HTMLInputElement>()

// 响应式数据
const editMode = ref(false)
const isSaving = ref(false)
const isChangingPassword = ref(false)
const showPasswordDialog = ref(false)
const showDevicesDialog = ref(false)
const showLogsDialog = ref(false)

// 表单数据
const profileForm = reactive({
  username: '',
  email: '',
  name: '',
  phone: '',
  company: '',
  bio: '',
  avatar: '',
  isVerified: false
})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 统计数据
const stats = reactive({
  loginCount: 156,
  dataSourceAccess: 12,
  lastLogin: new Date().toISOString()
})

// 模拟数据
const loginDevices = ref([
  {
    id: '1',
    device: 'Chrome 浏览器',
    type: 'desktop',
    location: '北京',
    ip: '192.168.1.100',
    loginTime: new Date().toISOString(),
    current: true
  },
  {
    id: '2',
    device: 'Safari 浏览器',
    type: 'mobile',
    location: '上海',
    ip: '192.168.1.101',
    loginTime: new Date(Date.now() - 86400000).toISOString(),
    current: false
  }
])

const operationLogs = ref([
  {
    id: '1',
    action: '登录系统',
    resource: '用户账户',
    result: 'success',
    ip: '192.168.1.100',
    userAgent: 'Chrome/120.0.0.0',
    timestamp: new Date().toISOString()
  },
  {
    id: '2',
    action: '访问数据源',
    resource: '文件系统-Demo',
    result: 'success',
    ip: '192.168.1.100',
    userAgent: 'Chrome/120.0.0.0',
    timestamp: new Date(Date.now() - 3600000).toISOString()
  }
])

// 验证规则
const profileRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ]
}

const passwordRules: FormRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 方法
const loadProfile = () => {
  const user = authStore.currentUser
  if (user) {
    Object.assign(profileForm, {
      username: user.username,
      email: user.email,
      name: user.name,
      phone: user.phone || '',
      company: user.company || '',
      bio: user.bio || '',
      avatar: user.avatar || '',
      isVerified: user.isVerified
    })
  }
}

const saveProfile = async () => {
  if (!profileFormRef.value) return
  
  await profileFormRef.value.validate(async (valid) => {
    if (valid) {
      isSaving.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // 更新store中的用户信息
        authStore.updateUser({
          email: profileForm.email,
          name: profileForm.name,
          phone: profileForm.phone,
          company: profileForm.company,
          bio: profileForm.bio,
          avatar: profileForm.avatar
        })
        
        ElMessage.success('个人信息更新成功')
        editMode.value = false
      } catch (error: any) {
        ElMessage.error(`更新失败：${error.message}`)
      } finally {
        isSaving.value = false
      }
    }
  })
}

const resetForm = () => {
  loadProfile()
}

const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      isChangingPassword.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        ElMessage.success('密码修改成功')
        showPasswordDialog.value = false
        Object.assign(passwordForm, {
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        })
      } catch (error: any) {
        ElMessage.error(`密码修改失败：${error.message}`)
      } finally {
        isChangingPassword.value = false
      }
    }
  })
}

const changeAvatar = () => {
  avatarInput.value?.click()
}

const handleAvatarChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (file) {
    // 这里应该上传到服务器，现在只是预览
    const reader = new FileReader()
    reader.onload = (e) => {
      profileForm.avatar = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

const sendVerificationEmail = async () => {
  try {
    // 模拟发送验证邮件
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('验证邮件已发送，请查收')
  } catch (error: any) {
    ElMessage.error(`发送失败：${error.message}`)
  }
}

const revokeDevice = async (device: any) => {
  try {
    // 模拟撤销设备
    await new Promise(resolve => setTimeout(resolve, 500))
    const index = loginDevices.value.findIndex(d => d.id === device.id)
    if (index !== -1) {
      loginDevices.value.splice(index, 1)
    }
    ElMessage.success('设备已撤销')
  } catch (error: any) {
    ElMessage.error(`撤销失败：${error.message}`)
  }
}

// 辅助函数
const formatDate = (dateString?: string): string => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  loadProfile()
})

// 页面标题
document.title = '个人中心 - 数据浏览系统'
</script>

<style scoped>
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}

.page-header p {
  color: var(--el-text-color-regular);
  margin: 0;
}

.profile-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  max-width: 1200px;
}

.profile-card,
.security-card,
.stats-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  height: fit-content;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.profile-form {
  padding: 24px 0;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-color-warning);
  margin-top: 4px;
}

.security-items {
  padding: 16px 0;
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.security-item:last-child {
  border-bottom: none;
}

.security-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.security-info p {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px 0;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.device-icon {
  margin-right: 4px;
  color: var(--el-text-color-secondary);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .profile-content {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
  
  .avatar-section {
    flex-direction: column;
    text-align: center;
  }
  
  .security-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
