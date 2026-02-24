<template>
  <div class="database-browser">
    <div class="header">
      <el-breadcrumb>
        <el-breadcrumb-item>
          <router-link to="/datasources">数据源</router-link>
        </el-breadcrumb-item>
        <el-breadcrumb-item>{{ dataSource?.cname || dataSource?.name || '加载中...' }}</el-breadcrumb-item>
        <el-breadcrumb-item v-if="currentTable">{{ currentTable }}</el-breadcrumb-item>
      </el-breadcrumb>
      
      <div class="toolbar">
        <el-button-group>
          <el-button 
            type="primary" 
            icon="Refresh" 
            @click="refreshData"
            :loading="loading"
          >
            刷新
          </el-button>
          <el-button 
            icon="Plus" 
            @click="showCreateDialog = true"
            v-if="currentTable && hasWritePermission"
          >
            新建记录
          </el-button>
        </el-button-group>
      </div>
    </div>

    <div class="content">
      <!-- 数据库结构树 -->
      <div class="sidebar">
        <div class="section-title">
                      <el-icon><Coin /></el-icon>
          数据库结构
        </div>
        
        <el-tree
          :data="dbStructure"
          :props="{ label: 'name', children: 'children' }"
          @node-click="handleNodeClick"
          :expand-on-click-node="false"
          default-expand-all
        >
          <template #default="{ node: _node, data }">
            <span class="tree-node">
              <el-icon v-if="data.type === 'database'"><Coin /></el-icon>
              <el-icon v-else-if="data.type === 'table'"><Grid /></el-icon>
              <el-icon v-else><Document /></el-icon>
              {{ data.name }}
              <span v-if="data.type === 'table' && data.count" class="record-count">
                ({{ data.count }})
              </span>
            </span>
          </template>
        </el-tree>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 表结构视图 -->
        <div v-if="currentTable && showSchema" class="schema-view">
          <el-card class="view-card" shadow="never">
            <template #header>
              <div class="card-header">
                <div class="section-title">
                  <el-icon size="18"><Grid /></el-icon>
                  <span>表结构</span>
                  <el-tag size="small" type="info">{{ currentTable }}</el-tag>
                </div>
                
                <div class="view-controls">
                  <el-button-group size="small">
                    <el-button 
                      :type="showSchema ? '' : 'primary'"
                      @click="showSchema = false"
                    >
                      数据
                    </el-button>
                    <el-button 
                      :type="showSchema ? 'primary' : ''"
                      @click="showSchema = true"
                    >
                      结构
                    </el-button>
                  </el-button-group>
                </div>
              </div>
            </template>
            
            <el-table :data="tableSchema" stripe class="schema-table">
              <el-table-column prop="name" label="字段名" min-width="180">
                <template #default="{ row }">
                  <div class="field-name">
                    <el-icon v-if="row.primary || row.is_primary_key" color="#f56c6c" size="14"><Key /></el-icon>
                    <span>{{ row.name }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="type" label="数据类型" min-width="140">
                <template #default="{ row }">
                  <el-tag size="small" type="success">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="nullable" label="允许为空" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.nullable ? 'info' : 'warning'">
                    {{ row.nullable ? '是' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="default_value" label="默认值" min-width="120">
                <template #default="{ row }">
                  <span class="default-value">{{ row.default_value || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="comment" label="备注" min-width="200">
                <template #default="{ row }">
                  <span class="comment">{{ row.comment || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <!-- 数据视图 -->
        <div v-if="currentTable && !showSchema" class="data-view">
          <el-card class="view-card" shadow="never">
            <template #header>
              <div class="card-header">
                <div class="section-title">
                  <el-icon size="18"><Grid /></el-icon>
                  <span>表数据</span>
                  <el-tag size="small" type="info">{{ currentTable }}</el-tag>
                  <el-tag size="small" type="success" v-if="totalCount > 0">{{ totalCount }} 条记录</el-tag>
                </div>
                
                <div class="view-controls">
                  <el-button-group size="small">
                    <el-button 
                      :type="showSchema ? '' : 'primary'"
                      @click="showSchema = false"
                    >
                      数据
                    </el-button>
                    <el-button 
                      :type="showSchema ? 'primary' : ''"
                      @click="showSchema = true"
                    >
                      结构
                    </el-button>
                  </el-button-group>
                </div>
              </div>
            </template>

            <!-- 查询条件 -->
            <div class="query-controls">
              <div class="query-form">
                <el-form inline>
                  <el-form-item style="margin-bottom: 0;">
                    <div class="query-input-wrapper">
                      <el-input
                        v-model="queryCondition"
                        placeholder="输入 SQL WHERE 条件，例如: id > 10 AND name LIKE '%test%'"
                        clearable
                        size="default"
                        class="query-input"
                      >
                        <template #prepend>
                          <span>WHERE</span>
                        </template>
                      </el-input>
                    </div>
                  </el-form-item>
                  <el-form-item style="margin-bottom: 0;">
                    <el-button type="primary" @click="executeQuery" :loading="loading">
                      <el-icon><Search /></el-icon>
                      查询
                    </el-button>
                    <el-button @click="clearQuery">清空</el-button>
                  </el-form-item>
                </el-form>
              </div>
            </div>

            <!-- 数据表格 -->
            <div class="table-wrapper">
              <el-table 
                :data="tableData" 
                stripe 
                v-loading="loading"
                :max-height="500"
                @row-click="handleRowClick"
                class="data-table"
                empty-text="暂无数据"
              >
                <el-table-column
                  v-for="column in columns"
                  :key="column.name"
                  :prop="column.name"
                  :label="column.name"
                  :min-width="getColumnWidth(column)"
                  show-overflow-tooltip
                >
                  <template #default="{ row }">
                    <div class="cell-content">
                      <span v-if="isJsonColumn(column)" class="json-indicator">
                        <el-tag size="small" type="info">JSON</el-tag>
                      </span>
                      <span v-else class="cell-value">{{ formatValue(row[column.name]) }}</span>
                    </div>
                  </template>
                </el-table-column>
                
                <el-table-column label="操作" width="140" fixed="right" v-if="hasWritePermission">
                  <template #default="{ row, $index }">
                    <div class="action-buttons">
                      <el-button size="small" type="primary" plain @click="editRecord(row)">
                        编辑
                      </el-button>
                      <el-popconfirm
                        title="确认删除这条记录吗？"
                        @confirm="deleteRecord(row, $index)"
                      >
                        <template #reference>
                          <el-button size="small" type="danger" plain>删除</el-button>
                        </template>
                      </el-popconfirm>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 分页 -->
            <div class="pagination-wrapper" v-if="totalCount > 0">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="totalCount"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
                background
              />
            </div>
          </el-card>
        </div>

        <!-- 空状态 -->
        <div v-if="!currentTable" class="empty-state">
          <el-empty description="请选择要查看的表" />
        </div>
      </div>
    </div>

    <!-- 创建/编辑记录对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingRecord ? '编辑记录' : '新建记录'"
      width="60%"
    >
      <el-form :model="recordForm" label-width="120px">
        <el-form-item
          v-for="field in tableSchema"
          :key="field.name"
          :label="field.name"
          :required="!field.nullable && !field.primary"
        >
          <el-input
            v-if="field.type.includes('varchar') || field.type.includes('text')"
            v-model="recordForm[field.name]"
            :placeholder="field.comment"
            :disabled="field.primary && editingRecord"
          />
          <el-input-number
            v-else-if="field.type.includes('int') || field.type.includes('decimal')"
            v-model="recordForm[field.name]"
            :disabled="field.primary && editingRecord"
            style="width: 100%"
          />
          <el-switch
            v-else-if="field.type.includes('boolean')"
            v-model="recordForm[field.name]"
          />
          <el-date-picker
            v-else-if="field.type.includes('date') || field.type.includes('time')"
            v-model="recordForm[field.name]"
            type="datetime"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
          <el-input
            v-else
            v-model="recordForm[field.name]"
            :placeholder="field.comment"
            :disabled="field.primary && editingRecord"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRecord" :loading="saving">
          {{ editingRecord ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Coin, Grid, Document, Key, Search } from '@element-plus/icons-vue'
import { useDataSourceStore } from '@/stores/datasource'
import { useAuthStore } from '@/stores/auth'
import { databaseApi } from '@/api/datasource'

const route = useRoute()
const dataSourceStore = useDataSourceStore()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const saving = ref(false)
const dataSource = ref(null)
const dbStructure = ref([])
const currentTable = ref('')
const showSchema = ref(false)
const tableSchema = ref([])
const tableData = ref([])
const columns = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const queryCondition = ref('')

// 对话框相关
const showCreateDialog = ref(false)
const editingRecord = ref(null)
const recordForm = ref({})

// 计算属性
const hasWritePermission = computed(() => {
  // 简化权限判断：管理员有写权限，其他用户暂时也给予写权限（可根据需求调整）
  return authStore.user?.role === 'admin' || true
})

// 生命周期
onMounted(async () => {
  await loadDataSource()
  await loadDatabaseStructure()
})

// 监听路由变化
watch(() => route.params.id, async (newId) => {
  if (newId) {
    await loadDataSource()
    await loadDatabaseStructure()
  }
})

// 方法
async function loadDataSource() {
  try {
    const id = route.params.id as string
  
    
    const response = await dataSourceStore.fetchDataSourceById(id)
    dataSource.value = response.data

  } catch (error) {
    console.error('❌ 数据库浏览: 数据源加载失败', error)
    ElMessage.error('加载数据源失败')
    
    // 如果API失败，尝试从当前数据源列表中找

    const currentList = dataSourceStore.dataSources

    
    if (Array.isArray(currentList)) {
      const found = currentList.find(ds => ds.id === id)
      if (found) {
        dataSource.value = found

      } else {

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
        console.error('❌ 数据库浏览: 强制获取数据源列表也失败:', fetchError)
      }
    }
  }
}

async function loadDatabaseStructure() {
  try {
    loading.value = true
    
    const id = route.params.id as string
    const response = await databaseApi.getTables(id)
    
    // 防御性检查：确保 response.data 存在且是数组
    let tablesData = null
    if (response.data && Array.isArray(response.data)) {
      tablesData = response.data
    } else if (Array.isArray(response)) {
      // 如果响应直接是数组
      tablesData = response
    } else {
      throw new Error('API响应格式异常')
    }
    
    dbStructure.value = tablesData.map(table => ({
      name: table.name,
      type: 'table',
      children: []
    }))
  } catch (error) {
    console.error('❌ 数据库浏览: 加载数据库结构失败', error)
    ElMessage.error('加载数据库结构失败')
    
    // 使用模拟数据作为后备
    dbStructure.value = [
      {
        name: 'users',
        type: 'table',
        children: []
      },
      {
        name: 'datasources', 
        type: 'table',
        children: []
      }
    ]
  } finally {
    loading.value = false
  }
}

async function handleNodeClick(data: any) {
  if (data.type === 'table') {
    currentTable.value = data.name
    showSchema.value = false
    await Promise.all([
      loadTableSchema(),
      loadTableData()
    ])
  }
}

async function loadTableSchema() {
  try {
    const id = route.params.id as string
    const response = await databaseApi.getTableSchema(id, currentTable.value)
    
    // 防御性检查：确保数据存在
    if (response.data && Array.isArray(response.data)) {
      tableSchema.value = response.data
    } else if (Array.isArray(response)) {
      tableSchema.value = response
    } else {
      tableSchema.value = []
    }
  } catch (error) {
    console.error('❌ 数据库浏览: 加载表结构失败', error)
    ElMessage.error('加载表结构失败')
    
    // 使用模拟数据作为后备
    tableSchema.value = [
      { name: 'id', type: 'int', nullable: false, key: 'PRI' },
      { name: 'name', type: 'varchar(100)', nullable: false, key: '' },
      { name: 'email', type: 'varchar(255)', nullable: true, key: 'UNI' }
    ]
  }
}

async function loadTableData() {
  try {
    loading.value = true
    
    const id = route.params.id as string
    const params: any = {
      page: currentPage.value,
      limit: pageSize.value
    }
    
    if (queryCondition.value) {
      params.where = queryCondition.value
    }
    
    // 获取表数据
    const response = await databaseApi.getTableData(id, currentTable.value, params)
    
    // 检查响应格式并处理数据
    if (Array.isArray(response)) {
      // 直接是数据数组，axios拦截器已解包
      tableData.value = response
      totalCount.value = response.length
      
      // 从数据中推断列信息  
      let rawColumns = []
      if (response.length > 0) {
        rawColumns = Object.keys(response[0])
      }
      
      // 转换为模板期望的对象格式
      columns.value = rawColumns.map(columnName => ({
        name: columnName,
        type: 'string',
        nullable: true
      }))
      
    } else if (typeof response === 'object' && response !== null) {
      // 标准格式响应 {data, total, columns}
      const actualData = response.data || []
      const actualTotal = response.total || 0
      const rawColumns = response.columns || []
      
      tableData.value = Array.isArray(actualData) ? actualData : []
      totalCount.value = typeof actualTotal === 'number' ? actualTotal : 0
      
      // 如果没有获取到列信息，尝试从数据中推断
      let processedColumns = rawColumns
      if (processedColumns.length === 0 && tableData.value.length > 0) {
        processedColumns = Object.keys(tableData.value[0])
      }
      
      // 转换为模板期望的对象格式
      columns.value = processedColumns.map(columnName => ({
        name: columnName,
        type: 'string',
        nullable: true
      }))
      
    } else {
      throw new Error(`未识别的响应格式: ${typeof response}`)
    }
  } catch (error) {
    console.error('❌ 数据库浏览: 加载表数据失败', error)
    ElMessage.error('加载表数据失败')
    
    // 使用模拟数据作为后备
    tableData.value = [
      { id: 1, name: '示例用户1', email: 'user1@example.com' },
      { id: 2, name: '示例用户2', email: 'user2@example.com' }
    ]
    totalCount.value = 2
    // 转换为模板期望的对象格式
    columns.value = ['id', 'name', 'email'].map(columnName => ({
      name: columnName,
      type: 'string',
      nullable: true
    }))
  } finally {
    loading.value = false
  }
}

async function refreshData() {
  if (currentTable.value) {
    await loadTableData()
  } else {
    await loadDatabaseStructure()
  }
}

async function executeQuery() {
  currentPage.value = 1
  await loadTableData()
}

function clearQuery() {
  queryCondition.value = ''
  executeQuery()
}

function handleRowClick(_row: any) {
  // TODO: 实现行点击处理
}

function editRecord(row: any) {
  editingRecord.value = row
  recordForm.value = { ...row }
  showCreateDialog.value = true
}

async function deleteRecord(row: any, _index: number) {
  try {
    loading.value = true

    
    const _id = route.params.id as string
    const _whereCondition = getPrimaryKeyCondition(row)
    
    // TODO: 实现删除记录的API调用

    ElMessage.warning('删除功能待实现')
    
    // 模拟删除成功
    // await databaseApi.deleteRecord(id, currentTable.value, whereCondition)
    // ElMessage.success('删除成功')
    // await loadTableData()
  } catch (error) {
    console.error('❌ 数据库浏览: 删除记录失败', error)
    ElMessage.error('删除失败')
  } finally {
    loading.value = false
  }
}

async function saveRecord() {
  try {
    saving.value = true

    
    const _id = route.params.id as string
    const isUpdate = !!editingRecord.value
    
    if (isUpdate) {
      // TODO: 实现更新记录的API调用

      // await databaseApi.updateRecord(id, currentTable.value, recordForm.value)
      ElMessage.warning('更新功能待实现')
    } else {
      // TODO: 实现插入记录的API调用

      // await databaseApi.insertRecord(id, currentTable.value, recordForm.value)
      ElMessage.warning('创建功能待实现')
    }
    
    // ElMessage.success(isUpdate ? '更新成功' : '创建成功')
    showCreateDialog.value = false
    editingRecord.value = null
    recordForm.value = {}
    // await loadTableData()
  } catch (error) {
    console.error('❌ 数据库浏览: 保存记录失败', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function handleSizeChange(size: number) {
  pageSize.value = size
  loadTableData()
}

function handleCurrentChange(page: number) {
  currentPage.value = page
  loadTableData()
}

function getColumnWidth(column: any): number {
  if (column.type && typeof column.type === 'string') {
    if (column.type.includes('text') || column.type.includes('json')) {
      return 220
    }
    if (column.type.includes('varchar')) {
      return 160
    }
    if (column.type.includes('int') || column.type.includes('decimal')) {
      return 120
    }
    if (column.type.includes('datetime') || column.type.includes('timestamp')) {
      return 160
    }
  }
  return 120
}

function isJsonColumn(column: any): boolean {
  return column.type.includes('json')
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'string' && value.length > 50) {
    return value.substring(0, 50) + '...'
  }
  return String(value)
}

function getPrimaryKeyCondition(row: any): Record<string, any> {
  const condition: Record<string, any> = {}
  tableSchema.value.forEach((field: any) => {
    if (field.primary) {
      condition[field.name] = row[field.name]
    }
  })
  return condition
}
</script>

<style scoped>
.database-browser {
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
  /* padding: 16px; */
  overflow-y: auto;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  padding-bottom: 16px;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

.record-count {
  color: #909399;
  font-size: 12px;
}

/* 卡片样式 */
.view-card {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  margin: 0;
  padding: 0;
}

.card-header .section-title span {
  color: #303133;
}

/* 查询控件样式 */
.query-controls {
  margin-bottom: 20px;
  padding: 0;
  background: transparent;
}

.query-form {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.query-input-wrapper {
  min-width: 400px;
}

.query-input {
  min-width: 400px;
}

:deep(.query-input .el-input-group__prepend) {
  background: #409eff;
  color: white;
  font-weight: 500;
  border-color: #409eff;
}

/* 表格样式 */
.table-wrapper {
  margin: 20px 0;
}

.data-table, .schema-table {
  border-radius: 6px;
  overflow: hidden;
}

.field-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.cell-content {
  display: flex;
  align-items: center;
}

.cell-value {
  color: #606266;
}

.default-value, .comment {
  color: #909399;
  font-size: 13px;
}

.json-indicator {
  display: flex;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* 分页样式 */
.pagination-wrapper {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: center;
}

/* 空状态 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

/* Element Plus 样式覆盖 */
:deep(.el-tree-node__content) {
  height: 32px;
}

:deep(.el-table th) {
  background-color: #fafafa;
  font-weight: 600;
  color: #606266;
}

:deep(.el-table .el-table__row) {
  transition: background-color 0.2s;
}

:deep(.el-table .el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #fafbfc;
}

:deep(.el-card__body) {
  padding: 20px;
}

:deep(.el-pagination) {
  font-weight: normal;
}

:deep(.el-pagination .btn-next), 
:deep(.el-pagination .btn-prev) {
  border-radius: 4px;
}

:deep(.el-pagination .el-pager li) {
  border-radius: 4px;
  margin: 0 2px;
}
</style>
