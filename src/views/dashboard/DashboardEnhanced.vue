<template>
  <div class="page-container">
    <div class="dashboard-header">
      <h1>数据浏览系统仪表盘</h1>
      <p>欢迎回来，{{ authStore.currentUser?.name }}</p>
      <div class="header-actions">
        <el-button 
          v-if="authStore.isAdmin"
          type="primary" 
          @click="runManualStats"
          :loading="statsLoading"
        >
          执行统计任务
        </el-button>
        <el-button @click="refreshCharts" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
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
            <small v-if="stats.statsDate" class="stats-date">
              统计日期: {{ formatStatsDate(stats.statsDate) }}
            </small>
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
            <h3>{{ stats.totalFiles }}</h3>
            <p>文件总数</p>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon records-icon">
            <el-icon><Box /></el-icon>
          </div>
          <div class="stat-info">
            <h3>{{ formatNumber(stats.totalRecords) }}</h3>
            <p>数据记录数</p>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <div class="charts-grid">
        <!-- 数据类型分布（按数据大小） -->
        <el-card class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>数据类型分布</span>
              <div class="header-tags">
                <el-tag v-if="typeDistributionStatsDate" size="small" type="info">
                  {{ formatStatsDate(typeDistributionStatsDate) }}
                </el-tag>
                <el-tag v-else size="small" type="warning">
                  实时数据
                </el-tag>
              </div>
            </div>
          </template>
          <div class="chart-container">
            <v-chart 
              class="chart" 
              :option="typeDistributionOption" 
              autoresize
            />
          </div>
        </el-card>

        <!-- 数据源分布（按数据大小排序） -->
        <el-card class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>数据源分布（Top 10）</span>
              <div class="header-tags">
                <el-tag v-if="datasourceDistributionStatsDate" size="small" type="info">
                  {{ formatStatsDate(datasourceDistributionStatsDate) }}
                </el-tag>
                <el-tag v-else size="small" type="warning">
                  实时数据
                </el-tag>
              </div>
            </div>
          </template>
          <div class="chart-container">
            <v-chart 
              class="chart" 
              :option="datasourceDistributionOption" 
              autoresize
            />
          </div>
        </el-card>
      </div>
    </div>

    <!-- 信息面板 -->
    <div class="info-section">
      <div class="info-grid">
        <!-- 系统状态 -->
        <el-card class="system-status-card">
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">数据库</span>
              <el-tag :type="systemStatus.database ? 'success' : 'danger'">
                {{ systemStatus.database ? '正常' : '异常' }}
              </el-tag>
            </div>
            
            <div class="status-item">
              <span class="status-label">缓存</span>
              <el-tag :type="systemStatus.cache ? 'success' : 'info'">
                {{ systemStatus.cache ? '启用' : '未启用' }}
              </el-tag>
            </div>
            
            <div class="status-item">
              <span class="status-label">调度器</span>
              <el-tag 
                :type="systemStatus.scheduler.status === 'running' ? 'success' : 'info'"
              >
                {{ systemStatus.scheduler.status === 'running' ? '运行中' : '已停止' }}
              </el-tag>
            </div>
            
            <div class="status-item">
              <span class="status-label">系统版本</span>
              <el-tag type="info">v1.0.0</el-tag>
            </div>
          </div>
          
          <!-- 统计任务状态 -->
          <div v-if="systemStatus.last_stats_task" class="stats-task-status">
            <h4>最近统计任务</h4>
            <div class="task-info">
              <p>
                <strong>日期:</strong> 
                {{ formatStatsDate(systemStatus.last_stats_task.date) }}
              </p>
              <p>
                <strong>状态:</strong>
                <el-tag 
                  :type="getTaskStatusType(systemStatus.last_stats_task.status)"
                  size="small"
                >
                  {{ getTaskStatusText(systemStatus.last_stats_task.status) }}
                </el-tag>
              </p>
              <p v-if="systemStatus.last_stats_task.duration">
                <strong>耗时:</strong> {{ systemStatus.last_stats_task.duration }} 秒
              </p>
            </div>
          </div>
          
          <!-- 计划任务列表 -->
          <div v-if="systemStatus.scheduler.jobs && systemStatus.scheduler.jobs.length > 0" class="scheduled-jobs">
            <h4>计划任务</h4>
            <div class="job-list">
              <div v-for="job in systemStatus.scheduler.jobs" :key="job.id" class="job-item">
                <span class="job-name">{{ job.name }}</span>
                <span class="job-next-run">
                  {{ job.next_run_time ? formatJobTime(job.next_run_time) : '无计划' }}
                </span>
              </div>
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
import { PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'
import type { DataSource } from '@/types/datasource'
import { dashboardApi } from '@/api/dashboard'
import type { TypeDistribution, DataSourceDistribution } from '@/api/dashboard'

// 注册 ECharts 组件
use([
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer
])

const router = useRouter()
const authStore = useAuthStore()
const dataSourceStore = useDataSourceStore()

// 响应式数据
const loading = ref(false)
const statsLoading = ref(false)

const stats = reactive({
  totalDataSources: 0,
  totalUsers: 0,
  totalDataSize: 0,
  totalFiles: 0,
  totalRecords: 0,
  statsDate: null as string | null
})

const systemStatus = reactive({
  database: true,
  cache: false,
  scheduler: {
    status: 'stopped',
    jobs: [] as any[]
  },
  last_stats_task: null as any
})

// 图表数据
const typeDistribution = ref<TypeDistribution[]>([])
const typeDistributionStatsDate = ref<string | null>(null)
const datasourceDistribution = ref<DataSourceDistribution[]>([])
const datasourceDistributionStatsDate = ref<string | null>(null)

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
      data: typeDistribution.value.map(item => ({
        value: item.value,
        name: item.name,
        count: item.count,
        itemStyle: {
          color: item.type === 'filesystem' ? '#5470c6' : 
                 item.type === 'database' ? '#91cc75' : '#fac858'
        }
      }))
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
      if (params.length === 0) return ''
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
    bottom: '15%',
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

// API 方法
const refreshStats = async () => {
  try {
    const response = await dashboardApi.getStats()
    // 处理可能的响应格式：response.data 或 response 本身
    const dashboardStats = response.data || response

    stats.totalDataSources = dashboardStats.total_datasources || 0
    stats.totalUsers = dashboardStats.total_users || 0
    stats.totalDataSize = dashboardStats.total_data_size || 0
    stats.totalFiles = dashboardStats.total_files || 0
    stats.totalRecords = dashboardStats.total_records || 0
    stats.statsDate = dashboardStats.stats_date || null
    

  } catch (error) {
    console.error('❌ Dashboard: 获取统计数据失败', error)
    ElMessage.error('获取统计数据失败')
  }
}

const refreshSystemStatus = async () => {
  try {
    const response = await dashboardApi.getSystemStatus()
    // 处理可能的响应格式：response.data 或 response 本身
    const statusData = response.data || response

    systemStatus.database = statusData.database
    systemStatus.cache = statusData.cache
    systemStatus.scheduler = statusData.scheduler || { status: 'stopped', jobs: [] }
    systemStatus.last_stats_task = statusData.last_stats_task
  } catch (error) {
    console.error('❌ Dashboard: 获取系统状态失败', error)
  }
}

const refreshTypeDistribution = async () => {
  try {
    const response = await dashboardApi.getTypeDistribution()
    // 处理可能的响应格式：response.data 或 response 本身
    const data = response.data || response

    typeDistribution.value = data.distribution || []
    typeDistributionStatsDate.value = data.stats_date
    

  } catch (error) {
    console.error('❌ Dashboard: 获取数据类型分布失败', error)
  }
}

const refreshDatasourceDistribution = async () => {
  try {
    const response = await dashboardApi.getDataSourceDistribution(10)
    // 处理可能的响应格式：response.data 或 response 本身
    const data = response.data || response

    datasourceDistribution.value = data.distribution || []
    datasourceDistributionStatsDate.value = data.stats_date
    

  } catch (error) {
    console.error('❌ Dashboard: 获取数据源分布失败', error)
  }
}

const runManualStats = async () => {
  if (!authStore.isAdmin) {
    ElMessage.error('需要管理员权限')
    return
  }
  
  statsLoading.value = true
  try {
    const response = await dashboardApi.runManualStats()
    // 处理可能的响应格式：response.data 或 response 本身
    const result = response.data || response
    
    ElMessage.success('统计任务已启动，请稍后查看结果')

    
    // 等待几秒后刷新数据
    setTimeout(() => {
      refreshCharts()
    }, 3000)
  } catch (error) {
    console.error('❌ Dashboard: 执行统计任务失败', error)
    ElMessage.error('执行统计任务失败')
  } finally {
    statsLoading.value = false
  }
}

const refreshCharts = async () => {
  loading.value = true
  try {
    await dataSourceStore.fetchDataSources()
    
    // 使用Promise.all同时获取所有数据
    await Promise.all([
      refreshStats(),
      refreshSystemStatus(),
      refreshTypeDistribution(),
      refreshDatasourceDistribution()
    ])
  } catch (error) {
    console.error('Dashboard refresh error:', error)
    ElMessage.error('数据刷新失败')
  } finally {
    loading.value = false
  }
}

// 工具函数
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const formatStatsDate = (dateStr: string | null): string => {
  if (!dateStr) return '实时数据'
  
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatJobTime = (timeStr: string): string => {
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

const getTaskStatusType = (status: string): string => {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getTaskStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'completed': '已完成',
    'running': '运行中',
    'failed': '失败',
    'pending': '待执行'
  }
  return statusMap[status] || status
}

// 其他方法保持不变
const navigateToDataSource = (dataSource: DataSource) => {
  const routeTypeMap: Record<string, string> = {
    filesystem: 'filesystem',
    database: 'database',
    object_storage: 'object_storage'
  }
  
  const routeType = routeTypeMap[dataSource.type] || dataSource.type
  router.push(`/browse/${routeType}/${dataSource.id}`)
}

const formatRelativeTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  if (days < 30) return `${Math.floor(days / 7)}周前`
  return `${Math.floor(days / 30)}个月前`
}

const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

// 生命周期
onMounted(() => {
  refreshCharts()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dashboard-header h1 {
  margin: 0;
  color: #303133;
}

.dashboard-header p {
  margin: 5px 0 0 0;
  color: #606266;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

.datasource-icon { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.users-icon { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.storage-icon { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.files-icon { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
.records-icon { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }

.stat-info h3 {
  margin: 0;
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-info p {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.stats-date {
  color: #409EFF;
  font-size: 12px;
}

.admin-only-hint {
  color: #E6A23C;
  font-size: 12px;
}

.charts-section {
  margin-bottom: 20px;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-card {
  height: 400px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-tags {
  display: flex;
  gap: 8px;
}

.chart-container {
  height: 320px;
  width: 100%;
}

.chart {
  height: 100%;
  width: 100%;
}

.info-section {
  margin-bottom: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.system-status-card {
  min-height: 300px;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border: 1px solid #EBEEF5;
  border-radius: 6px;
}

.status-label {
  font-weight: 500;
  color: #606266;
}

.stats-task-status {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
}

.stats-task-status h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 16px;
}

.task-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #606266;
}

.scheduled-jobs {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
}

.scheduled-jobs h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 16px;
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.job-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #F5F7FA;
  border-radius: 4px;
  font-size: 13px;
}

.job-name {
  font-weight: 500;
  color: #303133;
}

.job-next-run {
  color: #909399;
}

.actions-card {
  height: fit-content;
}

.actions-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.actions-grid .el-button {
  justify-content: flex-start;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
  
  .stat-content {
    flex-direction: column;
    text-align: center;
  }
  
  .stat-icon {
    width: 50px;
    height: 50px;
    font-size: 20px;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
