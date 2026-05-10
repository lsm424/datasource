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
                <Folder v-if="row?.type === 'filesystem'" />
                <Coin v-else-if="row?.type === 'database'" />
                <Box v-else />
              </el-icon>
              <div>
                <div class="name-primary">{{ row?.cname || row?.name || '未知数据源' }}</div>
                <div class="name-secondary" v-if="row?.cname">{{ row?.name }}</div>
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

        <el-table-column label="操作" width="160" fixed="right">
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
              
              <!-- 管理员操作下拉菜单 -->
              <el-dropdown 
                v-if="authStore.isAdmin"
                @command="(command: string) => handleAdminAction(command, row)"
                placement="bottom-end"
              >
                <el-button 
                  text 
                  type="info"
                  :loading="testingConnections[row.id] || dataSourceStore.isDeleting"
                >
                  <el-icon><MoreFilled /></el-icon>
                  更多
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit" icon="Edit">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="test" icon="Link" :disabled="testingConnections[row.id]">
                      {{ testingConnections[row.id] ? '测试中...' : '测试连接' }}
                    </el-dropdown-item>
                    <el-dropdown-item command="stats" icon="DataAnalysis" :disabled="runningStats[row.id]">
                      {{ runningStats[row.id] ? '统计中...' : '统计' }}
                    </el-dropdown-item>
                    <el-dropdown-item 
                      command="delete" 
                      icon="Delete"
                      :disabled="dataSourceStore.isDeleting"
                      divided
                    >
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
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
  MoreFilled,
  DataAnalysis
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'
import { dataSourceApi } from '@/api/datasource'
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
const runningStats = ref<Record<string, boolean>>({})
const totalCount = ref(0)

// 计算属性 - 直接使用store中的数据，因为后端已经处理了分页和过滤
const filteredDataSources = computed(() => {
  return dataSourceStore.dataSources.filter(ds => ds != null)
})

const paginatedDataSources = computed(() => {
  return filteredDataSources.value
})

// 方法
const refreshList = async () => {
  try {
    
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      type: filterType.value || undefined,
      is_active: filterStatus.value !== '' ? filterStatus.value : undefined,
      search: searchQuery.value || undefined
    }
    
    const response = await dataSourceStore.fetchDataSources(params)
    
    // 提取分页信息
    if (response && typeof response === 'object') {
      if ('total' in response) {
        totalCount.value = response.total
      }
    }
    
  } catch (error) {
    console.error('❌ DataSourceList: 刷新数据源列表失败', error)
    ElMessage.error('刷新数据源列表失败')
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

const browseDataSource = (datasource: DataSource) => {
  router.push(`/browse/${datasource.type}/${datasource.id}`)
}

const editDataSource = (datasource: DataSource) => {
  router.push(`/datasources/${datasource.id}/edit`)
}

const testConnection = async (datasource: DataSource) => {
  testingConnections.value[datasource.id] = true

  try {
    // 先获取数据源的完整详情（包含config配置）
    // 响应拦截器已经提取了 data.data，所以 fullDataSource 直接是数据源对象
    const fullDataSource = await dataSourceApi.getDataSourceById(datasource.id)

    const result = await dataSourceStore.testConnection({
      type: fullDataSource.type,
      config: fullDataSource.config
    })
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

const runDataSourceStats = async (datasource: DataSource) => {
  if (!datasource.is_active) {
    ElMessage.warning('数据源未激活，无法执行统计')
    return
  }

  runningStats.value[datasource.id] = true
  
  try {
    const response = await dataSourceStore.runDataSourceStats(datasource.id)
    if (response.data) {
      ElMessage.success(`数据源 ${datasource.name} 的统计任务已启动，请稍后查看结果`)
      
      // 2秒后自动刷新数据源列表以显示更新的统计信息
      setTimeout(async () => {
        await refreshList()
        
        // 显示统计完成通知，并提供查看选项
        ElMessageBox.confirm(
          `数据源 ${datasource.name} 的统计已完成。\n\n您可以：\n• 查看详细统计信息\n• 前往仪表盘查看总览数据（建议点击仪表盘的刷新按钮）`,
          '统计完成',
          {
            confirmButtonText: '查看统计详情',
            cancelButtonText: '前往仪表盘',
            type: 'success',
          }
        ).then(() => {
          // 用户选择查看统计详情
          showStatsHistory(datasource)
        }).catch(() => {
          // 用户选择前往仪表盘
          router.push('/dashboard')
        })
      }, 2000)
    }
  } catch (error: any) {
    ElMessage.error(`启动统计任务失败：${error.message}`)
  } finally {
    runningStats.value[datasource.id] = false
  }
}

const showStatsHistory = async (datasource: DataSource) => {
  try {
    const response = await dataSourceStore.getDataSourceStats(datasource.id, 10)
    if (response.data) {
      const statsData = response.data
      
      let historyText = `数据源：${statsData.datasource_name}\n\n`
      
      if (statsData.current_stats) {
        const stats = statsData.current_stats
        historyText += `当前统计信息：\n`
        historyText += `- 记录数：${formatNumber(stats.record_count)}\n`
        historyText += `- 数据大小：${formatFileSize(stats.data_size)}\n`
        historyText += `- 文件数：${formatNumber(stats.file_count)}\n`
        historyText += `- 最后更新：${new Date(stats.last_updated).toLocaleString()}\n`
        historyText += `- 状态：${stats.status === 'completed' ? '成功' : stats.status === 'failed' ? '失败' : '进行中'}\n\n`
      } else {
        historyText += `暂无统计信息\n\n`
      }
      
      if (statsData.history && statsData.history.length > 0) {
        historyText += `统计历史（最近${statsData.history.length}条）：\n`
        statsData.history.forEach((record, index) => {
          historyText += `${index + 1}. ${new Date(record.stats_date).toLocaleDateString()}\n`
          historyText += `   记录数：${formatNumber(record.record_count)}, 大小：${formatFileSize(record.data_size)}, 状态：${record.status === 'completed' ? '成功' : '失败'}\n`
          if (record.error_message) {
            historyText += `   错误：${record.error_message}\n`
          }
        })
      }
      
      ElMessageBox.alert(historyText, `统计信息 - ${statsData.datasource_name}`, {
        confirmButtonText: '确定',
        type: 'info'
      })
    }
  } catch (error: any) {
    ElMessage.error(`获取统计信息失败：${error.message}`)
  }
}

// 处理管理员操作下拉菜单
const handleAdminAction = async (command: string, row: DataSource) => {
  switch (command) {
    case 'edit':
      editDataSource(row)
      break
    
    case 'test':
      if (!testingConnections.value[row.id]) {
        await testConnection(row)
      }
      break

    case 'stats':
      if (!runningStats.value[row.id]) {
        await runDataSourceStats(row)
      }
      break
    
    case 'delete':
      // 显示确认对话框
      try {
        await ElMessageBox.confirm(
          '此操作将永久删除该数据源，是否继续？',
          '确认删除',
          {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger',
          }
        )
        // 用户确认后执行删除
        await deleteDataSource(row)
      } catch {
        // 用户取消删除，不做任何操作
        ElMessage.info('已取消删除')
      }
      break
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
  gap: 8px;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: nowrap;
}

/* 下拉菜单项样式优化 */
.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.el-dropdown-menu__item .el-icon {
  font-size: 14px;
  width: 14px;
  height: 14px;
}

/* 更多按钮样式 */
.action-buttons .el-dropdown .el-button {
  padding: 4px 8px;
  font-size: 12px;
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
