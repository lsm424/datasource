<template>
  <div class="page-container">
    <div class="page-header">
      <h1>添加数据源</h1>
      <p>配置新的数据源以便在系统中进行数据浏览</p>
    </div>

    <el-card class="create-card">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="选择类型" description="选择数据源类型" />
        <el-step title="基本信息" description="填写基本信息" />
        <el-step title="连接配置" description="配置连接参数" />
        <el-step title="测试连接" description="验证连接配置" />
      </el-steps>

      <div class="step-content">
        <!-- 步骤1: 选择类型 -->
        <div v-if="currentStep === 0" class="step-container">
          <h3>选择数据源类型</h3>
          <div class="type-grid">
            <div 
              v-for="type in dataSourceTypes" 
              :key="type.value"
              class="type-card"
              :class="{ active: selectedType === type.value }"
              @click="selectedType = type.value"
            >
              <div class="type-icon">
                <el-icon :size="32">
                  <component :is="type.icon" />
                </el-icon>
              </div>
              <h4>{{ type.label }}</h4>
              <p>{{ type.description }}</p>
            </div>
          </div>
        </div>

        <!-- 步骤2: 基本信息 -->
        <div v-if="currentStep === 1" class="step-container">
          <h3>基本信息</h3>
          <el-form
            ref="basicFormRef"
            :model="basicForm"
            :rules="basicRules"
            label-position="top"
            class="basic-form"
          >
            <div class="form-row">
              <el-form-item label="数据源名称" prop="name">
                <el-input
                  v-model="basicForm.name"
                  placeholder="请输入数据源名称（英文标识）"
                  clearable
                />
              </el-form-item>

              <el-form-item label="中文名称" prop="cname">
                <el-input
                  v-model="basicForm.cname"
                  placeholder="请输入中文显示名称"
                  clearable
                />
              </el-form-item>
            </div>

            <div class="form-row">
              <el-form-item label="单位/公司" prop="company">
                <el-input
                  v-model="basicForm.company"
                  placeholder="请输入单位或公司名称（可选）"
                  clearable
                />
              </el-form-item>

              <el-form-item label="数据来源" prop="source">
                <el-input
                  v-model="basicForm.source"
                  placeholder="请输入数据来源（可选）"
                  clearable
                />
              </el-form-item>
            </div>

            <el-form-item label="描述" prop="desc">
              <el-input
                v-model="basicForm.desc"
                type="textarea"
                placeholder="请描述这个数据源的用途和内容（可选）"
                :rows="3"
                maxlength="1000"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="标签">
              <el-tag
                v-for="tag in basicForm.tags"
                :key="tag"
                class="tag-item"
                closable
                @close="removeTag(tag)"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-if="tagInputVisible"
                ref="tagInputRef"
                v-model="tagInputValue"
                size="small"
                class="tag-input"
                @keyup.enter="confirmTag"
                @blur="confirmTag"
              />
              <el-button
                v-else
                size="small"
                @click="showTagInput"
              >
                <el-icon><Plus /></el-icon>
                添加标签
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤3: 连接配置 -->
        <div v-if="currentStep === 2" class="step-container">
          <h3>连接配置</h3>
          
          <!-- 文件系统配置 -->
          <el-form
            v-if="selectedType === 'filesystem'"
            ref="configFormRef"
            :model="configForms.filesystem"
            :rules="filesystemRules"
            label-position="top"
            class="config-form"
          >
            <el-form-item label="文件系统路径" prop="path">
              <el-input
                v-model="configForms.filesystem.path"
                placeholder="请输入文件系统的根路径，如: /data/files"
                clearable
              />
              <div class="form-tip">
                请确保系统有权限访问该路径
              </div>
            </el-form-item>

            <el-form-item label="文件编码" prop="encoding">
              <el-select
                v-model="configForms.filesystem.encoding"
                placeholder="选择文件编码"
              >
                <el-option label="UTF-8" value="utf-8" />
                <el-option label="GBK" value="gbk" />
                <el-option label="GB2312" value="gb2312" />
                <el-option label="ASCII" value="ascii" />
              </el-select>
            </el-form-item>

            <el-form-item label="允许的文件扩展名">
              <el-input
                v-model="extensionInput"
                placeholder="输入扩展名，用逗号分隔，如: .txt,.csv,.json"
                @blur="updateExtensions"
              />
              <div class="form-tip">
                留空表示允许所有文件类型
              </div>
            </el-form-item>
          </el-form>

          <!-- 数据库配置 -->
          <el-form
            v-if="selectedType === 'database'"
            ref="configFormRef"
            :model="configForms.database"
            :rules="databaseRules"
            label-position="top"
            class="config-form"
          >
            <el-form-item label="数据库类型" prop="db_type">
              <el-select
                v-model="configForms.database.db_type"
                placeholder="选择数据库类型"
              >
                <el-option label="MySQL" value="MySQL" />
                <el-option label="PostgreSQL" value="PostgreSQL" />
                <el-option label="SQLite" value="SQLite" />
                <el-option label="Oracle" value="Oracle" />
                <el-option label="SQL Server" value="SQLServer" />
              </el-select>
            </el-form-item>

            <div class="form-row" v-if="configForms.database.db_type !== 'SQLite'">
              <el-form-item label="主机地址" prop="host">
                <el-input
                  v-model="configForms.database.host"
                  placeholder="数据库主机地址，如: localhost"
                  clearable
                />
              </el-form-item>

              <el-form-item label="端口号" prop="port">
                <el-input-number
                  v-model="configForms.database.port"
                  :min="1"
                  :max="65535"
                  placeholder="端口号"
                  style="width: 100%"
                />
              </el-form-item>
            </div>

            <el-form-item label="数据库名" prop="database">
              <el-input
                v-model="configForms.database.database"
                :placeholder="configForms.database.db_type === 'SQLite' ? 'SQLite文件路径' : '数据库名称'"
                clearable
              />
            </el-form-item>

            <div class="form-row" v-if="configForms.database.db_type !== 'SQLite'">
              <el-form-item label="用户名" prop="user">
                <el-input
                  v-model="configForms.database.user"
                  placeholder="数据库用户名"
                  clearable
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="configForms.database.password"
                  type="password"
                  placeholder="数据库密码"
                  show-password
                  clearable
                />
              </el-form-item>
            </div>

            <div class="form-row">
              <el-form-item label="字符集">
                <el-select
                  v-model="configForms.database.charset"
                  placeholder="选择字符集"
                >
                  <el-option label="utf8" value="utf8" />
                  <el-option label="utf8mb4" value="utf8mb4" />
                  <el-option label="latin1" value="latin1" />
                </el-select>
              </el-form-item>

              <el-form-item label="连接超时(秒)">
                <el-input-number
                  v-model="configForms.database.connection_timeout"
                  :min="5"
                  :max="300"
                  style="width: 100%"
                />
              </el-form-item>
            </div>

            <el-form-item>
              <el-checkbox v-model="configForms.database.ssl">
                使用SSL连接
              </el-checkbox>
            </el-form-item>
          </el-form>

          <!-- 对象存储配置 -->
          <el-form
            v-if="selectedType === 'object_storage'"
            ref="configFormRef"
            :model="configForms.object_storage"
            :rules="objectStorageRules"
            label-position="top"
            class="config-form"
          >
            <el-form-item label="存储桶名称" prop="bucket">
              <el-input
                v-model="configForms.object_storage.bucket"
                placeholder="请输入存储桶名称"
                clearable
              />
            </el-form-item>

            <el-form-item label="端点地址" prop="endpoint">
              <el-input
                v-model="configForms.object_storage.endpoint"
                placeholder="请输入端点地址，如: https://s3.amazonaws.com"
                clearable
              />
            </el-form-item>

            <div class="form-row">
              <el-form-item label="访问密钥" prop="access_key">
                <el-input
                  v-model="configForms.object_storage.access_key"
                  placeholder="Access Key ID"
                  clearable
                />
              </el-form-item>

              <el-form-item label="密钥" prop="secret_key">
                <el-input
                  v-model="configForms.object_storage.secret_key"
                  type="password"
                  placeholder="Secret Access Key"
                  show-password
                  clearable
                />
              </el-form-item>
            </div>

            <div class="form-row">
              <el-form-item label="区域">
                <el-input
                  v-model="configForms.object_storage.region"
                  placeholder="区域名称（可选）"
                  clearable
                />
              </el-form-item>

              <el-form-item>
                <el-checkbox v-model="configForms.object_storage.ssl">
                  使用SSL连接
                </el-checkbox>
              </el-form-item>
            </div>
          </el-form>
        </div>

        <!-- 步骤4: 测试连接 -->
        <div v-if="currentStep === 3" class="step-container">
          <h3>测试连接</h3>
          <div class="test-container">
            <div class="test-info">
              <p>请点击下方按钮测试连接配置是否正确。</p>
              <p>测试成功后即可创建数据源。</p>
            </div>
            
            <el-button 
              type="primary" 
              size="large"
              :loading="testing"
              @click="testConnection"
            >
              <el-icon><Connection /></el-icon>
              {{ testing ? '测试中...' : '测试连接' }}
            </el-button>
            
            <div v-if="testResult" class="test-result">
              <el-result
                :icon="testResult.success ? 'success' : 'error'"
                :title="testResult.success ? '连接成功' : '连接失败'"
                :sub-title="testResult.message"
              >
                <template #extra>
                  <div v-if="testResult.details" class="test-details">
                    <h4>详细信息：</h4>
                    <pre>{{ JSON.stringify(testResult.details, null, 2) }}</pre>
                  </div>
                </template>
              </el-result>
            </div>
          </div>
        </div>
      </div>

      <!-- 按钮组 -->
      <div class="button-group">
        <el-button 
          v-if="currentStep > 0" 
          @click="prevStep"
        >
          上一步
        </el-button>
        
        <el-button 
          v-if="currentStep < 3"
          type="primary" 
          @click="nextStep"
          :disabled="!canProceed"
        >
          下一步
        </el-button>
        
        <el-button 
          v-if="currentStep === 3"
          type="success"
          :disabled="!testResult?.success"
          :loading="dataSourceStore.isCreating"
          @click="createDataSource"
        >
          创建数据源
        </el-button>
        
        <el-button @click="$router.go(-1)">
          取消
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Connection,
  Folder,
  Coin,
  Box
} from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { useDataSourceStore } from '@/stores/datasource'
import type { 
  DataSourceType, 
  CreateDataSourceForm,
  ConnectionTestResult 
} from '@/types/datasource'

const router = useRouter()
const authStore = useAuthStore()
const dataSourceStore = useDataSourceStore()

// 表单引用
const basicFormRef = ref<FormInstance>()
const configFormRef = ref<FormInstance>()
const tagInputRef = ref()

// 响应式数据
const currentStep = ref(0)
const selectedType = ref<DataSourceType>('')
const testing = ref(false)
const testResult = ref<ConnectionTestResult | null>(null)
const tagInputVisible = ref(false)
const tagInputValue = ref('')
const extensionInput = ref('')

// 数据源类型
const dataSourceTypes = [
  {
    value: 'filesystem',
    label: '文件系统',
    description: '浏览本地或网络文件系统中的文件和目录',
    icon: 'Folder'
  },
  {
    value: 'database',
    label: '数据库',
    description: '连接关系型数据库，查看表结构和数据',
    icon: 'Coin'
  },
  {
    value: 'object_storage',
    label: '对象存储',
    description: '连接云对象存储服务，如AWS S3、MinIO等',
    icon: 'Box'
  }
]

// 表单数据
const basicForm = reactive({
  name: '',
  cname: '',
  company: '',
  source: '',
  desc: '',
  tags: [] as string[]
})

const configForms = reactive({
  filesystem: {
    path: '',
    encoding: 'utf-8',
    extensions: [] as string[]
  },
  database: {
    db_type: '',
    host: '',
    port: 3306,
    database: '',
    user: '',
    password: '',
    charset: 'utf8mb4',
    ssl: false,
    connection_timeout: 30
  },
  object_storage: {
    bucket: '',
    endpoint: '',
    access_key: '',
    secret_key: '',
    region: '',
    ssl: true
  }
})

// 验证规则
const basicRules: FormRules = {
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 1, max: 100, message: '名称长度应在 1 到 100 个字符之间', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '名称只能包含字母、数字、下划线和横线', trigger: 'blur' }
  ],
  cname: [
    { required: true, message: '请输入中文名称', trigger: 'blur' },
    { min: 1, max: 100, message: '中文名称长度应在 1 到 100 个字符之间', trigger: 'blur' }
  ]
}

const filesystemRules: FormRules = {
  path: [
    { required: true, message: '请输入文件系统路径', trigger: 'blur' }
  ]
}

const databaseRules: FormRules = {
  db_type: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ],
  database: [
    { required: true, message: '请输入数据库名', trigger: 'blur' }
  ],
  user: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const objectStorageRules: FormRules = {
  bucket: [
    { required: true, message: '请输入存储桶名称', trigger: 'blur' }
  ],
  endpoint: [
    { required: true, message: '请输入端点地址', trigger: 'blur' },
    { pattern: /^https?:\/\//, message: '端点地址必须以http://或https://开头', trigger: 'blur' }
  ],
  access_key: [
    { required: true, message: '请输入访问密钥', trigger: 'blur' }
  ],
  secret_key: [
    { required: true, message: '请输入密钥', trigger: 'blur' }
  ]
}

// 计算属性
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return !!selectedType.value
    case 1:
      return basicForm.name && basicForm.cname
    case 2:
      // 这里应该验证配置表单，简化处理
      return true
    default:
      return false
  }
})

// 方法
const nextStep = async () => {
  if (currentStep.value === 1) {
    if (!basicFormRef.value) return
    const valid = await basicFormRef.value.validate().catch(() => false)
    if (!valid) return
  } else if (currentStep.value === 2) {
    if (!configFormRef.value) return
    const valid = await configFormRef.value.validate().catch(() => false)
    if (!valid) return
  }
  
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
    testResult.value = null
  }
}

const showTagInput = () => {
  tagInputVisible.value = true
  nextTick(() => {
    tagInputRef.value?.focus()
  })
}

const confirmTag = () => {
  if (tagInputValue.value && !basicForm.tags.includes(tagInputValue.value)) {
    basicForm.tags.push(tagInputValue.value)
  }
  tagInputValue.value = ''
  tagInputVisible.value = false
}

const removeTag = (tag: string) => {
  const index = basicForm.tags.indexOf(tag)
  if (index !== -1) {
    basicForm.tags.splice(index, 1)
  }
}

const updateExtensions = () => {
  if (extensionInput.value) {
    const extensions = extensionInput.value
      .split(',')
      .map(ext => ext.trim())
      .filter(ext => ext.length > 0)
    configForms.filesystem.extensions = extensions
  } else {
    configForms.filesystem.extensions = []
  }
}

const testConnection = async () => {
  testing.value = true
  testResult.value = null
  
  try {
    const config = configForms[selectedType.value as keyof typeof configForms]
    const result = await dataSourceStore.testConnection({
      type: selectedType.value,
      config
    })
    testResult.value = result
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.message || '连接测试失败'
    }
  } finally {
    testing.value = false
  }
}

const createDataSource = async () => {
  try {
    const config = configForms[selectedType.value as keyof typeof configForms]
    const createForm: CreateDataSourceForm = {
      ...basicForm,
      type: selectedType.value,
      config
    }
    
    console.log('🚀 CreateDataSource: 准备创建数据源', createForm)
    await dataSourceStore.createDataSource(createForm)
    ElMessage.success('数据源创建成功')
    
    // 创建成功后刷新列表，确保新数据源显示
    console.log('🔄 CreateDataSource: 创建成功，准备刷新列表')
    await dataSourceStore.fetchDataSources()
    console.log('✅ CreateDataSource: 列表已刷新，跳转到列表页面')
    
    router.push('/datasources')
  } catch (error: any) {
    console.error('❌ CreateDataSource: 创建数据源失败', error)
    ElMessage.error(`创建数据源失败：${error.message}`)
  }
}

// 页面标题
document.title = '添加数据源 - 数据浏览系统'
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

.create-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.step-content {
  margin: 40px 0;
  min-height: 400px;
}

.step-container {
  max-width: 800px;
  margin: 0 auto;
}

.step-container h3 {
  text-align: center;
  margin-bottom: 32px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* 类型选择 */
.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin: 32px 0;
}

.type-card {
  border: 2px solid var(--el-border-color);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.type-card:hover {
  border-color: var(--el-color-primary);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.type-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.type-icon {
  color: var(--el-color-primary);
  margin-bottom: 16px;
}

.type-card h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.type-card p {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.4;
}

/* 表单 */
.basic-form,
.config-form {
  max-width: 600px;
  margin: 0 auto;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.tag-item {
  margin-right: 8px;
  margin-bottom: 8px;
}

.tag-input {
  width: 100px;
  margin-right: 8px;
}

/* 测试连接 */
.test-container {
  text-align: center;
  padding: 40px 0;
}

.test-info {
  margin-bottom: 32px;
}

.test-info p {
  margin: 8px 0;
  color: var(--el-text-color-regular);
}

.test-result {
  margin-top: 32px;
}

.test-details {
  text-align: left;
  max-width: 500px;
  margin: 0 auto;
}

.test-details h4 {
  margin: 16px 0 8px 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.test-details pre {
  background: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
}

/* 按钮组 */
.button-group {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--el-border-color-lighter);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
  
  .type-grid {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
  
  .button-group {
    flex-wrap: wrap;
  }
}
</style>
