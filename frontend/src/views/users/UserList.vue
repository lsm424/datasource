<template>
  <div class="page-container">
    <div class="page-header">
      <h1>用户管理</h1>
      <p>管理系统中的所有用户账户</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        
        <el-select
          v-model="filterRoleId"
          placeholder="角色筛选"
          clearable
          @change="handleFilter"
        >
          <el-option
            v-for="item in allRoles"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          clearable
          @change="handleFilter"
        >
          <el-option label="已激活" :value="true" />
          <el-option label="已禁用" :value="false" />
        </el-select>
      </div>

      <div class="toolbar-right">
        <el-button @click="refreshList" :loading="isLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加用户
        </el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card class="list-card">
      <el-table
        :data="paginatedUsers"
        v-loading="isLoading"
        stripe
        @sort-change="handleSort"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="expand-row">
                <span class="expand-label">用户ID：</span>
                <span>{{ row.id }}</span>
              </div>
              <div class="expand-row" v-if="row.phone">
                <span class="expand-label">手机号：</span>
                <span>{{ row.phone }}</span>
              </div>
              <div class="expand-row" v-if="row.company">
                <span class="expand-label">公司：</span>
                <span>{{ row.company }}</span>
              </div>
              <div class="expand-row" v-if="row.bio">
                <span class="expand-label">简介：</span>
                <span>{{ row.bio }}</span>
              </div>
              <div class="expand-row">
                <span class="expand-label">创建时间：</span>
                <span>{{ formatDate(row.createdAt) }}</span>
              </div>
              <div class="expand-row" v-if="row.lastLoginAt">
                <span class="expand-label">最后登录：</span>
                <span>{{ formatDate(row.lastLoginAt) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="username" label="用户名" sortable>
          <template #default="{ row }">
            <div class="user-info">
              <el-avatar :src="row.avatar" :size="32">
                {{ row.name?.charAt(0) }}
              </el-avatar>
              <div class="user-details">
                <div class="username">{{ row.username }}</div>
                <div class="name">{{ row.name }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱" width="200">
          <template #default="{ row }">
            <span>{{ row.email }}</span>
            <el-icon
              v-if="row.isVerified"
              class="verified-icon"
              title="邮箱已验证"
            >
              <CircleCheckFilled />
            </el-icon>
          </template>
        </el-table-column>

        <el-table-column prop="roleName" label="角色" width="140">
          <template #default="{ row }">
            <el-tag type="primary">
              {{ row.roleName || '未分配' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'danger'" size="small">
              {{ row.isActive ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="createdAt" label="创建时间" width="180" sortable>
          <template #default="{ row }">
            <span>{{ formatDate(row.createdAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                text 
                @click="editUser(row)"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              
              <el-button 
                text 
                :type="row.isActive ? 'warning' : 'success'"
                @click="toggleUserStatus(row)"
              >
                <el-icon v-if="row.isActive"><Lock /></el-icon>
                <el-icon v-else><Unlock /></el-icon>
                {{ row.isActive ? '禁用' : '启用' }}
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个用户吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="deleteUser(row)"
                v-if="row.id !== authStore.currentUser?.id"
              >
                <template #reference>
                  <el-button 
                    text 
                    type="danger"
                  >
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalCount"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handleCurrentPageChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑用户对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingUser ? '编辑用户' : '添加用户'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-position="top"
      >
        <div class="form-row">
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="userForm.username"
              placeholder="请输入用户名"
              :disabled="!!editingUser"
              clearable
            />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="userForm.email"
              placeholder="请输入邮箱地址"
              clearable
            />
          </el-form-item>
        </div>

        <el-form-item label="真实姓名" prop="name">
          <el-input
            v-model="userForm.name"
            placeholder="请输入真实姓名"
            clearable
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item label="手机号">
            <el-input
              v-model="userForm.phone"
              placeholder="请输入手机号（可选）"
              clearable
            />
          </el-form-item>

          <el-form-item label="公司">
            <el-input
              v-model="userForm.company"
              placeholder="请输入公司名称（可选）"
              clearable
            />
          </el-form-item>
        </div>

        <el-form-item label="系统角色（账号类型）" prop="role">
          <el-radio-group v-model="userForm.role">
            <el-radio label="user">普通用户</el-radio>
            <el-radio label="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数据访问角色" prop="roleId">
          <el-select v-model="userForm.roleId" placeholder="请选择数据访问角色">
            <el-option
              v-for="item in allRoles"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="!editingUser" label="密码" prop="password">
          <el-input
            v-model="userForm.password"
            type="password"
            placeholder="请输入初始密码"
            show-password
            clearable
          />
          <div class="password-hint">
            密码要求：至少8位，包含大写字母、小写字母和数字
          </div>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="userForm.isActive">
            账户激活状态
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser" :loading="isSaving">
          {{ editingUser ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Plus,
  CircleCheckFilled,
  Edit,
  Lock,
  Unlock,
  Delete
} from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import type { User, UserRole } from '@/types/auth'
import { roleApi, type Role } from '@/api/roles'

const authStore = useAuthStore()

// 导入用户API
import { userApi } from '@/api/users'

// 表单引用
const userFormRef = ref<FormInstance>()

// 响应式数据
const users = ref<User[]>([])
const totalCount = ref(0)
const isLoading = ref(false)
const isSaving = ref(false)
const searchQuery = ref('')
const filterRole = ref<UserRole | ''>('') // 仍保留按系统角色过滤
const filterRoleId = ref<string | ''>('') // 按数据访问角色过滤
const filterStatus = ref<boolean | ''>('')
const currentPage = ref(1)
const pageSize = ref(20)
const sortField = ref('')
const sortOrder = ref('')
const showCreateDialog = ref(false)
const editingUser = ref<User | null>(null)

// 角色列表（数据访问角色）
const allRoles = ref<Role[]>([])

// 表单数据
const userForm = reactive({
  username: '',
  email: '',
  name: '',
  phone: '',
  company: '',
  bio: '',
  role: 'user' as UserRole,
  password: '',
  isActive: true,
  roleId: '' as string
})

// 验证规则
const userRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度应在 3 到 50 个字符之间', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) return callback()
        if (!/[A-Z]/.test(value)) {
          return callback(new Error('密码必须包含至少一个大写字母'))
        }
        if (!/[a-z]/.test(value)) {
          return callback(new Error('密码必须包含至少一个小写字母'))
        }
        if (!/\d/.test(value)) {
          return callback(new Error('密码必须包含至少一个数字'))
        }
        callback()
      }, 
      trigger: 'blur' 
    }
  ],
  role: [
    { required: true, message: '请选择系统角色', trigger: 'change' }
  ],
  roleId: [
    { required: true, message: '请选择数据访问角色', trigger: 'change' }
  ]
}

// 计算属性
const paginatedUsers = computed(() => {
  // 现在由服务器端处理分页和过滤，直接返回当前的用户列表
  return users.value
})

// 方法
const refreshList = async () => {
  isLoading.value = true
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      search: searchQuery.value || undefined,
      role: filterRole.value || undefined,
      role_id: filterRoleId.value || undefined,
      is_active: filterStatus.value !== '' ? filterStatus.value : undefined
    }
    
    const response = await userApi.getUsers(params)
    
    // 处理响应数据
    if (Array.isArray(response)) {
      users.value = response
      totalCount.value = response.length
    } else if (response && response.data) {
      users.value = response.data
      totalCount.value = response.total || 0
    }
  } catch (error: any) {
    console.error('获取用户列表失败:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    isLoading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  refreshList()
}

const handleFilter = () => {
  currentPage.value = 1
  refreshList()
}

const handleSort = ({ prop, order }: { prop: string; order: string }) => {
  sortField.value = prop
  sortOrder.value = order
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  refreshList()
}

const handleCurrentPageChange = (page: number) => {
  currentPage.value = page
  refreshList()
}

const editUser = (user: User) => {
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username,
    email: user.email,
    name: user.name,
    phone: user.phone || '',
    company: user.company || '',
    bio: user.bio || '',
    role: user.role,
    password: '',
    isActive: user.isActive,
    roleId: (user as any).roleId || ''
  })
  showCreateDialog.value = true
}

const toggleUserStatus = async (user: User) => {
  const action = user.isActive ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户 "${user.name}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
        // 调用API更新用户状态  
        await userApi.updateUser(user.id, { is_active: !user.isActive })
    ElMessage.success(`用户${action}成功`)
    // 刷新列表
    await refreshList()
  } catch (error) {
    // 用户取消或API错误
    if (error !== 'cancel') {
      ElMessage.error(`${action}用户失败`)
    }
  }
}

const deleteUser = async (user: User) => {
  try {
    await userApi.deleteUser(user.id)
    ElMessage.success('用户删除成功')
    // 刷新列表
    await refreshList()
  } catch (error: any) {
    ElMessage.error(`删除用户失败：${error.message}`)
  }
}

const saveUser = async () => {
  if (!userFormRef.value) return
  
  await userFormRef.value.validate(async (valid) => {
    if (valid) {
      isSaving.value = true
      try {
        if (editingUser.value) {
          // 更新用户
          await userApi.updateUser(editingUser.value.id, userForm)
          ElMessage.success('用户更新成功')
        } else {
          // 创建新用户
          await userApi.createUser(userForm)
          ElMessage.success('用户创建成功')
        }
        
        showCreateDialog.value = false
        resetForm()
        // 刷新列表
        await refreshList()
      } catch (error: any) {
        ElMessage.error(`操作失败：${error.message}`)
      } finally {
        isSaving.value = false
      }
    }
  })
}

const resetForm = () => {
  editingUser.value = null
  Object.assign(userForm, {
    username: '',
    email: '',
    name: '',
    phone: '',
    company: '',
    bio: '',
    role: 'user' as UserRole,
    password: '',
    isActive: true,
    roleId: ''
  })
  userFormRef.value?.clearValidate()
}

// 辅助函数
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 生命周期
onMounted(async () => {
  // 先加载角色列表
  try {
    const res = await roleApi.getRoles()
    const list = Array.isArray(res.data) ? res.data : res.data?.data || res.data || []
    allRoles.value = list
  } catch (error) {
    console.error('获取角色列表失败:', error)
  }
  await refreshList()
})

// 页面标题
document.title = '用户管理 - 数据浏览系统'
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

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.search-input {
  max-width: 300px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
}

.password-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.list-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.expand-content {
  padding: 16px 24px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  margin: 8px;
}

.expand-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.expand-row:last-child {
  margin-bottom: 0;
}

.expand-label {
  font-weight: 500;
  min-width: 80px;
  color: var(--el-text-color-regular);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-details {
  flex: 1;
}

.username {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.name {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.verified-icon {
  color: var(--el-color-success);
  margin-left: 4px;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-left {
    flex-wrap: wrap;
  }
  
  .toolbar-right {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
  
  .search-input {
    max-width: none;
    flex: 1;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 2px;
  }
  
  .action-buttons .el-button {
    justify-content: flex-start;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
