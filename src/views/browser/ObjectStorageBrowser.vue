<template>
  <div class="object-storage-browser">
    <div class="header">
      <div class="breadcrumb-section">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <router-link to="/datasources">数据源</router-link>
          </el-breadcrumb-item>
          <el-breadcrumb-item>{{ dataSource?.cname || dataSource?.name || '加载中...' }}</el-breadcrumb-item>
          <el-breadcrumb-item>
            {{ currentBucket || (dataSource?.config?.bucket ? `存储桶: ${dataSource.config.bucket}` : 'Buckets') }}
          </el-breadcrumb-item>
          <el-breadcrumb-item 
            v-for="(part, index) in prefixParts" 
            :key="index"
            :class="{ 'is-link': index < prefixParts.length - 1 }"
            @click="navigateToPrefix(index)"
          >
            {{ part }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      
      <div class="toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索对象..."
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
        
        <el-upload
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :show-file-list="false"
          :before-upload="beforeUpload"
          multiple
        >
          <el-button type="primary" icon="Upload">上传</el-button>
        </el-upload>
        
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

    <div class="content">
      <!-- Bucket列表 -->
      <div v-if="!currentBucket" class="bucket-list">
        <div class="section-title">
          <el-icon><Box /></el-icon>
          存储桶列表
        </div>
        
        <div class="buckets" v-loading="loading">
          <div
            v-for="bucket in buckets"
            :key="bucket.name"
            class="bucket-card"
            @click="selectBucket(bucket.name)"
          >
            <div class="bucket-icon">
              <el-icon><Box /></el-icon>
            </div>
            <div class="bucket-info">
              <div class="bucket-name">{{ bucket.name }}</div>
              <div class="bucket-meta">
                <span>{{ bucket.objectCount }} 对象</span>
                <span>{{ formatFileSize(bucket.size) }}</span>
                <span>{{ formatDate(bucket.creationDate) }}</span>
              </div>
            </div>
            <div class="bucket-actions">
              <el-dropdown @command="handleBucketAction">
                <el-button icon="More" circle size="small" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'info', bucket: bucket.name }">
                      <el-icon><InfoFilled /></el-icon>
                      详细信息
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'policy', bucket: bucket.name }">
                      <el-icon><Lock /></el-icon>
                      访问策略
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
        
        <div v-if="!loading && buckets.length === 0" class="empty-state">
          <el-empty description="没有找到存储桶" />
        </div>
      </div>

      <!-- 对象浏览主内容 -->
      <div v-else class="filesystem-layout">
        <!-- 侧边栏 - 目录树导航 -->
        <div class="sidebar" v-if="showSidebar">
          <div class="section-title">
            <el-icon><FolderOpened /></el-icon>
            {{ currentBucket }} 目录结构
          </div>
          
          <el-tree
            :data="directoryTree"
            :props="{ label: 'name', children: 'children', isLeaf: 'isLeaf' }"
            @node-click="handleTreeNodeClick"
            :expand-on-click-node="false"
            :highlight-current="true"
            node-key="path"
            :current-node-key="currentPrefix"
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
          <!-- 对象操作栏 -->
          <div class="action-bar">
            <div class="path-info">
              <el-button 
                v-if="canGoBack"
                type="text" 
                icon="ArrowLeft" 
                size="small"
                @click="goBack"
                :title="getBackButtonTooltip()"
              >
                返回
              </el-button>
              <span class="current-path">{{ currentBucket }}{{ currentPrefix ? '/' + currentPrefix : '' }}</span>
            </div>
            
            <div class="object-stats">
              <span>{{ filteredObjects.length }} 项</span>
              <span v-if="selectedObjects.length > 0">
                ({{ selectedObjects.length }} 选中)
              </span>
            </div>
            
            <div class="object-actions">
              <el-button
                v-if="selectedObjects.length > 0"
                type="danger"
                icon="Delete"
                size="small"
                @click="deleteSelectedObjects"
              >
                删除选中 ({{ selectedObjects.length }})
              </el-button>
            </div>
          </div>

          <!-- 对象列表 -->
          <div class="object-list" v-loading="loading">
            <!-- 列表视图 -->
            <el-table
              v-if="viewMode === 'list'"
              :data="filteredObjects"
              @selection-change="handleSelectionChange"
              @row-dblclick="handleDoubleClick"
              :row-class-name="getRowClassName"
            >
              <el-table-column type="selection" width="55" />
              <el-table-column prop="key" label="名称" min-width="300">
                <template #default="{ row }">
                  <div class="file-item">
                    <el-icon class="file-icon" :class="getFileIconClass(row)">
                      <component :is="getFileIcon(row)" />
                    </el-icon>
                    <span 
                      class="file-name" 
                      :class="{ 'is-link': row.isFolder }"
                      @click="handleItemClick(row)"
                    >
                      {{ getDisplayName(row) }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="size" label="大小" width="120" sortable>
                <template #default="{ row }">
                  {{ formatFileSize(row.size) }}
                </template>
              </el-table-column>
              <el-table-column prop="contentType" label="类型" width="150">
                <template #default="{ row }">
                  {{ row.isFolder ? '文件夹' : getFileType(row) }}
                </template>
              </el-table-column>
              <el-table-column prop="lastModified" label="修改时间" width="180" sortable>
                <template #default="{ row }">
                  {{ row.isFolder ? '-' : formatDate(row.lastModified) }}
                </template>
              </el-table-column>
              <el-table-column prop="storageClass" label="存储类" width="120">
                <template #default="{ row }">
                  <el-tag v-if="!row.isFolder" size="small" :type="getStorageClassType(row.storageClass)">
                    {{ row.storageClass || 'STANDARD' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button-group size="small" v-if="!row.isFolder">
                    <el-button 
                      icon="View" 
                      @click="previewObject(row)"
                      :disabled="!canPreview(row)"
                    >
                      预览
                    </el-button>
                    <el-button 
                      icon="Download" 
                      @click="downloadObject(row)"
                    >
                      下载
                    </el-button>
                    <el-dropdown @command="handleObjectAction">
                      <el-button icon="More" />
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item :command="{ action: 'info', object: row }">
                            <el-icon><InfoFilled /></el-icon>
                            详细信息
                          </el-dropdown-item>
                          <el-dropdown-item :command="{ action: 'copy', object: row }">
                            <el-icon><CopyDocument /></el-icon>
                            复制链接
                          </el-dropdown-item>
                          <el-dropdown-item 
                            :command="{ action: 'delete', object: row }"
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
                v-for="object in filteredObjects"
                :key="object.key"
                class="file-card"
                :class="{ 
                  'is-selected': selectedObjects.includes(object),
                  'is-directory': object.isFolder
                }"
                @click="handleItemClick(object, $event)"
                @dblclick="handleDoubleClick(object)"
              >
                <div class="file-icon-large">
                  <el-icon :class="getFileIconClass(object)">
                    <component :is="getFileIcon(object)" />
                  </el-icon>
                </div>
                <div class="file-info">
                  <div class="file-name" :title="getDisplayName(object)">
                    {{ getDisplayName(object) }}
                  </div>
                  <div class="file-meta" v-if="!object.isFolder">
                    <span class="file-size">{{ formatFileSize(object.size) }}</span>
                    <span class="file-date">{{ formatDate(object.lastModified, true) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="!loading && filteredObjects.length === 0" class="empty-state">
              <el-empty description="此目录为空" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="currentPreviewObject.key"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="object-preview">
        <!-- 图片预览 -->
        <div v-if="previewType === 'image'" class="image-preview">
          <img :src="previewUrl" :alt="currentPreviewObject.key" />
        </div>
        
        <!-- 文本预览 -->
        <div v-else-if="previewType === 'text'" class="text-preview">
          <pre>{{ previewContent }}</pre>
        </div>
        
        <!-- JSON预览 -->
        <div v-else-if="previewType === 'json'" class="json-preview">
          <pre>{{ formatJson(previewContent) }}</pre>
        </div>
        
        <!-- 其他类型 -->
        <div v-else class="unsupported-preview">
          <el-result
            icon="warning"
            title="预览不支持"
            sub-title="此文件类型暂不支持在线预览"
          >
            <template #extra>
              <el-button type="primary" @click="downloadObject(currentPreviewObject)">
                下载查看
              </el-button>
            </template>
          </el-result>
        </div>
      </div>
    </el-dialog>

    <!-- 对象详情对话框 -->
    <el-dialog v-model="showInfoDialog" title="对象详情" width="600px">
      <el-descriptions :column="2" border v-if="selectedObjectInfo">
        <el-descriptions-item label="键名" :span="2">{{ selectedObjectInfo.key }}</el-descriptions-item>
        <el-descriptions-item label="大小">{{ formatFileSize(selectedObjectInfo.size) }}</el-descriptions-item>
        <el-descriptions-item label="存储类型">{{ selectedObjectInfo.storageClass }}</el-descriptions-item>
        <el-descriptions-item label="内容类型">{{ selectedObjectInfo.contentType }}</el-descriptions-item>
        <el-descriptions-item label="ETag">{{ selectedObjectInfo.etag }}</el-descriptions-item>
        <el-descriptions-item label="最后修改">{{ formatDate(selectedObjectInfo.lastModified) }}</el-descriptions-item>
        <el-descriptions-item label="版本ID">{{ selectedObjectInfo.versionId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="服务器端加密" :span="2">
          {{ selectedObjectInfo.serverSideEncryption || '无' }}
        </el-descriptions-item>
      </el-descriptions>
      
      <!-- 元数据 -->
      <div v-if="selectedObjectInfo.metadata && Object.keys(selectedObjectInfo.metadata).length > 0" 
           style="margin-top: 20px;">
        <h4>元数据</h4>
        <el-table :data="formatMetadata(selectedObjectInfo.metadata)" size="small">
          <el-table-column prop="key" label="键" width="200" />
          <el-table-column prop="value" label="值" />
        </el-table>
      </div>
    </el-dialog>

    <!-- Bucket详情对话框 -->
    <el-dialog v-model="showBucketInfoDialog" title="存储桶详情" width="500px">
      <el-descriptions :column="1" border v-if="selectedBucketInfo">
        <el-descriptions-item label="名称">{{ selectedBucketInfo.name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(selectedBucketInfo.creationDate) }}</el-descriptions-item>
        <el-descriptions-item label="区域">{{ selectedBucketInfo.region || '-' }}</el-descriptions-item>
        <el-descriptions-item label="对象数量">{{ selectedBucketInfo.objectCount }}</el-descriptions-item>
        <el-descriptions-item label="总大小">{{ formatFileSize(selectedBucketInfo.size) }}</el-descriptions-item>
        <el-descriptions-item label="版本控制">
          <el-tag :type="selectedBucketInfo.versioning ? 'success' : 'info'">
            {{ selectedBucketInfo.versioning ? '已启用' : '未启用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="访问日志">
          <el-tag :type="selectedBucketInfo.logging ? 'success' : 'info'">
            {{ selectedBucketInfo.logging ? '已启用' : '未启用' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Box, FolderOpened, Document, List, Grid, Search, Refresh, Upload,
  ArrowLeft, Delete, View, Download, More, InfoFilled, CopyDocument,
  Picture, VideoPlay, Lock, Folder
} from '@element-plus/icons-vue'
import { useDataSourceStore } from '@/stores/datasource'
import { objectStorageApi } from '@/api/datasource'

const route = useRoute()
const router = useRouter()
const dataSourceStore = useDataSourceStore()

// 响应式数据
const loading = ref(false)
const dataSource = ref(null)
const buckets = ref([])
const currentBucket = ref('')
const currentPrefix = ref('')
const objects = ref([])
const searchQuery = ref('')
const viewMode = ref('list')
const selectedObjects = ref([])
const currentPage = ref(1)
const pageSize = ref(100)
const totalObjects = ref(0)

// 新增文件系统风格的数据
const showSidebar = ref(true)
const directoryTree = ref([])
const favorites = ref([])  // 收藏夹功能（可选）

// 预览相关
const showPreviewDialog = ref(false)
const currentPreviewObject = ref({})
const previewContent = ref('')
const previewUrl = ref('')
const previewType = ref('')

// 详情对话框
const showInfoDialog = ref(false)
const selectedObjectInfo = ref(null)
const showBucketInfoDialog = ref(false)
const selectedBucketInfo = ref(null)

// 上传相关
const uploadUrl = computed(() => {
  if (!currentBucket.value) return ''
  return `/api/v1/browse/object-storage/${route.params.id}/upload`
})

const uploadHeaders = computed(() => ({}))

const uploadData = computed(() => ({
  bucket: currentBucket.value,
  prefix: currentPrefix.value
}))

// 计算属性
const prefixParts = computed(() => {
  if (!currentPrefix.value) return []
  return currentPrefix.value.split('/').filter(part => part)
})

const filteredObjects = computed(() => {
  if (!searchQuery.value) return objects.value
  const query = searchQuery.value.toLowerCase()
  return objects.value.filter(object => 
    object.key.toLowerCase().includes(query)
  )
})

// 计算是否可以返回
const canGoBack = computed(() => {
  // 如果在文件夹中，总是可以返回
  if (currentPrefix.value) return true
  
  // 如果在存储桶根目录，且数据源没有配置特定bucket，可以返回到buckets列表
  if (!currentPrefix.value && !dataSource.value?.config?.bucket) return true
  
  // 其他情况（在特定bucket的根目录）不能返回
  return false
})

// 生命周期
onMounted(async () => {
  await loadDataSource()
  
  const bucket = route.query.bucket as string
  const prefix = route.query.prefix as string
  const configuredBucket = dataSource.value?.config?.bucket
  
  // 优先使用URL查询参数中的bucket
  if (bucket) {
    currentBucket.value = bucket
    currentPrefix.value = prefix || ''
    await loadObjects()
  } 
  // 如果URL中没有bucket，检查数据源配置中是否指定了bucket
  else if (configuredBucket) {
    currentBucket.value = configuredBucket
    currentPrefix.value = ''
    // 更新URL以反映当前状态
    router.push({
      query: { ...route.query, bucket: currentBucket.value }
    })
    await loadObjects()
  } 
  // 如果既没有URL参数也没有配置中的bucket，显示所有buckets
  else {
    await loadBuckets()
  }
})

// 监听路由变化
watch(() => route.query, async (newQuery) => {
  const bucket = newQuery.bucket as string
  const prefix = newQuery.prefix as string
  
  if (bucket !== currentBucket.value) {
    currentBucket.value = bucket || ''
    if (bucket) {
      currentPrefix.value = prefix || ''
      await loadObjects()
    } 
    // 如果URL中没有bucket，检查数据源配置中是否指定了bucket
    else if (dataSource.value?.config?.bucket) {
      currentBucket.value = dataSource.value.config.bucket
      currentPrefix.value = ''
      await loadObjects()
    } 
    else {
      await loadBuckets()
    }
  } else if (prefix !== currentPrefix.value) {
    currentPrefix.value = prefix || ''
    await loadObjects()
  }
})

// 方法
async function loadDataSource() {
  try {
    const id = route.params.id as string
    const response = await dataSourceStore.fetchDataSourceById(id)
    dataSource.value = response
  } catch (error) {
    console.error('对象存储浏览: 数据源加载失败', error)
    ElMessage.error('加载数据源失败')
    
    // 如果API失败，尝试从当前数据源列表中找
    const currentList = dataSourceStore.dataSources
    
    if (Array.isArray(currentList)) {
      const found = currentList.find(ds => ds.id === id)
      if (found) {
        dataSource.value = found
      }
    } else {
      // 如果数据源列表还未加载，尝试强制获取
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
        console.error('对象存储浏览: 强制获取数据源列表也失败:', fetchError)
      }
    }
  }
}

async function loadBuckets() {
  try {
    loading.value = true
    const id = route.params.id as string
    
    const response = await objectStorageApi.listBuckets(id)
    const data = response.data || response
    
    if (Array.isArray(data)) {
      buckets.value = data.map(bucket => ({
        name: bucket.name,
        createdDate: bucket.creation_date ? new Date(bucket.creation_date) : new Date(),
        region: bucket.region || 'us-east-1'
      }))
    } else {
      buckets.value = []
    }
  } catch (error) {
    console.error('对象存储浏览: 加载存储桶列表失败', error)
    ElMessage.error('加载存储桶列表失败')
    buckets.value = []
  } finally {
    loading.value = false
  }
}

async function loadObjects() {
  if (!currentBucket.value) {
    objects.value = []
    totalObjects.value = 0
    return
  }
  
  try {
    loading.value = true
    const id = route.params.id as string
    
    // 确保prefix格式正确：如果不为空且不以/结尾，则添加/
    let prefix = currentPrefix.value
    if (prefix && !prefix.endsWith('/')) {
      prefix = prefix + '/'
    }
    
    const params = {
      prefix: prefix,
      delimiter: '/', // 添加delimiter参数以支持文件夹结构
      max_keys: pageSize.value
    }
    
    const response = await objectStorageApi.listObjects(id, currentBucket.value, params)
    const data = response.data || response
    
    if (Array.isArray(data)) {
      objects.value = data.map(obj => ({
        key: obj.key,
        size: obj.size,
        lastModified: obj.last_modified || '',
        etag: obj.etag,
        contentType: obj.content_type || 'application/octet-stream',
        isFolder: obj.is_dir || false,
        metadata: obj.metadata || {}
      }))
      totalObjects.value = objects.value.length
      
      // 更新目录树（如果这是根目录的话）
      if (!currentPrefix.value) {
        await initializeDirectoryTree()
      }
    } else {
      objects.value = []
      totalObjects.value = 0
    }
  } catch (error) {
    console.error('对象存储浏览: 加载对象列表失败', error)
    ElMessage.error('加载对象列表失败')
    objects.value = []
    totalObjects.value = 0
  } finally {
    loading.value = false
  }
}

// 初始化目录树
async function initializeDirectoryTree() {
  try {
    const id = route.params.id as string
    
    // 获取根目录的所有文件夹
    const response = await objectStorageApi.listObjects(id, currentBucket.value, {
      prefix: '',
      delimiter: '/',
      max_keys: 1000
    })
    
    const data = response.data || response
    
    if (Array.isArray(data)) {
      const rootFolders = data
        .filter(obj => obj.is_dir)
        .map(obj => {
          const pathParts = obj.key.split('/').filter(p => p)
          const name = pathParts[0] || obj.key
          return {
            name: name,
            path: obj.key.endsWith('/') ? obj.key.slice(0, -1) : obj.key,
            type: 'directory',
            children: null,
            isLeaf: false
          }
        })
      
      directoryTree.value = rootFolders
    }
  } catch (error) {
    console.error('初始化目录树失败:', error)
  }
}

function selectBucket(bucketName: string) {
  currentBucket.value = bucketName
  currentPrefix.value = ''
  router.push({
    query: { ...route.query, bucket: bucketName, prefix: undefined }
  })
}

function navigateToPrefix(index: number) {
  const newPrefix = prefixParts.value.slice(0, index + 1).join('/')
  currentPrefix.value = newPrefix
  router.push({
    query: { ...route.query, prefix: newPrefix }
  })
}

function goBack() {
  if (currentPrefix.value) {
    // 在文件夹中，返回上一级文件夹
    const parts = prefixParts.value
    if (parts.length > 1) {
      const newPrefix = parts.slice(0, -1).join('/')
      currentPrefix.value = newPrefix
      router.push({
        query: { ...route.query, prefix: newPrefix }
      })
    } else {
      currentPrefix.value = ''
      router.push({
        query: { ...route.query, prefix: undefined }
      })
    }
  } else {
    // 在存储桶根目录中
    // 如果数据源配置了特定的bucket，不允许返回到buckets列表
    if (dataSource.value?.config?.bucket) {
      ElMessage.info('当前数据源已配置为特定存储桶，无法返回')
      return
    }
    
    // 如果没有配置特定bucket，可以返回到buckets列表
    currentBucket.value = ''
    router.push({
      query: { bucket: undefined, prefix: undefined }
    })
  }
}

function getBackButtonTooltip(): string {
  if (currentPrefix.value) {
    return '返回上级目录'
  } else if (dataSource.value?.config?.bucket) {
    return '已配置特定存储桶，无法返回'
  } else {
    return '返回存储桶列表'
  }
}

async function handleItemClick(object: any, event?: Event) {
  
  if (event?.ctrlKey || event?.metaKey) {
    // 多选
    const index = selectedObjects.value.findIndex(o => o.key === object.key)
    if (index > -1) {
      selectedObjects.value.splice(index, 1)
    } else {
      selectedObjects.value.push(object)
    }
  } else {
    if (object.isFolder) {
      const newPrefix = object.key
      currentPrefix.value = newPrefix
      
      // 更新URL
      router.push({
        query: { ...route.query, prefix: newPrefix }
      })
      
      // 直接刷新数据，不依赖路由监听
      await loadObjects()
    } else {
      selectedObjects.value = [object]
    }
  }
}

async function handleDoubleClick(object: any) {
  if (object.isFolder) {
    const newPrefix = object.key
    currentPrefix.value = newPrefix
    
    // 更新URL
    router.push({
      query: { ...route.query, prefix: newPrefix }
    })
    
    // 直接刷新数据，不依赖路由监听
    await loadObjects()
  } else {
    previewObject(object)
  }
}

function handleSelectionChange(selection: any[]) {
  selectedObjects.value = selection
}

function handleSearch() {
  // 搜索功能已通过计算属性实现
}

async function refreshData() {
  if (currentBucket.value) {
    await loadObjects()
  } else {
    await loadBuckets()
  }
}

function getDisplayName(object: any): string {
  if (object.isFolder) {
    return object.key.split('/').filter(p => p).pop() + '/'
  }
  return object.key.split('/').pop()
}

// 文件图标和样式
function getFileIcon(object: any) {
  if (object.isFolder) return FolderOpened
  
  const key = object.key.toLowerCase()
  if (/\.(jpg|jpeg|png|gif|bmp|webp)$/.test(key)) return Picture
  if (/\.(mp4|avi|mov|wmv|flv)$/.test(key)) return VideoPlay
  if (/\.(zip|rar|tar|gz)$/.test(key)) return Box
  
  return Document
}

function getFileIconClass(object: any) {
  const classes = ['file-icon']
  if (object.isFolder) {
    classes.push('directory-icon')
  } else {
    const key = object.key.toLowerCase()
    if (/\.(jpg|jpeg|png|gif|bmp|webp)$/.test(key)) {
      classes.push('image-icon')
    } else if (/\.(mp4|avi|mov|wmv|flv)$/.test(key)) {
      classes.push('video-icon')
    } else if (/\.(zip|rar|tar|gz)$/.test(key)) {
      classes.push('archive-icon')
    }
  }
  return classes.join(' ')
}

// 保持兼容性的别名
const getObjectIcon = getFileIcon
const getObjectIconClass = getFileIconClass

function getFileType(object: any): string {
  if (object.isFolder) return '文件夹'
  if (object.contentType) {
    // 简化MIME类型显示
    const mimeType = object.contentType.toLowerCase()
    if (mimeType.startsWith('image/')) return '图片'
    if (mimeType.startsWith('video/')) return '视频'
    if (mimeType.startsWith('audio/')) return '音频'
    if (mimeType.startsWith('text/')) return '文本'
    if (mimeType.includes('json')) return 'JSON'
    if (mimeType.includes('xml')) return 'XML'
    if (mimeType.includes('pdf')) return 'PDF'
    if (mimeType.includes('zip') || mimeType.includes('archive')) return '压缩包'
  }
  
  // 基于文件扩展名推断
  const key = object.key.toLowerCase()
  if (/\.(jpg|jpeg|png|gif|bmp|webp)$/.test(key)) return '图片'
  if (/\.(mp4|avi|mov|wmv|flv)$/.test(key)) return '视频'
  if (/\.(mp3|wav|flac|aac)$/.test(key)) return '音频'
  if (/\.(txt|md|log)$/.test(key)) return '文本'
  if (/\.json$/.test(key)) return 'JSON'
  if (/\.xml$/.test(key)) return 'XML'
  if (/\.pdf$/.test(key)) return 'PDF'
  if (/\.(zip|rar|tar|gz|7z)$/.test(key)) return '压缩包'
  
  return '文件'
}

function getRowClassName(row: any): string {
  if (row.row.isFolder) return 'folder-row'
  return ''
}

// 侧边栏树形导航相关方法
async function handleTreeNodeClick(data: any) {
  // 确保路径以 / 结尾，与MinIO的前缀格式保持一致
  const targetPath = data.path.endsWith('/') ? data.path : data.path + '/'
  const currentPath = currentPrefix.value.endsWith('/') ? currentPrefix.value : currentPrefix.value + '/'
  
  if (targetPath !== currentPath) {
    currentPrefix.value = data.path
    
    // 更新URL
    router.push({
      query: { ...route.query, prefix: data.path || undefined }
    })
    
    // 直接刷新主内容区数据
    await loadObjects()
  }
}

async function loadTreeNode(node: any, resolve: any) {
  try {
    const id = route.params.id as string
    // 确保prefix格式正确：如果不是空的，应该以/结尾
    let prefix = node.data?.path || ''
    if (prefix && !prefix.endsWith('/')) {
      prefix = prefix + '/'
    }
    

    
    const response = await objectStorageApi.listObjects(id, currentBucket.value, {
      prefix: prefix,
      delimiter: '/',
      max_keys: 1000
    })
    
    const data = response.data || response
    
    if (Array.isArray(data)) {
      const folders = data
        .filter(obj => obj.is_dir)
        .map(obj => {
          const pathParts = obj.key.split('/').filter(p => p)
          const name = pathParts[pathParts.length - 1] || obj.key
          // 保存为不带末尾斜杠的路径，但确保包含完整路径
          const cleanPath = obj.key.endsWith('/') ? obj.key.slice(0, -1) : obj.key
          return {
            name: name,
            path: cleanPath,
            type: 'directory',
            children: null,
            isLeaf: false
          }
        })
      
      resolve(folders)
    } else {
      resolve([])
    }
  } catch (error) {
    console.error('加载目录树节点失败:', error)
    resolve([])
  }
}

function getStorageClassType(storageClass: string): string {
  if (!storageClass) return 'info' // 处理未定义或空值情况
  
  switch (storageClass) {
    case 'STANDARD': return 'success'
    case 'STANDARD_IA': return 'warning'
    case 'GLACIER': return 'info'
    case 'DEEP_ARCHIVE': return 'danger'
    default: return 'info' // 默认返回有效的type值，而不是空字符串
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
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

function canPreview(object: any): boolean {
  const key = object.key.toLowerCase()
  const textExts = /\.(txt|md|json|xml|csv|log)$/
  const imageExts = /\.(jpg|jpeg|png|gif|bmp|webp)$/
  
  return textExts.test(key) || imageExts.test(key)
}

async function previewObject(object: any) {
  try {
    loading.value = true
    currentPreviewObject.value = object
    
    const id = route.params.id as string
    const key = object.key.toLowerCase()
    
    if (/\.(jpg|jpeg|png|gif|bmp|webp)$/.test(key)) {
      previewType.value = 'image'
      previewUrl.value = `/api/v1/browse/object-storage/${id}/preview?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
    } else if (/\.(txt|md|csv|log)$/.test(key)) {
      previewType.value = 'text'
      const response = await fetch(`/api/v1/browse/object-storage/${id}/content?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`)
      previewContent.value = await response.text()
    } else if (/\.json$/.test(key)) {
      previewType.value = 'json'
      const response = await fetch(`/api/v1/browse/object-storage/${id}/content?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`)
      previewContent.value = await response.text()
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

function formatJson(jsonStr: string): string {
  try {
    const parsed = JSON.parse(jsonStr)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return jsonStr
  }
}

async function downloadObject(object: any) {
  if (!currentBucket.value) {
    ElMessage.error('请先选择存储桶')
    return
  }
  
  try {
    const id = route.params.id as string
    const blob = await objectStorageApi.downloadObject(id, currentBucket.value, object.key)
    
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = getDisplayName(object)
    link.click()
    
    // 清理URL对象
    setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 100)
    
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('❌ 对象存储浏览: 下载失败', error)
    ElMessage.error('下载失败')
  }
}

async function handleObjectAction({ action, object }: { action: string, object: any }) {
  switch (action) {
    case 'info':
      await showObjectInfo(object)
      break
    case 'copy':
      await copyObjectUrl(object)
      break
    case 'delete':
      await deleteObject(object)
      break
  }
}

async function showObjectInfo(object: any) {
  try {
    const id = route.params.id as string
    const response = await fetch(`/api/v1/browse/object-storage/${id}/info?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`)
    selectedObjectInfo.value = await response.json()
    showInfoDialog.value = true
  } catch (error) {
    ElMessage.error('获取对象信息失败')
  }
}

async function copyObjectUrl(object: any) {
  try {
    const id = route.params.id as string
    const url = `/api/v1/browse/object-storage/${id}/url?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
    const response = await fetch(url)
    const data = await response.json()
    
    await navigator.clipboard.writeText(data.url)
    ElMessage.success('链接已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制链接失败')
  }
}

async function deleteObject(object: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除对象 "${object.key}"？`,
      '删除确认',
      { type: 'warning' }
    )
    
    const id = route.params.id as string
    const response = await fetch(`/api/v1/browse/object-storage/${id}/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bucket: currentBucket.value,
        keys: [object.key]
      })
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

async function deleteSelectedObjects() {
  if (selectedObjects.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedObjects.value.length} 个对象？`,
      '批量删除确认',
      { type: 'warning' }
    )
    
    const id = route.params.id as string
    const keys = selectedObjects.value.map(obj => obj.key)
    
    const response = await fetch(`/api/v1/browse/object-storage/${id}/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bucket: currentBucket.value,
        keys
      })
    })
    
    if (response.ok) {
      ElMessage.success('删除成功')
      selectedObjects.value = []
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

async function handleBucketAction({ action, bucket }: { action: string, bucket: string }) {
  switch (action) {
    case 'info':
      await showBucketInfo(bucket)
      break
    case 'policy':
      ElMessage.info('访问策略功能开发中')
      break
  }
}

async function showBucketInfo(bucketName: string) {
  try {
    const id = route.params.id as string
    const response = await fetch(`/api/v1/browse/object-storage/${id}/bucket-info?bucket=${bucketName}`)
    selectedBucketInfo.value = await response.json()
    showBucketInfoDialog.value = true
  } catch (error) {
    ElMessage.error('获取存储桶信息失败')
  }
}

function formatMetadata(metadata: Record<string, any>): Array<{key: string, value: string}> {
  return Object.entries(metadata).map(([key, value]) => ({
    key,
    value: String(value)
  }))
}

function handleSizeChange(size: number) {
  pageSize.value = size
  loadObjects()
}

function handleCurrentChange(page: number) {
  currentPage.value = page
  loadObjects()
}

// 上传相关
function beforeUpload(file: File) {
  const isLt100M = file.size / 1024 / 1024 < 100
  if (!isLt100M) {
    ElMessage.error('文件大小不能超过 100MB')
  }
  return isLt100M
}

function handleUploadSuccess(response: any, file: any) {
  ElMessage.success(`${file.name} 上传成功`)
  refreshData()
}

function handleUploadError(error: any, file: any) {
  ElMessage.error(`${file.name} 上传失败`)
}
</script>

<style scoped>
/* 样式与文件系统浏览器类似，但针对对象存储做了调整 */
.object-storage-browser {
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

.content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 文件系统风格布局 - 与FilesystemBrowser保持完全一致 */
.filesystem-layout {
  display: flex;
  flex: 1;
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

/* 操作栏样式 - 与FilesystemBrowser保持一致 */
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

.object-stats {
  font-size: 14px;
  color: #666;
}

.object-actions {
  display: flex;
  gap: 8px;
}

/* 对象列表样式 - 与FilesystemBrowser保持一致 */
.object-list {
  flex: 1;
  overflow: auto; /* 支持垂直和水平滚动 */
  /* padding: 16px; */ /* 移除padding，与文件系统浏览器一致 */
}

/* Bucket列表样式 */
.bucket-list {
  padding: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  padding-bottom: 24px;
  color: #303133;
  font-size: 18px;
}

.buckets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.bucket-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 16px;
}

.bucket-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
  transform: translateY(-2px);
}

.bucket-icon {
  font-size: 32px;
  color: #409eff;
}

.bucket-info {
  flex: 1;
}

.bucket-name {
  font-size: 16px;
  font-weight: bold;
  padding-bottom: 8px;
}

.bucket-meta {
  font-size: 14px;
  color: #666;
  display: flex;
  gap: 16px;
}

.bucket-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.bucket-card:hover .bucket-actions {
  opacity: 1;
}

/* 对象列表容器样式 */

.object-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.object-info .section-title {
  padding-bottom: 4px;
  font-size: 16px;
}

.object-stats {
  font-size: 14px;
  color: #666;
}

.object-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.object-content {
  flex: 1;
  padding: 16px 24px;
  overflow-y: auto;
}

/* 文件网格样式 - 与文件系统浏览器完全一致 */
.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  padding: 16px;
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

/* 文件项样式 */
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

/* 树形节点样式 */
.tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 表格行样式 */
.folder-row {
  background-color: #f8f9fa;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  padding: 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.etag {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

/* 图标颜色 */
.folder-icon {
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
.object-preview {
  max-height: 600px;
  overflow-y: auto;
}

.image-preview {
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 500px;
}

.text-preview pre,
.json-preview pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
}

:deep(.el-breadcrumb__item.is-link) {
  cursor: pointer;
}

:deep(.el-breadcrumb__item.is-link .el-breadcrumb__inner:hover) {
  color: #409eff;
}
</style>
