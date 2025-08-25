<template>
  <div class="page-container">
    <div class="dashboard-header">
      <h1>数据浏览系统仪表盘</h1>
      <p>欢迎回来，{{ authStore.currentUser?.name }}</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon datasource-icon">
            <el-icon><DataBoard /></el-icon>
          </div>
          <div class="stat-info">
            <h3>{{ stats.totalDataSources }}</h3>
            <p>数据源总数</p>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon users-icon">
            <el-icon><UserFilled /></el-icon>
          </div>
          <div class="stat-info">
            <h3 v-if="authStore.isAdmin">{{ stats.totalUsers }}</h3>
            <h3 v-else>-</h3>
            <p>用户总数</p>
            <small v-if="!authStore.isAdmin" class="admin-only-hint">需要管理员权限</small>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon storage-icon">
            <el-icon><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <h3>{{ formatFileSize(stats.totalDataSize) }}</h3>
            <p>数据总量</p>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon files-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-info">
            <h3>{{ formatNumber(stats.totalFiles) }}</h3>
            <p>文件总数</p>
          </div>
        </div>
      </el-card>
    </div>

    <div class="dashboard-content">
      <div class="left-column">
        <!-- 数据源类型分布图表 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>数据源类型分布</span>
              <el-button text @click="refreshCharts">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <div class="chart-container">
            <v-chart 
              :option="pieChartOption" 
              :loading="loading"
              class="chart"
            />
          </div>
        </el-card>

        <!-- 最近添加的数据源 -->
        <el-card class="recent-card">
          <template #header>
            <div class="card-header">
              <span>最近添加的数据源</span>
              <el-link type="primary" @click="$router.push('/datasources')">
                查看全部
              </el-link>
            </div>
          </template>
          <div class="recent-list">
            <div 
              v-for="datasource in recentDataSources" 
              :key="datasource.id"
              class="recent-item"
              @click="navigateToDataSource(datasource)"
            >
              <div class="recent-icon">
                <el-icon>
                  <Folder v-if="datasource.type === 'filesystem'" />
                  <Coin v-else-if="datasource.type === 'database'" />
                  <Box v-else />
                </el-icon>
              </div>
              <div class="recent-info">
                <h4>{{ datasource.cname || datasource.name }}</h4>
                <p>{{ formatDate(datasource.created_at) }}</p>
              </div>
              <div class="recent-status">
                <el-tag 
                  :type="datasource.is_connected ? 'success' : 'warning'"
                  size="small"
                >
                  {{ datasource.is_connected ? '已连接' : '未连接' }}
                </el-tag>
              </div>
            </div>
            
            <el-empty 
              v-if="recentDataSources.length === 0"
              description="暂无数据源"
              :image-size="120"
            />
          </div>
        </el-card>
      </div>

      <div class="right-column">
        <!-- 系统状态 -->
        <el-card class="status-card">
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="status-list">
            <div class="status-item">
              <span class="status-label">数据库连接</span>
              <el-tag :type="systemStatus.database ? 'success' : 'danger'">
                {{ systemStatus.database ? '正常' : '异常' }}
              </el-tag>
            </div>
            <div class="status-item">
              <span class="status-label">缓存服务</span>
              <el-tag :type="systemStatus.cache ? 'success' : 'info'">
                {{ systemStatus.cache ? '正常' : '未启用' }}
              </el-tag>
            </div>
            <div class="status-item">
              <span class="status-label">系统版本</span>
              <el-tag type="info">v1.0.0</el-tag>
            </div>
          </div>
        </el-card>

        <!-- 快捷操作 -->
        <el-card class="actions-card">
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="actions-grid">
            <el-button 
              v-if="authStore.isAdmin"
              type="primary" 
              @click="$router.push('/datasources/create')"
            >
              <el-icon><Plus /></el-icon>
              添加数据源
            </el-button>
            
            <el-button 
              v-if="authStore.isAdmin"
              @click="$router.push('/users')"
            >
              <el-icon><UserFilled /></el-icon>
              用户管理
            </el-button>
            
            <el-button @click="$router.push('/profile')">
              <el-icon><User /></el-icon>
              个人设置
            </el-button>
            
            <el-button @click="exportData">
              <el-icon><Download /></el-icon>
              导出数据
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataBoard,
  UserFilled,
  FolderOpened,
  Document,
  Refresh,
  Folder,
  Coin,
  Box,
  Plus,
  User,
  Download
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'
import type { DataSource } from '@/types/datasource'
import { dashboardApi } from '@/api/dashboard'

// 注册 ECharts 组件
use([
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer
])

const router = useRouter()
const authStore = useAuthStore()
const dataSourceStore = useDataSourceStore()

// 响应式数据
const loading = ref(false)
const stats = reactive({
  totalDataSources: 0,
  totalUsers: 0,
  totalDataSize: 0,
  totalFiles: 0,
  totalRecords: 0,
  statsDate: null
})

const systemStatus = reactive({
  database: true,
  cache: false,
  scheduler: {
    status: 'stopped',
    jobs: []
  },
  last_stats_task: null
})

// 图表数据
const typeDistribution = ref([])
const typeDistributionStatsDate = ref(null)
const datasourceDistribution = ref([])
const datasourceDistributionStatsDate = ref(null)

// 计算属性
const recentDataSources = computed(() => {
  return dataSourceStore.dataSources
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)
})

// 数据类型分布图表配置
const typeDistributionOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: function(params: any) {
      const size = formatFileSize(params.value)
      return `${params.name}<br/>数据大小: ${size}<br/>数据源数量: ${params.data.count}<br/>占比: ${params.percent}%`
    }
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      name: '数据类型分布',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: function(params: any) {
          return `${params.name}\n${formatFileSize(params.value)}`
        }
      },
      labelLine: {
        show: true
      },
      data: typeDistribution.value
    }
  ]
}))

// 数据源分布图表配置
const datasourceDistributionOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    },
    formatter: function(params: any) {
      const item = params[0]
      const data = datasourceDistribution.value[item.dataIndex]
      return `
        <div>
          <strong>${data.name}</strong><br/>
          类型: ${data.type}<br/>
          数据大小: ${formatFileSize(item.value)}<br/>
          文件数: ${data.files || 0}<br/>
          记录数: ${data.records || 0}
        </div>
      `
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '8%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: datasourceDistribution.value.map(item => item.name),
    axisLabel: {
      interval: 0,
      rotate: 45,
      formatter: function(value: string) {
        return value.length > 10 ? value.slice(0, 10) + '...' : value
      }
    }
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      formatter: function(value: number) {
        return formatFileSize(value)
      }
    }
  },
  series: [
    {
      name: '数据大小',
      type: 'bar',
      data: datasourceDistribution.value.map((item, index) => ({
        value: item.size,
        itemStyle: {
          color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'][index % 5]
        }
      })),
      barWidth: '60%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0]
      }
    }
  ]
}))

// 方法
const refreshStats = async () => {
  try {
    // 从后端API获取统计数据
    const response = await dashboardApi.getStats()
    const dashboardStats = response.data || response
    
    // 更新统计数据
    stats.totalDataSources = dashboardStats.total_datasources || 0
    stats.totalUsers = dashboardStats.total_users || 0
    stats.totalDataSize = dashboardStats.total_data_size || 0
    stats.totalFiles = dashboardStats.total_files || 0
    stats.totalRecords = dashboardStats.total_records || 0
    stats.statsDate = dashboardStats.stats_date || null
    
    console.log('📊 Dashboard: 统计数据更新完成', {
      dataSources: stats.totalDataSources,
      users: stats.totalUsers,
      dataSize: stats.totalDataSize,
      files: stats.totalFiles,
      records: stats.totalRecords,
      statsDate: stats.statsDate,
      isAdmin: dashboardStats.is_admin
    })
  } catch (error) {
    console.error('❌ Dashboard: 获取统计数据失败', error)
    ElMessage.error('获取统计数据失败')
  }
}

const refreshSystemStatus = async () => {
  try {
    const response = await dashboardApi.getSystemStatus()
    const statusData = response.data || response
    
    // 更新系统状态
    systemStatus.database = statusData.database
    systemStatus.cache = statusData.cache
    
    console.log('📊 Dashboard: 系统状态更新完成', statusData)
  } catch (error) {
    console.error('❌ Dashboard: 获取系统状态失败', error)
  }
}

const refreshCharts = async () => {
  loading.value = true
  try {
    // 同时获取数据源数据和统计数据
    await Promise.all([
      dataSourceStore.fetchDataSources(),
      refreshStats(),
      refreshSystemStatus()
    ])
  } catch (error) {
    ElMessage.error('刷新数据失败')
  } finally {
    loading.value = false
  }
}

const navigateToDataSource = (datasource: DataSource) => {
  // 映射数据源类型到路由路径
  const routeTypeMap: Record<string, string> = {
    'filesystem': 'filesystem',
    'database': 'database', 
    'object_storage': 'objectstorage'
  }
  const routeType = routeTypeMap[datasource.type] || datasource.type
  router.push(`/browse/${routeType}/${datasource.id}`)
}

const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString('zh-CN')
}

// 生命周期
onMounted(async () => {
  try {
    await refreshCharts()
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})

// 页面标题
document.title = '仪表盘 - 数据浏览系统'
</script>

<style scoped>
.page-container {
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

/* 统计卡片网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px 0 rgba(0, 0, 0, 0.12);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

.datasource-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.users-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.storage-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.files-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info h3 {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0 0 4px 0;
}

.stat-info p {
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin: 0;
}

.admin-only-hint {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  font-style: italic;
  margin-top: 2px;
  display: block;
}

/* 内容布局 */
.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

.left-column,
.right-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 卡片样式 */
.chart-card,
.recent-card,
.status-card,
.actions-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 300px;
}

.chart {
  width: 100%;
  height: 100%;
}

/* 最近数据源列表 */
.recent-list {
  max-height: 400px;
  overflow-y: auto;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background-color 0.2s;
}

.recent-item:hover {
  background-color: var(--el-fill-color-lighter);
  margin: 0 -16px;
  padding: 12px 16px;
  border-radius: 8px;
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-icon {
  width: 32px;
  height: 32px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-primary);
}

.recent-info {
  flex: 1;
}

.recent-info h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 4px 0;
}

.recent-info p {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0;
}

/* 系统状态 */
.status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.status-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* 快捷操作 */
.actions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.actions-grid .el-button {
  justify-content: flex-start;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .dashboard-content {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .actions-grid {
    grid-template-columns: 1fr;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style>
