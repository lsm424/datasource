<template>
  <div class="page-container">
    <div class="page-header">
      <h1>数据源管理</h1>
      <p>管理系统中的所有数据源配置</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索数据源..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        
        <el-select
          v-model="filterType"
          placeholder="类型筛选"
          clearable
          @change="handleFilter"
        >
          <el-option label="文件系统" value="filesystem" />
          <el-option label="数据库" value="database" />
          <el-option label="对象存储" value="object_storage" />
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
        <el-button @click="refreshList" :loading="dataSourceStore.isLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        
        <el-button 
          type="primary" 
          @click="$router.push('/datasources/create')"
          v-if="authStore.isAdmin"
        >
          <el-icon><Plus /></el-icon>
          添加数据源
        </el-button>
      </div>
    </div>

    <!-- 数据源列表 -->
    <el-card class="list-card">
      <el-table
        :data="paginatedDataSources"
        v-loading="dataSourceStore.isLoading"
        stripe
        @sort-change="handleSort"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="expand-row">
                <span class="expand-label">描述：</span>
                <span>{{ row.desc || '暂无描述' }}</span>
              </div>
              <div class="expand-row">
                <span class="expand-label">创建时间：</span>
                <span>{{ formatDate(row.createdAt) }}</span>
              </div>
              <div class="expand-row">
                <span class="expand-label">更新时间：</span>
                <span>{{ formatDate(row.updatedAt) }}</span>
              </div>
              <div class="expand-row" v-if="row.lastTestAt">
                <span class="expand-label">最后测试：</span>
                <span>{{ formatDate(row.lastTestAt) }}</span>
              </div>
              <div class="expand-row" v-if="row.tags?.length">
                <span class="expand-label">标签：</span>
                <div class="tag-list">
                  <el-tag
                    v-for="tag in row.tags"
                    :key="tag"
                    size="small"
                    style="margin-right: 4px;"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="名称" sortable>
          <template #default="{ row }">
            <div class="datasource-name">
              <el-icon class="datasource-icon">
                <Folder v-if="row.type === 'filesystem'" />
                <Coin v-else-if="row.type === 'database'" />
                <Box v-else />
              </el-icon>
              <div>
                <div class="name-primary">{{ row.cname || row.name }}</div>
                <div class="name-secondary" v-if="row.cname">{{ row.name }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">
              {{ getTypeDisplayName(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="company" label="单位" width="150">
          <template #default="{ row }">
            <span>{{ row.company || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="num" label="项目数" width="100" sortable>
          <template #default="{ row }">
            <span>{{ formatNumber(row.num) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="size" label="数据量" width="120" sortable>
          <template #default="{ row }">
            <span>{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <div class="status-column">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '激活' : '禁用' }}
              </el-tag>
              <el-tooltip
                v-if="row.is_connected !== undefined"
                :content="row.is_connected ? '连接正常' : '连接异常'"
                placement="top"
              >
                <el-icon 
                  :class="[
                    'connection-icon',
                    row.is_connected ? 'connected' : 'disconnected'
                  ]"
                >
                  <Connection />
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                text 
                type="primary" 
                @click="browseDataSource(row)"
              >
                <el-icon><View /></el-icon>
                浏览
              </el-button>
              
              <el-button 
                text 
                type="primary" 
                @click="testConnection(row)"
                :loading="testingConnections[row.id]"
                v-if="authStore.isAdmin"
              >
                <el-icon><Link /></el-icon>
                测试
              </el-button>
              
              <el-button 
                text 
                @click="editDataSource(row)"
                v-if="authStore.isAdmin"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个数据源吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="deleteDataSource(row)"
                v-if="authStore.isAdmin"
              >
                <template #reference>
                  <el-button 
                    text 
                    type="danger"
                    :loading="dataSourceStore.isDeleting"
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
          :total="filteredDataSources.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handleCurrentPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Plus,
  Folder,
  Coin,
  Box,
  Connection,
  View,
  Link,
  Edit,
  Delete
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'
import type { DataSource, DataSourceType } from '@/types/datasource'

const router = useRouter()
const authStore = useAuthStore()
const dataSourceStore = useDataSourceStore()

// 响应式数据
const searchQuery = ref('')
const filterType = ref<DataSourceType | ''>('')
const filterStatus = ref<boolean | ''>('')
const currentPage = ref(1)
const pageSize = ref(20)
const sortField = ref('')
const sortOrder = ref('')
const testingConnections = ref<Record<string, boolean>>({})

// 计算属性
const filteredDataSources = computed(() => {
  let result = dataSourceStore.dataSources.slice()
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(ds => 
      ds.name.toLowerCase().includes(query) ||
      ds.cname.toLowerCase().includes(query) ||
      ds.company?.toLowerCase().includes(query) ||
      ds.desc?.toLowerCase().includes(query)
    )
  }
  
  // 类型过滤
  if (filterType.value) {
    result = result.filter(ds => ds.type === filterType.value)
  }
  
  // 状态过滤
  if (filterStatus.value !== '') {
    result = result.filter(ds => ds.is_active === filterStatus.value)
  }
  
  // 排序
  if (sortField.value) {
    result.sort((a, b) => {
      const aVal = a[sortField.value as keyof DataSource]
      const bVal = b[sortField.value as keyof DataSource]
      
      if (sortOrder.value === 'descending') {
        return aVal > bVal ? -1 : 1
      } else {
        return aVal > bVal ? 1 : -1
      }
    })
  }
  
  return result
})

const paginatedDataSources = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredDataSources.value.slice(start, end)
})

// 方法
const refreshList = async () => {
  try {
    console.log('🔄 DataSourceList: 开始刷新数据源列表')
    await dataSourceStore.fetchDataSources()
    console.log('✅ DataSourceList: 数据源列表刷新完成，当前有', dataSourceStore.dataSources.length, '个数据源')
    console.log('📋 DataSourceList: 数据源详情', dataSourceStore.dataSources)
  } catch (error) {
    console.error('❌ DataSourceList: 刷新数据源列表失败', error)
    ElMessage.error('刷新数据源列表失败')
  }
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

const handleSort = ({ prop, order }: { prop: string; order: string }) => {
  sortField.value = prop
  sortOrder.value = order
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentPageChange = (page: number) => {
  currentPage.value = page
}

const browseDataSource = (datasource: DataSource) => {
  router.push(`/browse/${datasource.type}/${datasource.id}`)
}

const editDataSource = (datasource: DataSource) => {
  router.push(`/datasources/${datasource.id}/edit`)
}

const testConnection = async (datasource: DataSource) => {
  testingConnections.value[datasource.id] = true
  
  try {
    const result = await dataSourceStore.testConnection(datasource.config)
    if (result.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(`连接测试失败：${result.message}`)
    }
  } catch (error: any) {
    ElMessage.error(`连接测试失败：${error.message}`)
  } finally {
    testingConnections.value[datasource.id] = false
  }
}

const deleteDataSource = async (datasource: DataSource) => {
  try {
    await dataSourceStore.deleteDataSource(datasource.id)
    ElMessage.success('数据源删除成功')
  } catch (error: any) {
    ElMessage.error(`删除数据源失败：${error.message}`)
  }
}

// 辅助函数
const getTypeDisplayName = (type: string): string => {
  const typeMap: Record<string, string> = {
    filesystem: '文件系统',
    database: '数据库',
    object_storage: '对象存储'
  }
  return typeMap[type] || type
}

const getTypeTagType = (type: string): string => {
  const typeMap: Record<string, string> = {
    filesystem: 'primary',
    database: 'success',
    object_storage: 'warning'
  }
  return typeMap[type] || ''
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 生命周期
onMounted(async () => {
  await refreshList()
})

// 页面标题
document.title = '数据源管理 - 数据浏览系统'
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.datasource-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.datasource-icon {
  color: var(--el-color-primary);
}

.name-primary {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.name-secondary {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status-column {
  display: flex;
  align-items: center;
  gap: 8px;
}

.connection-icon {
  font-size: 14px;
  cursor: help;
}

.connection-icon.connected {
  color: var(--el-color-success);
}

.connection-icon.disconnected {
  color: var(--el-color-danger);
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
}
</style>
