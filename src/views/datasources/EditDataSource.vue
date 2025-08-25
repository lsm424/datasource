<template>
  <div class="edit-datasource">
    <div class="header">
      <el-breadcrumb>
        <el-breadcrumb-item>
          <router-link to="/datasources">数据源管理</router-link>
        </el-breadcrumb-item>
        <el-breadcrumb-item>编辑数据源</el-breadcrumb-item>
      </el-breadcrumb>
      
      <div class="header-actions">
        <el-button @click="goBack">返回</el-button>
        <el-button 
          type="primary" 
          @click="testConnection"
          :loading="testing"
          :disabled="!canTest"
        >
          测试连接
        </el-button>
        <el-button 
          type="success" 
          @click="saveDataSource"
          :loading="saving"
          :disabled="!canSave"
        >
          保存
        </el-button>
      </div>
    </div>

    <div class="content">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>数据源配置</span>
            <el-tag v-if="dataSource.id" :type="getStatusType(dataSource.is_active)">
              {{ dataSource.is_active ? '已激活' : '未激活' }}
            </el-tag>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          @submit.prevent
        >
          <!-- 基本信息 -->
          <el-divider content-position="left">基本信息</el-divider>
          
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="数据源名称" prop="name" required>
                <el-input 
                  v-model="form.name" 
                  placeholder="请输入数据源名称"
                  maxlength="100"
                  show-word-limit
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="中文名称" prop="cname">
                <el-input 
                  v-model="form.cname" 
                  placeholder="请输入中文名称"
                  maxlength="100"
                  show-word-limit
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="数据源类型" prop="type" required>
                <el-select 
                  v-model="form.type" 
                  placeholder="请选择数据源类型"
                  style="width: 100%"
                  @change="handleTypeChange"
                  :disabled="!!dataSource.id"
                >
                  <el-option
                    v-for="option in typeOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  >
                    <div class="type-option">
                      <el-icon :class="option.iconClass">
                        <component :is="option.icon" />
                      </el-icon>
                      <span>{{ option.label }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="所属单位" prop="company">
                <el-input 
                  v-model="form.company" 
                  placeholder="请输入所属单位"
                  maxlength="100"
                  show-word-limit
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              placeholder="请输入数据源描述"
              :rows="3"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>

          <!-- 连接配置 -->
          <el-divider content-position="left">连接配置</el-divider>

          <!-- 文件系统配置 -->
          <div v-if="form.type === 'filesystem'">
            <el-form-item label="根路径" prop="config.path" required>
              <el-input
                v-model="form.config.path"
                placeholder="请输入文件系统根路径，如: /data/files"
              >
                <template #prepend>
                  <el-icon><FolderOpened /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            
            <el-form-item label="访问模式">
              <el-radio-group v-model="form.config.access_mode">
                <el-radio value="readonly">只读</el-radio>
                <el-radio value="readwrite">读写</el-radio>
              </el-radio-group>
            </el-form-item>
          </div>

          <!-- 对象存储配置 -->
          <div v-if="form.type === 'object_storage'">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="Endpoint" prop="config.endpoint" required>
                  <el-input
                    v-model="form.config.endpoint"
                    placeholder="请输入服务端点，如: s3.amazonaws.com"
                  >
                    <template #prepend>
                      <el-icon><Link /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="存储桶" prop="config.bucket" required>
                  <el-input
                    v-model="form.config.bucket"
                    placeholder="请输入存储桶名称"
                  >
                    <template #prepend>
                      <el-icon><Box /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="Access Key" prop="config.access_key" required>
                  <el-input
                    v-model="form.config.access_key"
                    placeholder="请输入Access Key"
                    show-password
                  >
                    <template #prepend>
                      <el-icon><Key /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Secret Key" prop="config.secret_key" required>
                  <el-input
                    v-model="form.config.secret_key"
                    placeholder="请输入Secret Key"
                    show-password
                  >
                    <template #prepend>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="地域">
                  <el-input
                    v-model="form.config.region"
                    placeholder="请输入地域，如: us-east-1"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="使用SSL">
                  <el-switch v-model="form.config.use_ssl" />
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <!-- 数据库配置 -->
          <div v-if="form.type === 'database'">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="数据库类型" prop="config.db_type" required>
                  <el-select 
                    v-model="form.config.db_type" 
                    placeholder="请选择数据库类型"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="option in dbTypeOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="数据库名称" prop="config.database" required>
                  <el-input
                    v-model="form.config.database"
                    placeholder="请输入数据库名称"
                  >
                    <template #prepend>
                      <el-icon><DataBase /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="主机地址" prop="config.host" required>
                  <el-input
                    v-model="form.config.host"
                    placeholder="请输入主机地址"
                  >
                    <template #prepend>
                      <el-icon><Monitor /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="端口号" prop="config.port" required>
                  <el-input-number
                    v-model="form.config.port"
                    placeholder="请输入端口号"
                    :min="1"
                    :max="65535"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="用户名" prop="config.user" required>
                  <el-input
                    v-model="form.config.user"
                    placeholder="请输入用户名"
                  >
                    <template #prepend>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="密码" prop="config.password" required>
                  <el-input
                    v-model="form.config.password"
                    placeholder="请输入密码"
                    show-password
                  >
                    <template #prepend>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="连接池大小">
                  <el-input-number
                    v-model="form.config.pool_size"
                    :min="1"
                    :max="100"
                    placeholder="默认为10"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="连接超时(秒)">
                  <el-input-number
                    v-model="form.config.timeout"
                    :min="1"
                    :max="300"
                    placeholder="默认为30"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <!-- 高级配置 -->
          <el-divider content-position="left">高级配置</el-divider>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="标签">
                <el-select
                  v-model="form.tags"
                  multiple
                  filterable
                  allow-create
                  placeholder="请选择或输入标签"
                  style="width: 100%"
                >
                  <el-option
                    v-for="tag in availableTags"
                    :key="tag"
                    :label="tag"
                    :value="tag"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="是否激活">
                <el-switch v-model="form.is_active" />
                <span class="form-tip">激活后才能被访问</span>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- JSON配置编辑器 -->
          <el-form-item>
            <template #label>
              <span>JSON配置</span>
              <el-tooltip content="高级用户可直接编辑JSON配置" placement="top">
                <el-icon style="margin-left: 4px;"><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
            <div class="json-editor">
              <el-button 
                type="text" 
                @click="showJsonEditor = !showJsonEditor"
                style="margin-bottom: 8px;"
              >
                {{ showJsonEditor ? '隐藏' : '显示' }}JSON编辑器
              </el-button>
              <div v-if="showJsonEditor">
                <el-input
                  v-model="jsonConfig"
                  type="textarea"
                  :rows="10"
                  placeholder="JSON配置"
                  @blur="validateJson"
                />
                <div v-if="jsonError" class="json-error">
                  <el-alert
                    :title="jsonError"
                    type="error"
                    :closable="false"
                    show-icon
                  />
                </div>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 连接测试结果对话框 -->
    <el-dialog
      v-model="showTestResult"
      title="连接测试结果"
      width="500px"
    >
      <div class="test-result">
        <el-result
          :icon="testResult.success ? 'success' : 'error'"
          :title="testResult.success ? '连接成功' : '连接失败'"
          :sub-title="testResult.message"
        />
        
        <div v-if="testResult.details" class="test-details">
          <el-divider>详细信息</el-divider>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item
              v-for="(value, key) in testResult.details"
              :key="key"
              :label="formatDetailKey(key)"
            >
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus'
import { 
  FolderOpened, Link, Box, Key, Lock, DataBase, Monitor, User,
  QuestionFilled, Folder, Cloud, Coin
} from '@element-plus/icons-vue'
import { useDataSourceStore } from '@/stores/datasource'

const route = useRoute()
const router = useRouter()
const dataSourceStore = useDataSourceStore()

// 表单引用
const formRef = ref<FormInstance>()

// 响应式数据
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const showJsonEditor = ref(false)
const showTestResult = ref(false)
const jsonError = ref('')
const jsonConfig = ref('')

// 数据源对象
const dataSource = ref<any>({})

// 表单数据
const form = reactive({
  id: '',
  name: '',
  cname: '',
  type: '',
  company: '',
  description: '',
  tags: [],
  is_active: true,
  config: {}
})

// 测试结果
const testResult = ref({
  success: false,
  message: '',
  details: null
})

// 可用标签
const availableTags = ref(['生产', '开发', '测试', '重要', '临时'])

// 数据源类型选项
const typeOptions = [
  {
    value: 'filesystem',
    label: '文件系统',
    icon: Folder,
    iconClass: 'filesystem-icon'
  },
  {
    value: 'object_storage',
    label: '对象存储',
    icon: Cloud,
    iconClass: 'storage-icon'
  },
  {
    value: 'database',
    label: '数据库',
    icon: Coin,
    iconClass: 'database-icon'
  }
]

// 数据库类型选项
const dbTypeOptions = [
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'oracle', label: 'Oracle' },
  { value: 'sqlserver', label: 'SQL Server' },
  { value: 'mongodb', label: 'MongoDB' }
]

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择数据源类型', trigger: 'change' }
  ],
  'config.path': [
    { required: true, message: '请输入文件系统根路径', trigger: 'blur' }
  ],
  'config.endpoint': [
    { required: true, message: '请输入服务端点', trigger: 'blur' }
  ],
  'config.bucket': [
    { required: true, message: '请输入存储桶名称', trigger: 'blur' }
  ],
  'config.access_key': [
    { required: true, message: '请输入Access Key', trigger: 'blur' }
  ],
  'config.secret_key': [
    { required: true, message: '请输入Secret Key', trigger: 'blur' }
  ],
  'config.db_type': [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  'config.host': [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  'config.port': [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ],
  'config.database': [
    { required: true, message: '请输入数据库名称', trigger: 'blur' }
  ],
  'config.user': [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  'config.password': [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 计算属性
const canTest = computed(() => {
  if (!form.type) return false
  
  switch (form.type) {
    case 'filesystem':
      return !!form.config.path
    case 'object_storage':
      return !!(form.config.endpoint && form.config.bucket && 
               form.config.access_key && form.config.secret_key)
    case 'database':
      return !!(form.config.db_type && form.config.host && 
               form.config.port && form.config.database && 
               form.config.user && form.config.password)
    default:
      return false
  }
})

const canSave = computed(() => {
  return form.name && form.type && canTest.value
})

const isEditing = computed(() => {
  return !!route.params.id && route.params.id !== 'new'
})

// 生命周期
onMounted(async () => {
  if (isEditing.value) {
    await loadDataSource()
  } else {
    // 新建模式，初始化默认配置
    initializeForm()
  }
})

// 监听表单变化，同步到JSON编辑器
watch(() => form.config, (newConfig) => {
  if (!showJsonEditor.value) return
  jsonConfig.value = JSON.stringify(newConfig, null, 2)
}, { deep: true })

// 方法
async function loadDataSource() {
  try {
    loading.value = true
    const id = route.params.id as string
    dataSource.value = await dataSourceStore.getDataSource(id)
    
    // 填充表单数据
    Object.assign(form, {
      id: dataSource.value.id,
      name: dataSource.value.name,
      cname: dataSource.value.cname,
      type: dataSource.value.type,
      company: dataSource.value.company,
      description: dataSource.value.description,
      tags: dataSource.value.tags || [],
      is_active: dataSource.value.is_active,
      config: dataSource.value.config || {}
    })
    
    jsonConfig.value = JSON.stringify(form.config, null, 2)
  } catch (error) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}

function initializeForm() {
  // 重置配置
  form.config = {}
  jsonConfig.value = '{}'
}

function handleTypeChange(type: string) {
  // 切换类型时重置配置
  initializeForm()
  
  // 根据类型设置默认配置
  switch (type) {
    case 'filesystem':
      form.config = {
        path: '',
        access_mode: 'readonly'
      }
      break
    case 'object_storage':
      form.config = {
        endpoint: '',
        bucket: '',
        access_key: '',
        secret_key: '',
        region: '',
        use_ssl: true
      }
      break
    case 'database':
      form.config = {
        db_type: 'mysql',
        host: '',
        port: 3306,
        database: '',
        user: '',
        password: '',
        pool_size: 10,
        timeout: 30
      }
      break
  }
  
  jsonConfig.value = JSON.stringify(form.config, null, 2)
}

async function testConnection() {
  try {
    testing.value = true
    
    const testData = {
      type: form.type,
      config: form.config
    }
    
    console.log('🔧 EditDataSource: 开始测试连接', testData)
    const result = await dataSourceStore.testConnection(testData)
    console.log('✅ EditDataSource: 测试连接结果', result)
    
    testResult.value = result
    showTestResult.value = true
    
    if (result.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(`连接测试失败：${result.message}`)
    }
  } catch (error: any) {
    console.error('❌ EditDataSource: 测试连接异常', error)
    testResult.value = {
      success: false,
      message: error.message || '测试请求失败',
      details: null
    }
    showTestResult.value = true
    ElMessage.error(`连接测试失败：${error.message || '测试请求失败'}`)
  } finally {
    testing.value = false
  }
}

async function saveDataSource() {
  try {
    // 验证表单
    const valid = await formRef.value?.validate()
    if (!valid) return
    
    // 验证JSON配置
    if (showJsonEditor.value && !validateJson()) {
      return
    }
    
    saving.value = true
    
    const saveData = {
      name: form.name,
      cname: form.cname,
      type: form.type,
      company: form.company,
      description: form.description,
      tags: form.tags,
      is_active: form.is_active,
      config: form.config
    }
    
    let response
    if (isEditing.value) {
      // 更新
      response = await dataSourceStore.updateDataSource(form.id, saveData)
    } else {
      // 创建
      response = await dataSourceStore.createDataSource(saveData)
    }
    
    ElMessage.success(isEditing.value ? '更新成功' : '创建成功')
    
    // 跳转到数据源列表或详情页
    router.push('/datasources')
  } catch (error) {
    ElMessage.error(isEditing.value ? '更新失败' : '创建失败')
  } finally {
    saving.value = false
  }
}

function validateJson(): boolean {
  try {
    const parsed = JSON.parse(jsonConfig.value)
    form.config = parsed
    jsonError.value = ''
    return true
  } catch (error) {
    jsonError.value = 'JSON格式错误: ' + error.message
    return false
  }
}

function goBack() {
  router.back()
}

function getStatusType(isActive: boolean): string {
  return isActive ? 'success' : 'warning'
}

function formatDetailKey(key: string): string {
  const keyMap: Record<string, string> = {
    'version': '版本',
    'charset': '字符集',
    'timezone': '时区',
    'max_connections': '最大连接数',
    'server_info': '服务器信息',
    'disk_space': '磁盘空间',
    'permissions': '权限',
    'bucket_count': '存储桶数量',
    'region': '地域'
  }
  return keyMap[key] || key
}
</script>

<style scoped>
.edit-datasource {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: #f5f7fa;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filesystem-icon {
  color: #409eff;
}

.storage-icon {
  color: #67c23a;
}

.database-icon {
  color: #e6a23c;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.json-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}

.json-error {
  margin-top: 8px;
}

.test-result {
  padding: 20px 0;
}

.test-details {
  margin-top: 20px;
}

:deep(.el-divider__text) {
  background-color: #fff;
  font-weight: bold;
  color: #303133;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-card__header) {
  background-color: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

:deep(.el-input-group__prepend) {
  background-color: #f5f7fa;
  border-color: #dcdfe6;
  color: #909399;
}

:deep(.el-select .el-input__wrapper) {
  cursor: pointer;
}

:deep(.el-textarea__inner) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.el-row {
  margin-bottom: 0;
}

.el-col {
  margin-bottom: 0;
}

:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-form-item--small) {
  margin-bottom: 18px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .header-actions {
    justify-content: flex-end;
  }
  
  .content {
    padding: 16px;
  }
  
  .el-row {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  
  .el-col {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-bottom: 12px;
  }
}

/* 加载状态 */
.el-form--loading {
  opacity: 0.6;
  pointer-events: none;
}

/* 必填字段标识 */
:deep(.el-form-item.is-required .el-form-item__label::before) {
  content: '*';
  color: #f56c6c;
  margin-right: 4px;
}
</style>
