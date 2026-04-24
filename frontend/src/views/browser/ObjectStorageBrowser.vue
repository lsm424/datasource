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
          
          <!-- 性能提示 -->
          <div class="performance-tip" v-if="totalObjects > 100">
            <el-alert
              :title="`此目录包含 ${totalObjects} 个对象，建议使用分页浏览以提高性能`"
              type="info"
              :closable="false"
              show-icon
              class="performance-alert"
            />
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
              <el-table-column label="操作" width="240" fixed="right">
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
                      icon="ChatDotRound" 
                      @click="openAnalyze(row)"
                    >
                      分析
                    </el-button>
                    <el-button 
                      icon="Download" 
                      @click="downloadObject(row)"
                    >
                      下载
                    </el-button>
                    <el-button 
                      icon="Link" 
                      @click="copyApiLink(row)"
                      title="复制API链接"
                    >
                      API
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
        
        <!-- 分页组件 -->
        <div class="pagination-container" v-if="totalObjects > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100, 200, 500]"
            :total="totalObjects"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>
    </div>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="`预览: ${currentPreviewObject.key ? getDisplayName(currentPreviewObject) : '文件预览'}`"
      width="80%"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="object-preview">
        <!-- 图片预览 -->
        <div v-if="previewType === 'image'" class="image-preview">
          <img 
            :src="previewUrl" 
            :alt="currentPreviewObject.key || '图片预览'" 
            @load="handleImageLoad"
            @error="handlePreviewError"
          />
        </div>
        
        <!-- 视频预览 -->
        <div v-else-if="previewType === 'video'" class="video-preview">
          <video 
            :src="previewUrl"
            controls
            preload="metadata"
            @error="handlePreviewError"
            style="width: 100%; max-height: 600px;"
          >
            您的浏览器不支持视频播放
          </video>
        </div>
        
        <!-- 音频预览 -->
        <div v-else-if="previewType === 'audio'" class="audio-preview">
          <div class="audio-container">
            <div class="audio-info">
              <el-icon size="48"><VideoPlay /></el-icon>
              <div class="audio-name">{{ currentPreviewObject.key ? getDisplayName(currentPreviewObject) : '音频文件' }}</div>
              <div class="audio-size">{{ formatFileSize(currentPreviewObject.size || 0) }}</div>
            </div>
            <audio 
              :src="previewUrl"
              controls
              preload="metadata"
              @error="handlePreviewError"
              style="width: 100%; margin-top: 20px;"
            >
              您的浏览器不支持音频播放
            </audio>
          </div>
        </div>
        
        <!-- 文本预览 -->
        <div v-else-if="previewType === 'text'" class="text-preview">
          <div class="text-toolbar">
            <el-tag size="small" type="info">{{ currentPreviewObject.key ? getFileType(currentPreviewObject) : '文本文件' }}</el-tag>
            <el-tag size="small">{{ formatFileSize(currentPreviewObject.size || 0) }}</el-tag>
            <el-button
              v-if="csvChartData"
              size="small"
              :type="showCsvChartView ? 'primary' : 'default'"
              @click="showCsvChartView = !showCsvChartView"
            >
              <el-icon><DataLine /></el-icon>
              {{ showCsvChartView ? '文本' : '图形' }}
            </el-button>
          </div>
          <div v-if="showCsvChartView && csvChartData && csvChartOption" class="csv-chart-container">
            <v-chart class="csv-chart" :option="csvChartOption" autoresize />
          </div>
          <pre v-else class="text-content"><code>{{ previewContent }}</code></pre>
        </div>
        
        <!-- JSON预览 -->
        <div v-else-if="previewType === 'json'" class="json-preview">
          <div class="json-toolbar">
            <el-tag size="small" type="success">JSON</el-tag>
            <el-tag size="small">{{ formatFileSize(currentPreviewObject.size || 0) }}</el-tag>
            <el-button 
              size="small" 
              text 
              @click="copyToClipboard(formatJson(previewContent))"
            >
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
          </div>
          <pre class="json-content"><code>{{ formatJson(previewContent) }}</code></pre>
        </div>
        
        <!-- Excel预览 -->
        <div v-else-if="previewType === 'excel'" class="excel-preview">
          <div class="excel-toolbar" v-if="currentPreviewObject.excelInfo">
            <el-tag size="small" type="success">Excel表格</el-tag>
            <el-tag size="small">{{ currentPreviewObject.excelInfo.rows }} 行</el-tag>
            <el-tag size="small">{{ currentPreviewObject.excelInfo.columns?.length || 0 }} 列</el-tag>
            <el-tag size="small">{{ formatFileSize(currentPreviewObject.size || 0) }}</el-tag>
          </div>
          <div class="excel-content" v-html="previewContent"></div>
        </div>
        
        <!-- NC文件预览 -->
        <div v-else-if="previewType === 'nc'" class="nc-preview">
          <div v-if="currentPreviewObject.ncInfo?.loading" class="nc-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在加载NC文件信息...</span>
          </div>
          <div v-else-if="currentPreviewObject.ncInfo?.error" class="nc-error">
            <el-result icon="error" title="加载失败" :sub-title="currentPreviewObject.ncInfo.error" />
          </div>
          <div v-else class="nc-content">
            <div class="nc-toolbar">
              <el-tag size="small" type="success">NetCDF文件</el-tag>
              <el-tag size="small" v-if="currentPreviewObject.ncVariable">{{ currentPreviewObject.ncVariable }}</el-tag>
              <el-tag size="small">{{ formatFileSize(currentPreviewObject.ncInfo?.fileSize || 0) }}</el-tag>
            </div>
            <div v-if="currentPreviewObject.ncImage" class="nc-image">
              <img :src="currentPreviewObject.ncImage" alt="NC文件可视化" />
            </div>
            <div v-if="currentPreviewObject.ncStats" class="nc-stats">
              <el-descriptions :column="4" border>
                <el-descriptions-item label="最小值">{{ currentPreviewObject.ncStats.min?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="最大值">{{ currentPreviewObject.ncStats.max?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="平均值">{{ currentPreviewObject.ncStats.mean?.toFixed(4) }}</el-descriptions-item>
                <el-descriptions-item label="维度">{{ currentPreviewObject.ncStats.shape?.join(' x ') }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <div v-if="currentPreviewObject.ncInfo?.dimensions" class="nc-dimensions">
              <h4>维度信息</h4>
              <el-tag v-for="(value, key) in currentPreviewObject.ncInfo.dimensions" :key="key" size="small" style="margin-right: 8px; margin-bottom: 4px;">
                {{ key }}: {{ value }}
              </el-tag>
            </div>
            <div v-if="currentPreviewObject.ncInfo?.variables" class="nc-variables">
              <h4>变量列表</h4>
              <el-table :data="currentPreviewObject.ncInfo.variables" size="small" max-height="200">
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
        
        <!-- PDF预览 -->
        <div v-else-if="previewType === 'pdf'" class="pdf-preview">
          <iframe 
            :src="previewUrl"
            style="width: 100%; height: 600px; border: none;"
            @error="handlePreviewError"
          >
            您的浏览器不支持PDF预览
          </iframe>
        </div>
        
        <!-- 不支持的类型 -->
        <div v-else class="unsupported-preview">
          <el-result
            icon="warning"
            title="预览不支持"
            :sub-title="`${currentPreviewObject.key ? getFileType(currentPreviewObject) : '此'} 类型文件暂不支持在线预览`"
          >
            <template #extra>
              <div class="preview-actions">
                <el-button type="primary" @click="downloadObject(currentPreviewObject)">
                  <el-icon><Download /></el-icon>
                  下载查看
                </el-button>
                <el-button @click="showObjectInfo(currentPreviewObject)">
                  <el-icon><InfoFilled /></el-icon>
                  查看详情
                </el-button>
              </div>
            </template>
          </el-result>
        </div>
      </div>
      
      <template #footer>
        <div class="preview-footer">
          <div class="preview-info">
            <span>大小: {{ formatFileSize(currentPreviewObject.size || 0) }}</span>
            <span v-if="currentPreviewObject.lastModified">
              修改时间: {{ formatDate(currentPreviewObject.lastModified) }}
            </span>
          </div>
          <div class="preview-actions">
            <el-button @click="downloadObject(currentPreviewObject)">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
            <el-button @click="showPreviewDialog = false">关闭</el-button>
          </div>
        </div>
      </template>
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
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Box, FolderOpened, Document, Delete, Download, InfoFilled, CopyDocument,
  Picture, VideoPlay, Lock, Folder, DataLine, ChatDotRound, Loading
} from '@element-plus/icons-vue'
import ResourceAnalyzeDialog from '@/components/ResourceAnalyzeDialog.vue'
import { useDataSourceStore } from '@/stores/datasource'
import { useAuthStore } from '@/stores/auth'
import { objectStorageApi } from '@/api/datasource'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const dataSourceStore = useDataSourceStore()
const authStore = useAuthStore()

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
const pageSize = ref(50)
const totalObjects = ref(0)

// 新增文件系统风格的数据
const showSidebar = ref(true)
const directoryTree = ref([])

// 分析对话
const showAnalyzeDialog = ref(false)
const analyzeResourceKey = ref('')
const analyzeDisplayName = ref('')
const analyzeDatasourceType = ref('object_storage')
const analyzeDatasourceId = ref('')

// 预览相关
const showPreviewDialog = ref(false)
const currentPreviewObject = ref({})
const previewContent = ref('')
const previewUrl = ref('')
const previewType = ref('')
const previewBlobUrl = ref('') // 存储blob URL，用于媒体文件预览
const showCsvChartView = ref(false) // CSV 图形视图开关（Year,5%,Mean,95% 三曲线）

// 详情对话框
const showInfoDialog = ref(false)
const selectedObjectInfo = ref(null)
const showBucketInfoDialog = ref(false)
const selectedBucketInfo = ref(null)

// 上传相关
const uploadUrl = computed(() => {
  if (!currentBucket.value) return ''
  return `/api/browse/object_storage/${route.params.id}/upload`
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

/** 解析 CSV 内容，若列为 Year, 5%, Mean, 95% 则返回可绘图数据 */
const csvChartData = computed(() => {
  const content = previewContent.value
  if (!content || typeof content !== 'string') return null
  const lines = content.trim().split(/\r?\n/).filter(Boolean)
  if (lines.length < 2) return null
  const headers = lines[0].split(',').map((h: string) => h.trim())
  const hLower = headers.map((h: string) => h.toLowerCase())
  const yearIdx = hLower.findIndex((h: string) => h === 'year')
  const p5Idx = headers.findIndex((h: string) => h === '5%')
  const meanIdx = hLower.findIndex((h: string) => h === 'mean')
  const p95Idx = headers.findIndex((h: string) => h === '95%')
  if (yearIdx === -1 || p5Idx === -1 || meanIdx === -1 || p95Idx === -1) return null
  const yearData: number[] = []
  const p5Data: number[] = []
  const meanData: number[] = []
  const p95Data: number[] = []
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(',').map((c: string) => c.trim())
    const y = parseFloat(cells[yearIdx])
    const v5 = parseFloat(cells[p5Idx])
    const vm = parseFloat(cells[meanIdx])
    const v95 = parseFloat(cells[p95Idx])
    if (!isNaN(y) && !isNaN(v5) && !isNaN(vm) && !isNaN(v95)) {
      yearData.push(y)
      p5Data.push(v5)
      meanData.push(vm)
      p95Data.push(v95)
    }
  }
  if (yearData.length === 0) return null
  return { yearData, p5Data, meanData, p95Data }
})

const csvChartOption = computed(() => {
  const d = csvChartData.value
  if (!d) return null
  return {
    xAxis: { type: 'category', data: d.yearData, name: 'Year' },
    yAxis: { type: 'value', name: 'Value' },
    series: [
      { name: '5%', type: 'line', data: d.p5Data, smooth: true },
      { name: 'Mean', type: 'line', data: d.meanData, smooth: true },
      { name: '95%', type: 'line', data: d.p95Data, smooth: true }
    ],
    tooltip: { trigger: 'axis' },
    legend: { top: 0 }
  }
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
    if (prefix) {
      await tryPreviewPrefixFromQuery(bucket, prefix)
    }
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
watch(() => route.params.id, async (newId) => {
  if (newId) {
    await loadDataSource()
    
    const bucket = route.query.bucket as string
    const prefix = route.query.prefix as string
    const configuredBucket = dataSource.value?.config?.bucket
    
    // 优先使用URL查询参数中的bucket
    if (bucket) {
      currentBucket.value = bucket
      currentPrefix.value = prefix || ''
      if (prefix) {
        await tryPreviewPrefixFromQuery(bucket, prefix)
      }
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
      currentBucket.value = ''
      currentPrefix.value = ''
      await loadBuckets()
    }
  }
})

watch(() => route.query, async (newQuery) => {
  const bucket = newQuery.bucket as string
  const prefix = newQuery.prefix as string
  
  if (bucket !== currentBucket.value) {
    currentBucket.value = bucket || ''
    if (bucket) {
      currentPrefix.value = prefix || ''
      if (prefix) {
        await tryPreviewPrefixFromQuery(bucket, prefix)
      }
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
    if (prefix) {
      await tryPreviewPrefixFromQuery(currentBucket.value, prefix)
    }
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
  // 图片
  if (/\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|ico)$/.test(key)) return Picture
  // 视频
  if (/\.(mp4|avi|mov|wmv|flv|mkv|webm|m4v)$/.test(key)) return VideoPlay
  // 音频 (使用VideoPlay图标，因为Element Plus没有专门的音频图标)
  if (/\.(mp3|wav|flac|aac|ogg|m4a|wma)$/.test(key)) return VideoPlay
  // 压缩包
  if (/\.(zip|rar|tar|gz|7z|bz2)$/.test(key)) return Box
  // PDF
  if (/\.pdf$/.test(key)) return Document
  // 代码文件
  if (/\.(js|ts|jsx|tsx|vue|html|css|java|py|cpp|c|h)$/.test(key)) return Document
  // JSON/配置文件
  if (/\.(json|yaml|yml|xml|ini|conf|cfg)$/.test(key)) return Document
  
  return Document
}

function getFileIconClass(object: any) {
  const classes = ['file-icon']
  if (object.isFolder) {
    classes.push('directory-icon')
  } else {
    const key = object.key.toLowerCase()
    if (/\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|ico)$/.test(key)) {
      classes.push('image-icon')
    } else if (/\.(mp4|avi|mov|wmv|flv|mkv|webm|m4v)$/.test(key)) {
      classes.push('video-icon')
    } else if (/\.(mp3|wav|flac|aac|ogg|m4a|wma)$/.test(key)) {
      classes.push('audio-icon')
    } else if (/\.(zip|rar|tar|gz|7z|bz2)$/.test(key)) {
      classes.push('archive-icon')
    } else if (/\.pdf$/.test(key)) {
      classes.push('pdf-icon')
    } else if (/\.(js|ts|jsx|tsx|vue|html|css|java|py|cpp|c|h)$/.test(key)) {
      classes.push('code-icon')
    } else if (/\.(json|yaml|yml|xml|ini|conf|cfg)$/.test(key)) {
      classes.push('config-icon')
    }
  }
  return classes.join(' ')
}

// 保持兼容性的别名
// 已移除未使用的函数别名

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
  if (/\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|ico)$/.test(key)) return '图片'
  if (/\.(mp4|avi|mov|wmv|flv|mkv|webm|m4v)$/.test(key)) return '视频'
  if (/\.(mp3|wav|flac|aac|ogg|m4a|wma)$/.test(key)) return '音频'
  if (/\.(txt|md|log|csv)$/.test(key)) return '文本'
  if (/\.json$/.test(key)) return 'JSON'
  if (/\.(xml|yaml|yml)$/.test(key)) return '配置文件'
  if (/\.pdf$/.test(key)) return 'PDF'
  if (/\.(zip|rar|tar|gz|7z|bz2)$/.test(key)) return '压缩包'
  if (/\.(js|ts|jsx|tsx)$/.test(key)) return 'JavaScript'
  if (/\.(vue|html|css)$/.test(key)) return 'Web文件'
  if (/\.(java|py|cpp|c|h)$/.test(key)) return '代码文件'
  if (/\.(ini|conf|cfg)$/.test(key)) return '配置文件'
  
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
  console.log('[canPreview] object:', object)
  console.log('[canPreview] object.key:', object?.key)
  
  const key = object.key.toLowerCase()
  const textExts = /\.(txt|md|json|xml|csv|log|yaml|yml|ini|conf|cfg|js|ts|html|css|sql|py|java|cpp|c|h|vue|jsx|tsx)$/
  const imageExts = /\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|ico)$/
  const videoExts = /\.(mp4|avi|mov|wmv|flv|mkv|webm|m4v)$/
  const audioExts = /\.(mp3|wav|flac|aac|ogg|m4a|wma)$/
  const excelExts = /\.(xlsx|xls)$/
  const ncExts = /\.nc$/
  
  const result = textExts.test(key) || imageExts.test(key) || videoExts.test(key) || audioExts.test(key) || excelExts.test(key) || ncExts.test(key)
  console.log('[canPreview] result:', result)
  return result
}

// 添加新的文件类型检测函数
function getPreviewType(object: any): string {
  const key = object.key.toLowerCase()
  
  if (/\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|ico)$/.test(key)) {
    return 'image'
  }
  if (/\.(mp4|avi|mov|wmv|flv|mkv|webm|m4v)$/.test(key)) {
    return 'video'
  }
  if (/\.(mp3|wav|flac|aac|ogg|m4a|wma)$/.test(key)) {
    return 'audio'
  }
  if (/\.json$/.test(key)) {
    return 'json'
  }
  if (/\.(txt|md|csv|log|yaml|yml|ini|conf|cfg|js|ts|html|css|sql|py|java|cpp|c|h|vue|jsx|tsx|xml)$/.test(key)) {
    return 'text'
  }
  if (/\.pdf$/.test(key)) {
    return 'pdf'
  }
  if (/\.(xlsx|xls)$/.test(key)) {
    return 'excel'
  }
  if (/\.nc$/.test(key)) {
    return 'nc'
  }
  
  return 'unsupported'
}

/**
 * 当 URL 的 bucket + prefix 指向一个文件时，自动弹出预览浮窗；否则返回 false。
 * 用于 /browse/object_storage/:id?bucket=xxx&prefix=path/to/file.mp4 直接预览文件。
 */
async function tryPreviewPrefixFromQuery(bucketFromQuery: string, prefixFromQuery: string): Promise<boolean> {
  if (!bucketFromQuery || !prefixFromQuery || prefixFromQuery.endsWith('/')) return false
  const key = prefixFromQuery.replace(/\/+$/, '')
  const obj = { key, isFolder: false }
  if (getPreviewType(obj) === 'unsupported') return false
  currentBucket.value = bucketFromQuery
  const parentPrefix = key.includes('/') ? key.split('/').slice(0, -1).join('/') : ''
  currentPrefix.value = parentPrefix
  await previewObject(obj)
  return true
}

function openAnalyze(row: any) {
  const id = route.params.id as string
  analyzeDatasourceId.value = id
  analyzeDatasourceType.value = 'object_storage'
  analyzeResourceKey.value = `object_storage:${id}:${currentBucket.value}:${row.key}`
  const key = row.key || ''
  analyzeDisplayName.value = row.name || (key.includes('/') ? key.split('/').pop() : key) || '对象'
  showAnalyzeDialog.value = true
}

async function previewObject(object: any) {
  try {
    loading.value = true
    currentPreviewObject.value = object
    
    const id = route.params.id as string
    const detectedType = getPreviewType(object)
    previewType.value = detectedType
    
    switch (detectedType) {
      case 'image':
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          if (!token) {
            ElMessage.error('请先登录')
            previewType.value = 'unsupported'
            break
          }
          
          const imageApiUrl = `/api/browse/object_storage/${id}/preview?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
          const response = await fetch(imageApiUrl, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          
          if (!response.ok) {
            throw new Error(`图片预览失败: ${response.status} ${response.statusText}`)
          }
          
          const blob = await response.blob()
          if (!blob || blob.size === 0) {
            throw new Error('图片文件为空或无效')
          }
          
          // 清理之前的blob URL（如果存在）
          if (previewBlobUrl.value) {
            URL.revokeObjectURL(previewBlobUrl.value)
          }
          
          // 创建新的blob URL
          previewBlobUrl.value = URL.createObjectURL(blob)
          previewUrl.value = previewBlobUrl.value
          
        } catch (error) {
          console.error('获取图片文件失败:', error)
          ElMessage.error(`图片预览失败: ${error.message || '未知错误'}`)
          previewType.value = 'unsupported'
        }
        break
        
      case 'video':
      case 'audio':
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          if (!token) {
            ElMessage.error('请先登录')
            previewType.value = 'unsupported'
            break
          }
          
          const previewApiUrl = `/api/browse/object_storage/${id}/preview?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
          const response = await fetch(previewApiUrl, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          
          if (!response.ok) {
            throw new Error(`预览失败: ${response.status} ${response.statusText}`)
          }
          
          const blob = await response.blob()
          if (!blob || blob.size === 0) {
            throw new Error('预览文件为空或无效')
          }
          
          // 清理之前的blob URL（如果存在）
          if (previewBlobUrl.value) {
            URL.revokeObjectURL(previewBlobUrl.value)
          }
          
          // 创建新的blob URL
          previewBlobUrl.value = URL.createObjectURL(blob)
          previewUrl.value = previewBlobUrl.value
          
        } catch (error) {
          console.error('获取媒体文件失败:', error)
          ElMessage.error(`媒体预览失败: ${error.message || '未知错误'}`)
          previewType.value = 'unsupported'
        }
        break
        
      case 'text':
      case 'json':
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          const response = await fetch(`/api/browse/object_storage/${id}/content?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (response.ok) {
            const data = await response.json()
            previewContent.value = data.content || ''
          } else {
            throw new Error('Failed to fetch content')
          }
        } catch (error) {
          console.error('获取文本内容失败:', error)
          ElMessage.error('获取文件内容失败')
          previewType.value = 'unsupported'
        }
        break
      
      case 'excel':
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          const response = await fetch(`/api/browse/object_storage/${id}/content?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (response.ok) {
            const data = await response.json()
            previewContent.value = data.content || ''
            // 存储额外的Excel信息
            currentPreviewObject.value.excelInfo = {
              rows: data.rows,
              columns: data.columns
            }
          } else {
            throw new Error('Failed to fetch Excel content')
          }
        } catch (error) {
          console.error('获取Excel内容失败:', error)
          ElMessage.error('获取Excel文件内容失败')
          previewType.value = 'unsupported'
        }
        break
        
      case 'nc':
        console.log('[previewObject] NC file detected')
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          if (!token) {
            ElMessage.error('请先登录')
            previewType.value = 'unsupported'
            break
          }
          
          const ncApiUrl = `/api/browse/object_storage/${id}/nc/preview?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
          const response = await fetch(ncApiUrl, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
          })
          
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || `NC文件预览失败: ${response.status} ${response.statusText}`)
          }
          
          const result = await response.json()
          console.log('[previewObject] NC preview result:', result)
          
          if (result.code === 200 && result.data) {
            if (result.data.image) {
              currentPreviewObject.value.ncImage = result.data.image
              currentPreviewObject.value.ncVariable = result.data.variable
              currentPreviewObject.value.ncStats = {
                min: result.data.min,
                max: result.data.max,
                mean: result.data.mean,
                shape: result.data.shape
              }
            }
            currentPreviewObject.value.ncInfo = {
              loading: false,
              message: result.message
            }
          } else {
            throw new Error(result.detail || 'NC 文件预览失败')
          }
        } catch (error) {
          console.error('NC 文件预览失败:', error)
          ElMessage.error(`NC 文件预览失败: ${error.message}`)
          previewType.value = 'unsupported'
        }
        break
        
      case 'pdf':
        try {
          const token = authStore.token || localStorage.getItem('auth_token')
          if (!token) {
            ElMessage.error('请先登录')
            previewType.value = 'unsupported'
            break
          }
          
          const pdfApiUrl = `/api/browse/object_storage/${id}/preview?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
          const response = await fetch(pdfApiUrl, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          
          if (!response.ok) {
            throw new Error(`PDF预览失败: ${response.status} ${response.statusText}`)
          }
          
          const blob = await response.blob()
          if (!blob || blob.size === 0) {
            throw new Error('PDF文件为空或无效')
          }
          
          // 清理之前的blob URL（如果存在）
          if (previewBlobUrl.value) {
            URL.revokeObjectURL(previewBlobUrl.value)
          }
          
          // 创建新的blob URL
          previewBlobUrl.value = URL.createObjectURL(blob)
          previewUrl.value = previewBlobUrl.value
          
        } catch (error) {
          console.error('获取PDF文件失败:', error)
          ElMessage.error(`PDF预览失败: ${error.message || '未知错误'}`)
          previewType.value = 'unsupported'
        }
        break
        
      default:
        previewType.value = 'unsupported'
    }
    
    showPreviewDialog.value = true
  } catch (error) {
    console.error('预览失败:', error)
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

// 清理blob URL的函数
function cleanupPreviewBlobUrl() {
  if (previewBlobUrl.value) {
    URL.revokeObjectURL(previewBlobUrl.value)
    previewBlobUrl.value = ''
  }
}

// 监听预览对话框关闭，清理blob URL 并重置图表视图
watch(showPreviewDialog, (newValue) => {
  if (!newValue) {
    showCsvChartView.value = false
    setTimeout(() => {
      cleanupPreviewBlobUrl()
    }, 100)
  }
})

// 组件卸载时清理blob URL
onUnmounted(() => {
  cleanupPreviewBlobUrl()
})

async function downloadObject(object: any) {
  if (!currentBucket.value) {
    ElMessage.error('请先选择存储桶')
    return
  }
  
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
    
    const downloadUrl = `/api/browse/object_storage/${id}/download?bucket=${encodeURIComponent(currentBucket.value)}&key=${encodeURIComponent(object.key)}`
    
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
    link.download = getDisplayName(object)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 清理URL对象
    setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 100)
    
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('❌ 对象存储浏览: 下载失败', error)
    ElMessage.error(error.message || '下载失败')
  } finally {
    loading.value = false
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

// 复制API链接
async function copyApiLink(object: any) {
  if (!currentBucket.value) {
    ElMessage.error('请先选择存储桶')
    return
  }
  
  try {
    const id = route.params.id as string
    const apiUrl = `${window.location.origin}/api/browse/object_storage/${id}/api?bucket=${encodeURIComponent(currentBucket.value)}&key=${encodeURIComponent(object.key)}`
    
    // 尝试使用现代 Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(apiUrl)
      ElMessage.success('API链接已复制到剪贴板')
      return
    }
    
    // 降级方案：使用 textarea 和 execCommand
    const textarea = document.createElement('textarea')
    textarea.value = apiUrl
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    
    try {
      const successful = document.execCommand('copy')
      if (successful) {
        ElMessage.success('API链接已复制到剪贴板')
      } else {
        throw new Error('execCommand 返回 false')
      }
    } catch (err) {
      console.error('复制失败:', err)
      ElMessage.error('复制失败，请手动复制链接')
      // 显示链接供用户手动复制
      ElMessage.info(apiUrl)
    } finally {
      document.body.removeChild(textarea)
    }
  } catch (error) {
    console.error('复制API链接失败:', error)
    ElMessage.error('复制API链接失败')
  }
}

async function showObjectInfo(object: any) {
  try {
    const id = route.params.id as string
    const response = await fetch(`/api/browse/object_storage/${id}/info?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`)
    selectedObjectInfo.value = await response.json()
    showInfoDialog.value = true
  } catch (error) {
    ElMessage.error('获取对象信息失败')
  }
}

async function copyObjectUrl(object: any) {
  try {
    const id = route.params.id as string
    const url = `${window.location.origin}/api/browse/object_storage/${id}/download?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`
    
    await navigator.clipboard.writeText(url)
    ElMessage.success('下载链接已复制到剪贴板')
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
    const response = await fetch(`/api/browse/object_storage/${id}?bucket=${currentBucket.value}&key=${encodeURIComponent(object.key)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
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
    let successCount = 0
    let errorCount = 0
    
    // 循环删除每个对象
    for (const obj of selectedObjects.value) {
      try {
        const response = await fetch(`/api/browse/object_storage/${id}?bucket=${currentBucket.value}&key=${encodeURIComponent(obj.key)}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        })
        
        if (response.ok) {
          successCount++
        } else {
          errorCount++
        }
      } catch (error) {
        errorCount++
        console.error(`删除对象 ${obj.key} 失败:`, error)
      }
    }
    
    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个对象${errorCount > 0 ? `, ${errorCount} 个失败` : ''}`)
      selectedObjects.value = []
      await refreshData()
    } else {
      throw new Error('所有对象删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
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
    const response = await fetch(`/api/browse/object_storage/${id}/bucket-info?bucket=${bucketName}`)
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

// 预览相关辅助方法
function handleImageLoad() {
  // 图片加载完成处理
}

function handlePreviewError(event: Event) {
  console.error('预览加载失败:', event)
  ElMessage.error('预览加载失败，请尝试下载文件查看')
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
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

.etag {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

/* 图标颜色 */
.folder-icon,
.directory-icon {
  color: #409eff;
}

.image-icon {
  color: #67c23a;
}

.video-icon {
  color: #e6a23c;
}

.audio-icon {
  color: #9254de;
}

.archive-icon {
  color: #f56c6c;
}

.pdf-icon {
  color: #ff4d4f;
}

.code-icon {
  color: #1890ff;
}

.config-icon {
  color: #52c41a;
}

/* 预览样式 */
.object-preview {
  min-height: 400px;
  max-height: 80vh;
  overflow-y: auto;
}

/* 图片预览 */
.image-preview {
  text-align: center;
  padding: 20px;
  background: #fafbfc;
  border-radius: 8px;
}

.image-preview img {
  max-width: 100%;
  max-height: 600px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.image-preview img:hover {
  transform: scale(1.02);
}

/* 视频预览 */
.video-preview {
  text-align: center;
  padding: 20px;
  background: #000;
  border-radius: 8px;
}

.video-preview video {
  border-radius: 8px;
  max-width: 100%;
  max-height: 600px;
}

/* 音频预览 */
.audio-preview {
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.audio-container {
  text-align: center;
}

.audio-info {
  margin-bottom: 30px;
}

.audio-info .el-icon {
  margin-bottom: 16px;
  color: white;
}

.audio-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  word-break: break-all;
}

.audio-size {
  font-size: 14px;
  opacity: 0.9;
}

/* 文本预览 */
.text-preview {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.text-toolbar,
.json-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.text-content,
.json-content {
  margin: 0;
  padding: 20px;
  background: #ffffff;
  border: none;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.json-content {
  background: #f8f9fa;
  color: #2c3e50;
}

.csv-chart-container {
  padding: 20px;
  min-height: 400px;
}

.csv-chart {
  width: 100%;
  height: 400px;
}

/* NC文件预览样式 */
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

/* Excel预览样式 */
.excel-preview {
  max-width: 100%;
}

.excel-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  padding: 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.excel-content {
  max-height: 600px;
  overflow: auto;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
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

/* JSON语法高亮样式 */
.json-content code {
  background: transparent;
  padding: 0;
  font-family: inherit;
}

/* PDF预览 */
.pdf-preview {
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
}

/* 预览对话框页脚 */
.preview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-top: 1px solid #e4e7ed;
  margin-top: 20px;
}

.preview-info {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: #666;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

/* 不支持预览的样式优化 */
.unsupported-preview {
  padding: 40px 20px;
}

.unsupported-preview .preview-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 16px;
}

:deep(.el-breadcrumb__item.is-link) {
  cursor: pointer;
}

:deep(.el-breadcrumb__item.is-link .el-breadcrumb__inner:hover) {
  color: #409eff;
}
</style>
