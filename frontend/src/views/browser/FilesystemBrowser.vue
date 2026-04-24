<template>
  <div class="filesystem-browser">
    <div class="header">
      <div class="breadcrumb-section">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <router-link to="/datasources">数据源</router-link>
          </el-breadcrumb-item>
          <el-breadcrumb-item>{{ dataSource?.cname || dataSource?.name || '加载中...' }}</el-breadcrumb-item>
          <el-breadcrumb-item 
            v-for="(part, index) in pathParts" 
            :key="index"
            :class="{ 'is-link': index < pathParts.length - 1 }"
            @click="navigateToPath(index)"
          >
            {{ part }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      
      <div class="toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索文件..."
          style="width: 200px"
          prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
        
        <el-button-group>
          <el-button 
            :type="viewMode === 'list' ? 'primary' : ''" 
            icon="List" 
            @click="viewMode = 'list'"
          />
          <el-button 
            :type="viewMode === 'grid' ? 'primary' : ''" 
            icon="Grid" 
            @click="viewMode = 'grid'"
          />
        </el-button-group>
        
        <el-button 
          type="primary" 
          icon="Refresh" 
          @click="refreshData"
          :loading="loading"
        >
          刷新
        </el-button>
      </div>
    </div>

    <!-- 快速访问栏 -->
    <div class="quick-access" v-if="favorites.length > 0">
      <div class="section-title">
        <el-icon><Star /></el-icon>
        收藏夹
      </div>
      <div class="favorites">
        <el-tag
          v-for="fav in favorites"
          :key="fav.path"
          closable
          @close="removeFavorite(fav.path)"
          @click="navigateToAbsolutePath(fav.path)"
          class="favorite-tag"
        >
          <el-icon><Folder /></el-icon>
          {{ fav.name }}
        </el-tag>
      </div>
    </div>

    <div class="content">
      <!-- 文件夹树形导航 -->
      <div class="sidebar" v-if="showSidebar">
        <div class="section-title">
          <el-icon><FolderOpened /></el-icon>
          目录结构
        </div>
        
        <el-tree
          :data="directoryTree"
          :props="{ label: 'name', children: 'children', isLeaf: 'isLeaf' }"
          @node-click="handleTreeNodeClick"
          :expand-on-click-node="false"
          :highlight-current="true"
          node-key="path"
          :current-node-key="currentPath"
          lazy
          :load="loadTreeNode"
        >
          <template #default="{ node, data }">
            <span class="tree-node">
              <el-icon v-if="data.type === 'directory'"><Folder /></el-icon>
              <el-icon v-else><Document /></el-icon>
              {{ data.name }}
            </span>
          </template>
        </el-tree>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 文件操作栏 -->
        <div class="action-bar">
          <div class="path-info">
            <span class="current-path">{{ currentPath || '/' }}</span>
            <el-button 
              type="text" 
              icon="Star" 
              size="small"
              @click="addToFavorites"
              :disabled="isInFavorites"
            >
              {{ isInFavorites ? '已收藏' : '收藏' }}
            </el-button>
          </div>
          
          <div class="file-stats">
            <span>{{ filteredFiles.length }} 项</span>
            <span v-if="selectedFiles.length > 0">
              ({{ selectedFiles.length }} 选中)
            </span>
          </div>
        </div>
        
        <!-- 性能提示 -->
        <div class="performance-tip" v-if="totalFiles > 100">
          <el-alert
            :title="`此目录包含 ${totalFiles} 个文件，建议使用分页浏览以提高性能`"
            type="info"
            :closable="false"
            show-icon
            class="performance-alert"
          />
        </div>

        <!-- 文件列表 -->
        <div class="file-list" v-loading="loading">
          <!-- 列表视图 -->
          <el-table
            v-if="viewMode === 'list'"
            :data="filteredFiles"
            @row-dblclick="handleDoubleClick"
            @selection-change="handleSelectionChange"
            :row-class-name="getRowClassName"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="name" label="名称" min-width="300">
              <template #default="{ row }">
                <div class="file-item">
                  <el-icon class="file-icon" :class="getFileIconClass(row)">
                    <component :is="getFileIcon(row)" />
                  </el-icon>
                  <span 
                    class="file-name" 
                    :class="{ 'is-link': row.type === 'directory' }"
                    @click="handleItemClick(row)"
                  >
                    {{ row.name }}
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="120" sortable>
              <template #default="{ row }">
                {{ formatFileSize(row.size) }}
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="modified_at" label="修改时间" width="180" sortable>
              <template #default="{ row }">
                {{ formatDate(row.modified_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="permissions" label="权限" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="getPermissionType(row.permissions)">
                  {{ row.permissions || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button-group size="small">
                  <el-button 
                    v-if="row.type !== 'directory'" 
                    icon="View" 
                    @click="previewFile(row)"
                    :disabled="!canPreview(row)"
                  >
                    预览
                  </el-button>
                  <el-button 
                    v-if="row.type !== 'directory'"
                    icon="ChatDotRound"
                    @click="openAnalyze(row)"
                    :disabled="!canAnalyze(row)"
                  >
                    分析
                  </el-button>
                  <el-button 
                    icon="Download" 
                    @click="downloadFile(row)"
                    v-if="row.type !== 'directory'"
                  >
                    下载
                  </el-button>
                  <el-button 
                    v-if="row.type !== 'directory'"
                    icon="Link" 
                    @click="copyApiLink(row)"
                    title="复制API链接"
                  >
                    API
                  </el-button>
                  <el-dropdown @command="handleFileAction">
                    <el-button icon="More" />
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item :command="{ action: 'info', file: row }">
                          <el-icon><InfoFilled /></el-icon>
                          详细信息
                        </el-dropdown-item>
                        <el-dropdown-item :command="{ action: 'rename', file: row }">
                          <el-icon><Edit /></el-icon>
                          重命名
                        </el-dropdown-item>
                        <el-dropdown-item 
                          :command="{ action: 'delete', file: row }"
                          divided
                        >
                          <el-icon><Delete /></el-icon>
                          删除
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>

          <!-- 网格视图 -->
          <div v-else class="file-grid">
            <div
              v-for="file in filteredFiles"
              :key="file.path"
              class="file-card"
              :class="{ 
                'is-selected': selectedFiles.includes(file),
                'is-directory': file.type === 'directory'
              }"
              @click="handleItemClick(file, $event)"
              @dblclick="handleDoubleClick(file)"
            >
              <div class="file-icon-large">
                <el-icon :class="getFileIconClass(file)">
                  <component :is="getFileIcon(file)" />
                </el-icon>
              </div>
              <div class="file-info">
                <div class="file-name" :title="file.name">{{ file.name }}</div>
                <div class="file-meta">
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <span class="file-date">{{ formatDate(file.modified_at, true) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="!loading && filteredFiles.length === 0" class="empty-state">
            <el-empty description="此目录为空" />
          </div>
        </div>
        
        <!-- 分页组件 -->
        <div class="pagination-container" v-if="totalFiles > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100, 200, 500]"
            :total="totalFiles"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- 文件预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="currentPreviewFile.name"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="file-preview">
        <!-- 文本预览 -->
        <div v-if="previewType === 'text'" class="text-preview">
          <pre>{{ previewContent }}</pre>
        </div>
        
        <!-- 图片预览 -->
        <div v-else-if="previewType === 'image'" class="image-preview">
          <img :src="previewUrl" :alt="currentPreviewFile.name" />
        </div>

        <!-- 视频预览 -->
        <div v-else-if="previewType === 'video'" class="video-preview">
          <video :src="previewUrl" controls style="max-width: 100%; max-height: 70vh;"></video>
        </div>
        
        <!-- JSON预览 -->
        <div v-else-if="previewType === 'json'" class="json-preview">
          <pre>{{ formatJson(previewContent) }}</pre>
        </div>
        
        <!-- Excel预览 -->
        <div v-else-if="previewType === 'excel'" class="excel-preview">
          <div class="excel-toolbar" v-if="currentPreviewFile.excelInfo">
            <el-tag size="small" type="success">Excel表格</el-tag>
            <el-tag size="small">{{ currentPreviewFile.excelInfo.rows }} 行</el-tag>
            <el-tag size="small">{{ currentPreviewFile.excelInfo.columns?.length || 0 }} 列</el-tag>
            <el-tag size="small">{{ formatFileSize(currentPreviewFile.size || 0) }}</el-tag>
          </div>
          <div class="excel-content" v-html="previewContent"></div>
        </div>
        
        <!-- NC文件预览 -->
        <div v-else-if="previewType === 'nc'" class="nc-preview">
          <div v-if="currentPreviewFile.ncInfo?.loading" class="nc-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在加载NC文件信息...</span>
          </div>
          <div v-else-if="currentPreviewFile.ncInfo?.error" class="nc-error">
            <el-result icon="error" title="加载失败" :sub-title="currentPreviewFile.ncInfo.error" />
          </div>
          <div v-else class="nc-content">
            <div class="nc-toolbar">
              <el-tag size="small" type="success">NetCDF文件</el-tag>
              <el-tag size="small" v-if="currentPreviewFile.ncVariable">{{ currentPreviewFile.ncVariable }}</el-tag>
              <el-tag size="small">{{ formatFileSize(currentPreviewFile.ncInfo?.fileSize || 0) }}</el-tag>
            </div>
            <div v-if="currentPreviewFile.ncImage" class="nc-image">
              <img :src="currentPreviewFile.ncImage" alt="NC文件可视化" />
            </div>
            <div v-if="currentPreviewFile.ncStats" class="nc-stats">
              <el-descriptions :column="4" border>
                <el-descriptions-item label="最小值">{{ currentPreviewFile.ncStats.min?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="最大值">{{ currentPreviewFile.ncStats.max?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="平均值">{{ currentPreviewFile.ncStats.mean?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="维度">{{ currentPreviewFile.ncStats.shape?.join(' x ') }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <div v-if="currentPreviewFile.ncInfo?.dimensions" class="nc-dimensions">
              <h4>维度信息</h4>
              <el-tag v-for="(value, key) in currentPreviewFile.ncInfo.dimensions" :key="key" size="small" style="margin-right: 8px; margin-bottom: 4px;">
                {{ key }}: {{ value }}
              </el-tag>
            </div>
            <div v-if="currentPreviewFile.ncInfo?.variables" class="nc-variables">
              <h4>变量列表</h4>
              <el-table :data="currentPreviewFile.ncInfo.variables" size="small" max-height="200">
                <el-table-column prop="name" label="变量名" width="120" />
                <el-table-column prop="shape" label="形状" width="150">
                  <template #default="{ row }">
                    {{ row.shape.join(' x ') }}
                  </template>
                </el-table-column>
                <el-table-column prop="dtype" label="数据类型" width="100" />
              </el-table>
            </div>
          </div>
        </div>
        
        <!-- 其他类型 -->
        <div v-else class="unsupported-preview">
          <el-result
            icon="warning"
            title="预览不支持"
            sub-title="此文件类型暂不支持在线预览"
          >
            <template #extra>
              <el-button type="primary" @click="downloadFile(currentPreviewFile)">
                下载查看
              </el-button>
            </template>
          </el-result>
        </div>
      </div>
    </el-dialog>

    <!-- 文件详情对话框 -->
    <el-dialog v-model="showInfoDialog" title="文件详情" width="500px">
      <el-descriptions :column="1" border v-if="selectedFileInfo">
        <el-descriptions-item label="名称">{{ selectedFileInfo.name }}</el-descriptions-item>
        <el-descriptions-item label="路径">{{ selectedFileInfo.path }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ selectedFileInfo.type }}</el-descriptions-item>
        <el-descriptions-item label="大小">{{ formatFileSize(selectedFileInfo.size) }}</el-descriptions-item>
        <el-descriptions-item label="权限">{{ selectedFileInfo.permissions || '-' }}</el-descriptions-item>
        <el-descriptions-item label="修改时间">{{ formatDate(selectedFileInfo.modified_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 资源分析对话弹窗 -->
    <ResourceAnalyzeDialog
      v-model:visible="showAnalyzeDialog"
      :resource-key="analyzeResourceKey"
      :resource-display-name="analyzeDisplayName"
      :datasource-type="analyzeDatasourceType"
      :datasource-id="analyzeDatasourceId"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { 
  Folder, FolderOpened, Document, Star, List, Grid, 
  Search, Refresh, View, Download, More, InfoFilled, 
  Edit, Delete, Picture, VideoPlay, Box, ChatDotRound
} from '@element-plus/icons-vue'
import ResourceAnalyzeDialog from '@/components/ResourceAnalyzeDialog.vue'
import { useDataSourceStore } from '@/stores/datasource'
import { useAuthStore } from '@/stores/auth'
import { filesystemApi } from '@/api/datasource'

const route = useRoute()
const router = useRouter()
const dataSourceStore = useDataSourceStore()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const dataSource = ref(null)
const currentPath = ref('')
const files = ref([])
const searchQuery = ref('')
const viewMode = ref('list')
const showSidebar = ref(true)
const selectedFiles = ref([])
const directoryTree = ref([])
const favorites = ref([])

// 分页相关
const currentPage = ref(1)
const pageSize = ref(50)
const totalFiles = ref(0)

// 预览相关
const showPreviewDialog = ref(false)
const currentPreviewFile = ref({})
const previewContent = ref('')
const previewUrl = ref('')
const previewType = ref('')

// 详情对话框
const showInfoDialog = ref(false)
const selectedFileInfo = ref(null)

// 分析对话
const showAnalyzeDialog = ref(false)
const analyzeResourceKey = ref('')
const analyzeDisplayName = ref('')
const analyzeDatasourceType = ref('filesystem')
const analyzeDatasourceId = ref('')

// 计算属性
const pathParts = computed(() => {
  if (!currentPath.value) return []
  return currentPath.value.split('/').filter(part => part)
})

const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  const query = searchQuery.value.toLowerCase()
  return files.value.filter(file => 
    file.name.toLowerCase().includes(query)
  )
})

const isInFavorites = computed(() => {
  return favorites.value.some(fav => fav.path === currentPath.value)
})

// 生命周期
onMounted(async () => {
  await loadDataSource()
  currentPath.value = (route.query.path as string) || ''
  const pathFromQuery = currentPath.value
  if (pathFromQuery) {
    await tryPreviewPathFromQuery(pathFromQuery)
  }
  await loadDirectoryTree()
  await loadFiles()
  loadFavorites()
})

// 监听路由变化
watch(() => route.params.id, async (newId) => {
  if (newId) {
    await loadDataSource()
    await loadDirectoryTree()
    currentPath.value = (route.query.path as string) || ''
    if (currentPath.value) {
      await tryPreviewPathFromQuery(currentPath.value)
    }
    await loadFiles()
  }
})

watch(() => route.query.path, async (newPath) => {
  const pathStr = (newPath as string) || ''
  currentPath.value = pathStr
  if (pathStr) {
    await tryPreviewPathFromQuery(pathStr)
  }
  loadFiles()
})

// 方法
async function loadDataSource() {
  try {
    const id = route.params.id as string
    const response = await dataSourceStore.fetchDataSourceById(id)
    dataSource.value = response.data
  } catch (error) {
    ElMessage.error('加载数据源失败')
    
    // 如果API失败，尝试从当前数据源列表中找
    const currentList = dataSourceStore.dataSources
    const id = route.params.id as string
    
    if (Array.isArray(currentList)) {
      const found = currentList.find(ds => ds.id === id)
      if (found) {
        dataSource.value = found
      }
    } else {
      // 如枟数据源列表还未加载，尝试强制获取
      try {
        await dataSourceStore.fetchDataSources()
        const newList = dataSourceStore.dataSources
        if (Array.isArray(newList)) {
          const found = newList.find(ds => ds.id === id)
          if (found) {
            dataSource.value = found
          }
        }
      } catch (fetchError) {
        console.error('获取数据源列表失败:', fetchError)
      }
    }
  }
}

async function loadDirectoryTree() {
  try {
    const id = route.params.id as string
    const response = await filesystemApi.listFiles(id, '/')
    
    // 确保正确提取文件数组数据
    let fileData = []
    if (Array.isArray(response)) {
      fileData = response
    } else if (response && Array.isArray(response.data)) {
      fileData = response.data
    } else {
      return
    }
    
    // 构建目录树结构
    directoryTree.value = fileData
      .filter(item => item.type === 'directory')
      .map(item => ({
        name: item.name,
        path: item.path,
        type: 'directory',
        isLeaf: false,
        children: []
      }))
  } catch (error) {
    console.error('❌ 目录树加载失败:', error)
    directoryTree.value = []
  }
}

async function loadFiles() {
  try {
    loading.value = true
    const id = route.params.id as string
    const response = await filesystemApi.listFiles(id, currentPath.value || '/', currentPage.value, pageSize.value)
    
    // 确保正确提取文件数组数据
    let fileData = []
    if (Array.isArray(response)) {
      // 响应拦截器已处理，直接是数组
      fileData = response
    } else if (response && Array.isArray(response.data)) {
      // 响应是包装对象，提取data字段
      fileData = response.data
      // 提取分页信息
      if (response.total !== undefined) {
        totalFiles.value = response.total
      }
      if (response.page !== undefined) {
        currentPage.value = response.page
      }
      if (response.limit !== undefined) {
        pageSize.value = response.limit
      }
    } else {
      console.warn('⚠️ 文件系统浏览: 响应数据格式异常', response)
    }
    
    files.value = fileData
  } catch (error) {
    console.error('❌ 文件系统浏览: 加载文件列表失败', error)
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

async function loadTreeNode(node: any, resolve: Function) {
  try {
    const id = route.params.id as string
    const path = node.data?.path || '/'
    
    const response = await filesystemApi.listFiles(id, path)
    
    // 确保正确提取文件数组数据
    let fileData = []
    if (Array.isArray(response)) {
      fileData = response
    } else if (response && Array.isArray(response.data)) {
      fileData = response.data
    } else {
      resolve([])
      return
    }
    
    const nodes = fileData
      .filter(file => file.type === 'directory')
      .map(dir => ({
        ...dir,
        isLeaf: false
      }))
    
    resolve(nodes)
  } catch (error) {
    console.error('加载树节点失败:', error)
    resolve([])
  }
}

function navigateToPath(index: number) {
  const newPath = pathParts.value.slice(0, index + 1).join('/')
  navigateToAbsolutePath(newPath)
}

function navigateToAbsolutePath(path: string) {
  currentPath.value = path
  router.push({
    query: { ...route.query, path }
  })
}

function handleTreeNodeClick(data: any) {
  navigateToAbsolutePath(data.path)
}

function handleItemClick(file: any, event?: Event) {
  if (event?.ctrlKey || event?.metaKey) {
    // 多选
    const index = selectedFiles.value.findIndex(f => f.path === file.path)
    if (index > -1) {
      selectedFiles.value.splice(index, 1)
    } else {
      selectedFiles.value.push(file)
    }
  } else {
    if (file.type === 'directory') {
      navigateToAbsolutePath(file.path)
    } else {
      selectedFiles.value = [file]
    }
  }
}

function handleDoubleClick(file: any) {
  if (file.type === 'directory') {
    navigateToAbsolutePath(file.path)
  } else {
    previewFile(file)
  }
}

function handleSelectionChange(selection: any[]) {
  selectedFiles.value = selection
}

function handleSearch() {
  // 搜索功能已通过计算属性实现
}

async function refreshData() {
  await loadFiles()
}

// 分页处理函数
function handlePageChange(page: number) {
  currentPage.value = page
  loadFiles()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1  // 重置到第一页
  loadFiles()
}

function getFileIcon(file: any) {
  if (file.type === 'directory') return Folder
  
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) return Picture
  if (['mp4', 'avi', 'mov', 'wmv', 'flv'].includes(ext)) return VideoPlay
  if (['zip', 'rar', 'tar', 'gz'].includes(ext)) return Box
  
  return Document
}

function getFileIconClass(file: any) {
  const classes = ['file-icon']
  if (file.type === 'directory') {
    classes.push('directory-icon')
  } else {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) {
      classes.push('image-icon')
    } else if (['mp4', 'avi', 'mov', 'wmv', 'flv'].includes(ext)) {
      classes.push('video-icon')
    } else if (['zip', 'rar', 'tar', 'gz'].includes(ext)) {
      classes.push('archive-icon')
    }
  }
  return classes.join(' ')
}

function getRowClassName({ row }: { row: any }) {
  return row.type === 'directory' ? 'directory-row' : 'file-row'
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

function formatDate(dateStr: string, short = false): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (short) {
    return date.toLocaleDateString()
  }
  return date.toLocaleString()
}

function getPermissionType(permissions: string | null | undefined): string {
  if (!permissions) return 'info'  // 默认类型
  if (permissions.includes('r') && permissions.includes('w')) return 'success'
  if (permissions.includes('r')) return 'info'
  return 'warning'
}

function canPreview(file: any): boolean {
  // 优先使用后端返回的 extension 字段（去掉前面的点号）
  let ext = file.extension?.toLowerCase()?.replace(/^\./, '')
  
  // 如果没有 extension 字段或为空，则从文件名中提取
  if (!ext && file.name) {
    ext = file.name.split('.').pop()?.toLowerCase()
  }
  
  const textExts = ['txt', 'md', 'json', 'xml', 'csv', 'log']
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
  const excelExts = ['xlsx', 'xls']
  const videoExts = ['mp4', 'mov', 'avi', 'mkv', 'webm']
  const ncExts = ['nc']
  
  return textExts.includes(ext) || imageExts.includes(ext) || excelExts.includes(ext) || videoExts.includes(ext) || ncExts.includes(ext)
}

function canAnalyze(file: any): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase()
  // 分析目前支持：文本类 / 图片 / 视频（会抽帧为图片）/ CSV
  const analyzableTextExts = ['txt', 'md', 'json', 'xml', 'csv', 'log']
  const analyzableImageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
  const analyzableVideoExts = ['mp4', 'mov', 'avi', 'mkv', 'webm']

  return analyzableTextExts.includes(ext) || analyzableImageExts.includes(ext) || analyzableVideoExts.includes(ext)
}

function openAnalyze(row: any) {
  const id = route.params.id as string
  analyzeDatasourceId.value = id
  analyzeDatasourceType.value = 'filesystem'
  analyzeResourceKey.value = `filesystem:${id}:${row.path}`
  analyzeDisplayName.value = row.name || row.path || '文件'
  showAnalyzeDialog.value = true
}

async function previewFile(file: any) {
  try {
    loading.value = true
    currentPreviewFile.value = file
    
    const id = route.params.id as string
    const token = authStore.token || localStorage.getItem('auth_token')
    // 优先使用后端返回的 extension 字段（去掉前面的点号）
    let ext = file.extension?.toLowerCase()?.replace(/^\./, '')
    if (!ext && file.name) {
      ext = file.name.split('.').pop()?.toLowerCase()
    }
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) {
      previewType.value = 'image'
      const base = `/api/browse/filesystem/${id}/download?path=${encodeURIComponent(file.path)}`
      previewUrl.value = token ? `${base}&token=${encodeURIComponent(token)}` : base
    } else if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext || '')) {
      // 本地文件系统视频预览：直接用下载接口作为视频源
      previewType.value = 'video'
      const base = `/api/browse/filesystem/${id}/download?path=${encodeURIComponent(file.path)}`
      previewUrl.value = token ? `${base}&token=${encodeURIComponent(token)}` : base
    } else if (['txt', 'md', 'csv', 'log'].includes(ext)) {
      previewType.value = 'text'
      const response = await fetch(`/api/browse/filesystem/${id}/content?path=${encodeURIComponent(file.path)}`, {
        headers: { 'Authorization': `Bearer ${authStore.token || localStorage.getItem('auth_token')}` }
      })
      const data = await response.json()
      previewContent.value = data.content
    } else if (ext === 'json') {
      previewType.value = 'json'
      const response = await fetch(`/api/browse/filesystem/${id}/content?path=${encodeURIComponent(file.path)}`, {
        headers: { 'Authorization': `Bearer ${authStore.token || localStorage.getItem('auth_token')}` }
      })
      const data = await response.json()
      previewContent.value = data.content
    } else if (['xlsx', 'xls'].includes(ext)) {
      previewType.value = 'excel'
      const response = await fetch(`/api/browse/filesystem/${id}/content?path=${encodeURIComponent(file.path)}`, {
        headers: { 'Authorization': `Bearer ${authStore.token || localStorage.getItem('auth_token')}` }
      })
      const data = await response.json()
      previewContent.value = data.content
      // 存储额外的Excel信息
      currentPreviewFile.value.excelInfo = {
        rows: data.rows,
        columns: data.columns
      }
    } else if (ext === 'nc') {
      previewType.value = 'nc'
      previewUrl.value = ''
      previewContent.value = ''
      currentPreviewFile.value.ncInfo = { loading: true }
      try {
        const infoResponse = await fetch(`/api/browse/filesystem/${id}/nc/info?path=${encodeURIComponent(file.path)}`, {
          headers: { 'Authorization': `Bearer ${authStore.token || localStorage.getItem('auth_token')}` }
        })
        const infoData = await infoResponse.json()
        currentPreviewFile.value.ncInfo = {
          loading: false,
          dimensions: infoData.data.dimensions,
          variables: infoData.data.variables,
          fileSize: infoData.data.file_size
        }
        
        const previewResponse = await fetch(`/api/browse/filesystem/${id}/nc/preview?path=${encodeURIComponent(file.path)}`, {
          headers: { 'Authorization': `Bearer ${authStore.token || localStorage.getItem('auth_token')}` }
        })
        const previewData = await previewResponse.json()
        if (previewData.code === 200) {
          currentPreviewFile.value.ncImage = previewData.data.image
          currentPreviewFile.value.ncVariable = previewData.data.variable
          currentPreviewFile.value.ncStats = {
            min: previewData.data.min,
            max: previewData.data.max,
            mean: previewData.data.mean,
            shape: previewData.data.shape
          }
        }
      } catch (ncError) {
        console.error('NC文件预览失败:', ncError)
        currentPreviewFile.value.ncInfo = { loading: false, error: '预览失败' }
      }
    } else {
      previewType.value = 'unsupported'
    }
    
    showPreviewDialog.value = true
  } catch (error) {
    ElMessage.error('预览失败')
  } finally {
    loading.value = false
  }
}

/**
 * 当 URL 的 path 参数指向文件时，请求内容并自动弹出预览浮窗；若为目录则返回 false。
 * 用于 /browse/filesystem/:id?path=/xxx 直接打开文件预览。
 */
async function tryPreviewPathFromQuery(pathFromQuery: string): Promise<boolean> {
  if (!pathFromQuery || pathFromQuery === '/') return false
  const normalizedPath = pathFromQuery.startsWith('/') ? pathFromQuery : '/' + pathFromQuery
  const id = route.params.id as string
  const token = authStore.token || localStorage.getItem('auth_token')
  try {
    const response = await fetch(
      `/api/browse/filesystem/${id}/content?path=${encodeURIComponent(normalizedPath)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (!response.ok) return false
    const data = await response.json()
    const name = normalizedPath.split('/').filter(Boolean).pop() || normalizedPath
    const ext = name.split('.').pop()?.toLowerCase()
    const fileObj = { name, path: normalizedPath, type: 'file' }
    currentPreviewFile.value = fileObj
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || '')) {
      previewType.value = 'image'
      const base = `/api/browse/filesystem/${id}/download?path=${encodeURIComponent(normalizedPath)}`
      previewUrl.value = token ? `${base}&token=${encodeURIComponent(token)}` : base
    } else if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext || '')) {
      previewType.value = 'video'
      const base = `/api/browse/filesystem/${id}/download?path=${encodeURIComponent(normalizedPath)}`
      previewUrl.value = token ? `${base}&token=${encodeURIComponent(token)}` : base
    } else if (['txt', 'md', 'csv', 'log'].includes(ext || '')) {
      previewType.value = 'text'
      previewContent.value = data.content ?? ''
    } else if (ext === 'json') {
      previewType.value = 'json'
      previewContent.value = data.content ?? ''
    } else if (['xlsx', 'xls'].includes(ext || '')) {
      previewType.value = 'excel'
      previewContent.value = data.content ?? ''
      currentPreviewFile.value = {
        ...fileObj,
        excelInfo: { rows: data.rows, columns: data.columns }
      }
    } else if (ext === 'nc') {
      previewType.value = 'nc'
      currentPreviewFile.value = { name, path: normalizedPath, type: 'file', ncInfo: { loading: true } }
      try {
        const infoResponse = await fetch(`/api/browse/filesystem/${id}/nc/info?path=${encodeURIComponent(normalizedPath)}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const infoData = await infoResponse.json()
        currentPreviewFile.value.ncInfo = {
          loading: false,
          dimensions: infoData.data.dimensions,
          variables: infoData.data.variables,
          fileSize: infoData.data.file_size
        }
        
        const previewResponse = await fetch(`/api/browse/filesystem/${id}/nc/preview?path=${encodeURIComponent(normalizedPath)}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const previewData = await previewResponse.json()
        if (previewData.code === 200) {
          currentPreviewFile.value.ncImage = previewData.data.image
          currentPreviewFile.value.ncVariable = previewData.data.variable
          currentPreviewFile.value.ncStats = {
            min: previewData.data.min,
            max: previewData.data.max,
            mean: previewData.data.mean,
            shape: previewData.data.shape
          }
        }
      } catch (ncError) {
        console.error('NC文件预览失败:', ncError)
        currentPreviewFile.value.ncInfo = { loading: false, error: '预览失败' }
      }
    } else {
      previewType.value = 'unsupported'
    }
    currentPath.value = normalizedPath.replace(/\/[^/]+$/, '') || '/'
    showPreviewDialog.value = true
    return true
  } catch {
    return false
  }
}

function formatJson(jsonStr: string): string {
  try {
    const parsed = JSON.parse(jsonStr)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return jsonStr
  }
}

async function downloadFile(file: any) {
  try {
    loading.value = true
    const id = route.params.id as string
    
    // 使用fetch携带认证信息下载
    if (!authStore.isAuthenticated) {
      ElMessage.error('请先登录')
      return
    }
    
    const token = authStore.token || localStorage.getItem('auth_token')
    if (!token) {
      ElMessage.error('认证信息丢失，请重新登录')
      return
    }
    
    const downloadUrl = `/api/browse/filesystem/${id}/download?path=${encodeURIComponent(file.path)}`
    
    const response = await fetch(downloadUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`下载失败: ${response.status} ${response.statusText}`)
    }
    
    const blob = await response.blob()
    
    // 验证blob有效性
    if (!blob || blob.size === 0) {
      throw new Error('下载的文件为空或无效')
    }
    
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 清理URL对象
    setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 100)
    
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('❌ 文件系统浏览: 下载失败', error)
    ElMessage.error(error.message || '下载失败')
  } finally {
    loading.value = false
  }
}

async function handleFileAction({ action, file }: { action: string, file: any }) {
  switch (action) {
    case 'info':
      await showFileInfo(file)
      break
    case 'rename':
      await renameFile(file)
      break
    case 'delete':
      await deleteFile(file)
      break
  }
}

// 复制API链接
function copyApiLink(file: any) {
  try {
    const id = route.params.id as string
    const apiUrl = `${window.location.origin}/api/browse/filesystem/${id}/api?path=${encodeURIComponent(file.path)}`
    
    navigator.clipboard.writeText(apiUrl).then(() => {
      ElMessage.success('API链接已复制到剪贴板')
    }).catch(() => {
      // 降级方案
      const input = document.createElement('input')
      input.value = apiUrl
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      ElMessage.success('API链接已复制到剪贴板')
    })
  } catch (error) {
    console.error('复制API链接失败:', error)
    ElMessage.error('复制API链接失败')
  }
}

async function showFileInfo(file: any) {
  try {
    const id = route.params.id as string
    const response = await fetch(`/api/browse/filesystem/${id}/info?path=${encodeURIComponent(file.path)}`)
    selectedFileInfo.value = await response.json()
    showInfoDialog.value = true
  } catch (error) {
    ElMessage.error('获取文件信息失败')
  }
}

async function renameFile(file: any) {
  try {
    const newName = await ElMessageBox.prompt('请输入新文件名', '重命名', {
      inputValue: file.name,
      inputValidator: (value: string) => {
        if (!value) return '文件名不能为空'
        if (value === file.name) return '文件名未改变'
        return true
      }
    })
    
    const id = route.params.id as string
    const response = await fetch(`/api/browse/filesystem/${id}/rename`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        old_path: file.path,
        new_name: newName.value
      })
    })
    
    if (response.ok) {
      ElMessage.success('重命名成功')
      await refreshData()
    } else {
      throw new Error('重命名失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重命名失败')
    }
  }
}

async function deleteFile(file: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除 "${file.name}"？`,
      '删除确认',
      { type: 'warning' }
    )
    
    const id = route.params.id as string
    const response = await fetch(`/api/browse/filesystem/${id}/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: file.path })
    })
    
    if (response.ok) {
      ElMessage.success('删除成功')
      await refreshData()
    } else {
      throw new Error('删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 收藏夹功能
function loadFavorites() {
  const stored = localStorage.getItem(`favorites_${route.params.id}`)
  if (stored) {
    favorites.value = JSON.parse(stored)
  }
}

function addToFavorites() {
  const favorite = {
    path: currentPath.value,
    name: pathParts.value[pathParts.value.length - 1] || 'Root'
  }
  
  favorites.value.push(favorite)
  saveFavorites()
  ElMessage.success('已添加到收藏夹')
}

function removeFavorite(path: string) {
  const index = favorites.value.findIndex(fav => fav.path === path)
  if (index > -1) {
    favorites.value.splice(index, 1)
    saveFavorites()
  }
}

function saveFavorites() {
  localStorage.setItem(`favorites_${route.params.id}`, JSON.stringify(favorites.value))
}
</script>

<style scoped>
.filesystem-browser {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.breadcrumb-section {
  flex: 1;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quick-access {
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.favorites {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.favorite-tag {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  border-right: 1px solid #ebeef5;
  background: #fafafa;
  padding: 16px;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.path-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.current-path {
  font-family: monospace;
  background: #f0f2f5;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.file-stats {
  font-size: 14px;
  color: #666;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  /* padding: 16px; */
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.file-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.file-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.file-card.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.file-card.is-directory {
  background: #f8f9fa;
}

.file-icon-large {
  font-size: 48px;
  margin-bottom: 12px;
}

.file-info .file-name {
  font-weight: bold;
  margin-bottom: 4px;
  word-break: break-all;
}

.file-meta {
  font-size: 12px;
  color: #666;
}

.file-meta span {
  display: block;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  margin-bottom: 16px;
  color: #303133;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  cursor: pointer;
}

.file-name.is-link {
  color: #409eff;
}

.file-name.is-link:hover {
  text-decoration: underline;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

/* 性能提示样式 */
.performance-tip {
  padding: 8px 16px;
  background: #f0f9ff;
  border-bottom: 1px solid #e1f5fe;
}

.performance-alert {
  margin: 0;
}

.performance-alert .el-alert__content {
  font-size: 13px;
}

/* 分页组件样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  padding: 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

/* 文件图标颜色 */
.directory-icon {
  color: #409eff;
}

.image-icon {
  color: #67c23a;
}

.video-icon {
  color: #e6a23c;
}

.archive-icon {
  color: #f56c6c;
}

/* 预览样式 */
.file-preview {
  max-height: 600px;
  overflow-y: auto;
}

.text-preview pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
}

.image-preview {
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 500px;
}

.json-preview pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

/* Excel预览样式 */
.excel-preview {
  max-width: 100%;
}

.nc-preview {
  max-width: 100%;
}

.nc-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #909399;
  font-size: 14px;
}

.nc-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.nc-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 4px;
}

.nc-image {
  max-width: 100%;
  overflow: auto;
  text-align: center;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
}

.nc-image img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}

.nc-stats {
  margin: 8px 0;
}

.nc-dimensions {
  margin: 8px 0;
}

.nc-dimensions h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #303133;
}

.nc-variables {
  margin: 8px 0;
}

.nc-variables h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #303133;
}

.excel-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  padding: 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 4px 4px 0 0;
}

.excel-content {
  max-height: 600px;
  overflow: auto;
  border: 1px solid #e4e7ed;
  border-radius: 0 0 4px 4px;
  background: white;
}

.excel-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  margin: 0;
}

.excel-content :deep(table th) {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #606266;
  padding: 8px 12px;
  text-align: left;
  border-bottom: 2px solid #e4e7ed;
  border-right: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 10;
}

.excel-content :deep(table td) {
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
  border-right: 1px solid #ebeef5;
  color: #606266;
  vertical-align: top;
}

.excel-content :deep(table tr:nth-child(even)) {
  background-color: #fafafa;
}

.excel-content :deep(table tr:hover) {
  background-color: #f0f9ff;
}

/* 表格行样式 */
:deep(.directory-row) {
  background-color: #f8f9fa;
}

:deep(.directory-row:hover td) {
  background-color: #ecf5ff !important;
}

:deep(.el-breadcrumb__item.is-link) {
  cursor: pointer;
}

:deep(.el-breadcrumb__item.is-link .el-breadcrumb__inner:hover) {
  color: #409eff;
}
</style>
