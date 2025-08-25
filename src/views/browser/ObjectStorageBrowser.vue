<template>
  <div class="object-storage-browser">
    <div class="header">
      <div class="breadcrumb-section">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <router-link to="/datasources">数据源</router-link>
          </el-breadcrumb-item>
          <el-breadcrumb-item>{{ dataSource?.cname || dataSource?.name || '加载中...' }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentBucket || 'Buckets' }}</el-breadcrumb-item>
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

      <!-- 对象列表 -->
      <div v-else class="object-list">
        <div class="object-header">
          <div class="object-info">
            <div class="section-title">
              <el-icon><FolderOpened /></el-icon>
              {{ currentBucket }}
              <span v-if="currentPrefix">/ {{ currentPrefix }}</span>
            </div>
            <div class="object-stats">
              {{ filteredObjects.length }} 对象
              <span v-if="selectedObjects.length > 0">
                ({{ selectedObjects.length }} 选中)
              </span>
            </div>
          </div>
          
          <div class="object-actions">
            <el-button 
              type="text" 
              icon="ArrowLeft" 
              @click="goBack"
            >
              返回
            </el-button>
            
            <el-button
              v-if="selectedObjects.length > 0"
              type="danger"
              icon="Delete"
              @click="deleteSelectedObjects"
            >
              删除选中 ({{ selectedObjects.length }})
            </el-button>
          </div>
        </div>

        <!-- 对象表格/网格 -->
        <div class="object-content" v-loading="loading">
          <!-- 列表视图 -->
          <el-table
            v-if="viewMode === 'list'"
            :data="filteredObjects"
            @selection-change="handleSelectionChange"
            @row-dblclick="handleDoubleClick"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="key" label="名称" min-width="300">
              <template #default="{ row }">
                <div class="object-item">
                  <el-icon class="object-icon" :class="getObjectIconClass(row)">
                    <component :is="getObjectIcon(row)" />
                  </el-icon>
                  <span 
                    class="object-name" 
                    :class="{ 'is-folder': row.isFolder }"
                    @click="handleItemClick(row)"
                  >
                    {{ getDisplayName(row) }}
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="120" sortable>
              <template #default="{ row }">
                {{ row.isFolder ? '-' : formatFileSize(row.size) }}
              </template>
            </el-table-column>
            <el-table-column prop="storageClass" label="存储类型" width="120">
              <template #default="{ row }">
                <el-tag v-if="!row.isFolder" size="small" :type="getStorageClassType(row.storageClass)">
                  {{ row.storageClass }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="lastModified" label="修改时间" width="180" sortable>
              <template #default="{ row }">
                {{ row.isFolder ? '-' : formatDate(row.lastModified) }}
              </template>
            </el-table-column>
            <el-table-column prop="etag" label="ETag" width="100">
              <template #default="{ row }">
                <span v-if="!row.isFolder && row.etag" class="etag">
                  {{ row.etag.substring(0, 8) }}...
                </span>
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
          <div v-else class="object-grid">
            <div
              v-for="object in filteredObjects"
              :key="object.key"
              class="object-card"
              :class="{ 
                'is-selected': selectedObjects.includes(object),
                'is-folder': object.isFolder
              }"
              @click="handleItemClick(object, $event)"
              @dblclick="handleDoubleClick(object)"
            >
              <div class="object-icon-large">
                <el-icon :class="getObjectIconClass(object)">
                  <component :is="getObjectIcon(object)" />
                </el-icon>
              </div>
              <div class="object-info">
                <div class="object-name" :title="getDisplayName(object)">
                  {{ getDisplayName(object) }}
                </div>
                <div class="object-meta" v-if="!object.isFolder">
                  <span class="object-size">{{ formatFileSize(object.size) }}</span>
                  <span class="object-date">{{ formatDate(object.lastModified, true) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!loading && filteredObjects.length === 0" class="empty-state">
            <el-empty description="此目录为空" />
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination" v-if="totalObjects > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[50, 100, 200, 500]"
            :total="totalObjects"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
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
  Picture, VideoPlay, Lock
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

// 生命周期
onMounted(async () => {
  await loadDataSource()
  const bucket = route.query.bucket as string
  const prefix = route.query.prefix as string
  
  if (bucket) {
    currentBucket.value = bucket
    currentPrefix.value = prefix || ''
    await loadObjects()
  } else {
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
    } else {
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
    console.log('🔍 对象存储浏览: 开始加载数据源', id)
    
    const response = await dataSourceStore.fetchDataSourceById(id)
    dataSource.value = response.data
    console.log('✅ 对象存储浏览: 数据源加载成功', dataSource.value)
  } catch (error) {
    console.error('❌ 对象存储浏览: 数据源加载失败', error)
    ElMessage.error('加载数据源失败')
    
    // 如果API失败，尝试从当前数据源列表中找
    console.log('🔄 对象存储浏览: 尝试从当前列表中查找数据源')
    const currentList = dataSourceStore.dataSources
    console.log('📊 对象存储浏览: 当前数据源列表:', currentList)
    
    if (Array.isArray(currentList)) {
      const found = currentList.find(ds => ds.id === id)
      if (found) {
        dataSource.value = found
        console.log('✅ 对象存储浏览: 从列表中找到数据源', found)
        console.log('🏷️ 对象存储浏览: 数据源名称', found.cname || found.name)
      } else {
        console.log('❌ 对象存储浏览: 在数据源列表中未找到ID为', id, '的数据源')
      }
    } else {
      console.log('⚠️ 对象存储浏览: 数据源列表不是数组或为空:', currentList)
      
      // 如果数据源列表还未加载，尝试强制获取
      console.log('🔄 对象存储浏览: 尝试强制获取数据源列表')
      try {
        await dataSourceStore.fetchDataSources()
        const newList = dataSourceStore.dataSources
        if (Array.isArray(newList)) {
          const found = newList.find(ds => ds.id === id)
          if (found) {
            dataSource.value = found
            console.log('✅ 对象存储浏览: 强制获取后从列表中找到数据源', found)
          }
        }
      } catch (fetchError) {
        console.error('❌ 对象存储浏览: 强制获取数据源列表也失败:', fetchError)
      }
    }
  }
}

async function loadBuckets() {
  try {
    loading.value = true
    const id = route.params.id as string
    
    // TODO: 后端暂未实现buckets端点，使用模拟数据
    // 正式环境中应该调用 objectStorageApi.listBuckets(id)
    console.log('📂 对象存储浏览: 模拟buckets数据 (待后端实现)')
    
    buckets.value = [
      { name: 'default-bucket', createdDate: new Date(), region: 'us-east-1' },
      { name: 'backup-bucket', createdDate: new Date(), region: 'us-west-2' }
    ]
  } catch (error) {
    console.error('❌ 对象存储浏览: 加载存储桶列表失败', error)
    ElMessage.error('加载存储桶列表失败')
  } finally {
    loading.value = false
  }
}

async function loadObjects() {
  try {
    loading.value = true
    const id = route.params.id as string
    const params = {
      prefix: currentPrefix.value,
      max_keys: pageSize.value
    }
    
    const response = await objectStorageApi.listObjects(id, params)
    objects.value = response.data || []
    totalObjects.value = response.data?.length || 0
    console.log('🗂️ 对象存储浏览: 加载对象列表成功', objects.value)
  } catch (error) {
    console.error('❌ 对象存储浏览: 加载对象列表失败', error)
    ElMessage.error('加载对象列表失败')
  } finally {
    loading.value = false
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
    currentBucket.value = ''
    router.push({
      query: { bucket: undefined, prefix: undefined }
    })
  }
}

function handleItemClick(object: any, event?: Event) {
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
      router.push({
        query: { ...route.query, prefix: newPrefix }
      })
    } else {
      selectedObjects.value = [object]
    }
  }
}

function handleDoubleClick(object: any) {
  if (object.isFolder) {
    const newPrefix = object.key
    currentPrefix.value = newPrefix
    router.push({
      query: { ...route.query, prefix: newPrefix }
    })
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

function getObjectIcon(object: any) {
  if (object.isFolder) return FolderOpened
  
  const key = object.key.toLowerCase()
  if (/\.(jpg|jpeg|png|gif|bmp|webp)$/.test(key)) return Picture
  if (/\.(mp4|avi|mov|wmv|flv)$/.test(key)) return VideoPlay
  if (/\.(zip|rar|tar|gz)$/.test(key)) return Box
  
  return Document
}

function getObjectIconClass(object: any) {
  const classes = ['object-icon']
  if (object.isFolder) {
    classes.push('folder-icon')
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

function getStorageClassType(storageClass: string): string {
  switch (storageClass) {
    case 'STANDARD': return 'success'
    case 'STANDARD_IA': return 'warning'
    case 'GLACIER': return 'info'
    case 'DEEP_ARCHIVE': return 'danger'
    default: return ''
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
  try {
    const id = route.params.id as string
    const url = `/api/v1/browse/object-storage/${id}/download?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
    
    const link = document.createElement('a')
    link.href = url
    link.download = getDisplayName(object)
    link.click()
    
    ElMessage.success('开始下载')
  } catch (error) {
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
  overflow: hidden;
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

/* 对象列表样式 */
.object-list {
  display: flex;
  flex-direction: column;
  height: 100%;
}

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

.object-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.object-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.object-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.object-card.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.object-card.is-folder {
  background: #f8f9fa;
}

.object-icon-large {
  font-size: 48px;
  padding-bottom: 12px;
}

.object-info .object-name {
  font-weight: bold;
  padding-bottom: 4px;
  word-break: break-all;
}

.object-meta {
  font-size: 12px;
  color: #666;
}

.object-meta span {
  display: block;
}

.object-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.object-name {
  cursor: pointer;
}

.object-name.is-folder {
  color: #409eff;
}

.object-name.is-folder:hover {
  text-decoration: underline;
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
