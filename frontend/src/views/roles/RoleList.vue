<template>
  <div class="page-container">
    <div class="page-header">
      <h1>角色管理</h1>
      <p>配置不同角色可访问的数据集</p>
    </div>

    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索角色..."
          clearable
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="toolbar-right">
        <el-button @click="refreshList" :loading="isLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增角色
        </el-button>
      </div>
    </div>

    <el-card class="list-card">
      <el-table :data="filteredRoles" v-loading="isLoading" stripe>
        <el-table-column prop="name" label="角色名称" />
        <el-table-column prop="code" label="编码" width="160" />
        <el-table-column label="内置" width="80">
          <template #default="{ row }">
            <el-tag :type="row.builtIn ? 'info' : 'success'" size="small">
              {{ row.builtIn ? '内置' : '自定义' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button text @click="editRole(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button text @click="editRoleDatasets(row)">
                <el-icon><Collection /></el-icon>
                数据权限
              </el-button>
              <el-popconfirm
                v-if="row.code !== 'admin' && !row.builtIn"
                title="确定要删除该角色吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="deleteRole(row)"
              >
                <template #reference>
                  <el-button text type="danger">
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑角色对话框 -->
    <el-dialog v-model="showEditDialog" :title="editingRole ? '编辑角色' : '新增角色'" width="500px">
      <el-form :model="roleForm" :rules="roleRules" ref="roleFormRef" label-position="top">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code" v-if="!editingRole || !editingRole.builtIn">
          <el-input
            v-model="roleForm.code"
            placeholder="仅限字母、数字、下划线"
            :disabled="!!editingRole"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="roleForm.description"
            type="textarea"
            rows="3"
            placeholder="请输入角色描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRole" :loading="savingRole">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 配置数据权限对话框 -->
    <el-dialog
      v-model="showDatasetsDialog"
      :title="`配置角色数据权限 - ${currentRole?.name || ''}`"
      width="600px"
    >
      <el-alert
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 12px"
        title="仅对非管理员用户生效；管理员始终拥有所有数据源访问权限。"
      />
      <el-checkbox-group
        v-model="selectedDatasetIds"
        class="dataset-list"
        :disabled="currentRole?.code === 'admin'"
      >
        <el-checkbox
          v-for="ds in allDatasources"
          :key="ds.id"
          :label="ds.id"
        >
          {{ ds.cname || ds.name }}（{{ ds.type }}）
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="showDatasetsDialog = false">关闭</el-button>
        <el-button
          v-if="currentRole?.code !== 'admin'"
          type="primary"
          @click="saveRoleDatasets"
          :loading="savingDatasets"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Refresh, Plus, Edit, Delete, Collection } from '@element-plus/icons-vue'

import { roleApi, type Role } from '@/api/roles'
import { useDataSourceStore } from '@/stores/datasource'

const dataSourceStore = useDataSourceStore()

const roles = ref<Role[]>([])
const isLoading = ref(false)
const savingRole = ref(false)
const savingDatasets = ref(false)
const searchQuery = ref('')

const showEditDialog = ref(false)
const showDatasetsDialog = ref(false)
const editingRole = ref<Role | null>(null)
const currentRole = ref<Role | null>(null)
const selectedDatasetIds = ref<string[]>([])

const roleFormRef = ref<FormInstance>()
const roleForm = reactive({
  name: '',
  code: '',
  description: ''
})

const roleRules: FormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_]+$/,
      message: '角色编码仅支持字母、数字和下划线',
      trigger: 'blur'
    }
  ]
}

const filteredRoles = computed(() => {
  if (!searchQuery.value) return roles.value
  const q = searchQuery.value.toLowerCase()
  return roles.value.filter(
    r =>
      r.name.toLowerCase().includes(q) ||
      r.code.toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q)
  )
})

const allDatasources = computed(() => dataSourceStore.dataSources || [])

const refreshList = async () => {
  isLoading.value = true
  try {
    const res = await roleApi.getRoles()
    const list = Array.isArray(res.data) ? res.data : res.data?.data || res.data || []
    roles.value = list
  } catch (err: any) {
    console.error('获取角色列表失败', err)
    ElMessage.error('获取角色列表失败')
  } finally {
    isLoading.value = false
  }
}

const handleSearch = () => {
  // 只修改计算属性，无需重新拉取
}

const openCreateDialog = () => {
  editingRole.value = null
  roleForm.name = ''
  roleForm.code = ''
  roleForm.description = ''
  showEditDialog.value = true
}

const editRole = (role: Role) => {
  editingRole.value = role
  roleForm.name = role.name
  roleForm.code = role.code
  roleForm.description = role.description || ''
  showEditDialog.value = true
}

const saveRole = async () => {
  if (!roleFormRef.value) return
  await roleFormRef.value.validate(async valid => {
    if (!valid) return
    savingRole.value = true
    try {
      if (editingRole.value) {
        await roleApi.updateRole(editingRole.value.id, {
          name: roleForm.name,
          description: roleForm.description || undefined
        })
        ElMessage.success('角色更新成功')
      } else {
        await roleApi.createRole({
          name: roleForm.name,
          code: roleForm.code,
          description: roleForm.description || undefined
        })
        ElMessage.success('角色创建成功')
      }
      showEditDialog.value = false
      await refreshList()
    } catch (err: any) {
      ElMessage.error(`保存角色失败：${err.message || '未知错误'}`)
    } finally {
      savingRole.value = false
    }
  })
}

const deleteRole = async (role: Role) => {
  try {
    await roleApi.deleteRole(role.id)
    ElMessage.success('角色删除成功')
    await refreshList()
  } catch (err: any) {
    ElMessage.error(`删除角色失败：${err.message || '未知错误'}`)
  }
}

const editRoleDatasets = async (role: Role) => {
  currentRole.value = role
  selectedDatasetIds.value = []
  showDatasetsDialog.value = true
  try {
    // 确保已有数据源列表
    if (!allDatasources.value.length) {
      await dataSourceStore.fetchDataSources({ page: 1, limit: 1000 })
    }

    // 管理员角色：固定拥有全部数据源访问权限，直接全部勾选（不依赖后端绑定记录）
    if (role.code === 'admin') {
      selectedDatasetIds.value = allDatasources.value.map((ds: any) => ds.id)
      return
    }

    const res = await roleApi.getRoleDatasets(role.id)
    // request.ts 已经解包 DataResponse，这里直接就是 RoleWithDatasets
    const data: any = res
    selectedDatasetIds.value = data?.datasetIds || data?.dataset_ids || []
  } catch (err: any) {
    console.error('获取角色数据权限失败', err)
    ElMessage.error('获取角色数据权限失败')
  }
}

const saveRoleDatasets = async () => {
  if (!currentRole.value) return
  savingDatasets.value = true
  try {
    await roleApi.updateRoleDatasets(currentRole.value.id, selectedDatasetIds.value)
    ElMessage.success('数据权限保存成功')
    showDatasetsDialog.value = false
  } catch (err: any) {
    ElMessage.error(`保存数据权限失败：${err.message || '未知错误'}`)
  } finally {
    savingDatasets.value = false
  }
}

const formatDate = (str: string) => {
  return new Date(str).toLocaleString('zh-CN')
}

onMounted(async () => {
  await refreshList()
  if (!allDatasources.value.length) {
    try {
      await dataSourceStore.fetchDataSources({ page: 1, limit: 1000 })
    } catch (err) {
      console.error('获取数据源列表失败', err)
    }
  }
  document.title = '角色管理 - 数据浏览系统'
})
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
  margin: 0 0 8px 0;
}

.page-header p {
  margin: 0;
  color: var(--el-text-color-regular);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.search-input {
  max-width: 260px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.list-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 380px;
  overflow-y: auto;
}
</style>

