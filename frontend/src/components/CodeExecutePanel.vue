<template>
  <el-drawer
    v-model="visible"
    title="代码执行"
    size="40%"
    :with-header="true"
    class="code-execute-panel"
    destroy-on-close
  >
    <div class="panel-container">
      <!-- 代码展示区域 -->
      <div class="code-section">
        <div class="section-header">
          <span class="section-title">Python 代码</span>
          <div class="section-actions">
            <el-button
              type="primary"
              size="small"
              :loading="executing"
              @click="executeCode"
            >
              <el-icon><VideoPlay /></el-icon>
              运行
            </el-button>
            <el-button size="small" @click="copyCode">
              <el-icon><DocumentCopy /></el-icon>
              复制
            </el-button>
          </div>
        </div>
        <div class="code-editor">
          <pre><code class="language-python">{{ code }}</code></pre>
        </div>
      </div>

      <!-- 控制台输出区域 -->
      <div class="console-section">
        <div class="section-header">
          <span class="section-title">控制台输出</span>
          <div class="section-actions">
            <el-button
              v-if="result?.images?.length"
              type="success"
              size="small"
              @click="showImages = true"
            >
              <el-icon><Picture /></el-icon>
              查看图片 ({{ result.images.length }})
            </el-button>
            <el-button size="small" @click="clearOutput">
              <el-icon><Delete /></el-icon>
              清空
            </el-button>
          </div>
        </div>
        <div class="console-output" ref="consoleRef">
          <div v-if="!result && !executing" class="empty-tip">
            点击"运行"按钮执行代码
          </div>
          <div v-else-if="executing" class="executing-tip">
            <el-icon class="loading-icon"><Loading /></el-icon>
            正在执行代码...
          </div>
          <template v-else>
            <!-- 标准输出 -->
            <div v-if="result?.stdout" class="output-block">
              <div class="output-label">标准输出:</div>
              <pre class="output-content stdout">{{ result.stdout }}</pre>
            </div>
            <!-- 标准错误 -->
            <div v-if="result?.stderr" class="output-block">
              <div class="output-label">错误输出:</div>
              <pre class="output-content stderr">{{ result.stderr }}</pre>
            </div>
            <!-- 异常信息 -->
            <div v-if="result?.error" class="output-block">
              <div class="output-label">异常信息:</div>
              <pre class="output-content error">{{ result.error }}</pre>
            </div>
            <!-- 执行成功但无输出 -->
            <div v-if="result && !result.stdout && !result.stderr && !result.error && !result.images?.length" class="output-block">
              <div class="output-label">执行成功 (无输出)</div>
            </div>
            <!-- 生成的图片 - 显示在控制台输出底部 -->
            <div v-if="result?.images?.length" class="output-block images-output-block">
              <div class="output-label">生成的图片 ({{ result.images.length }}张):</div>
              <div class="images-inline-container">
                <div
                  v-for="(img, idx) in result.images"
                  :key="idx"
                  class="image-inline-item"
                  @click="openImagePreview(idx)"
                >
                  <img :src="`data:image/png;base64,${img}`" :alt="`图片 ${idx + 1}`" />
                  <div class="image-overlay">点击查看大图</div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="showImages"
      title="执行生成的图片"
      width="80%"
      class="image-preview-dialog"
    >
      <div class="images-container">
        <div
          v-for="(img, idx) in result?.images"
          :key="idx"
          class="image-item"
        >
          <div class="image-title">图片 {{ idx + 1 }}</div>
          <img :src="`data:image/png;base64,${img}`" alt="生成的图片" />
        </div>
      </div>
    </el-dialog>

    <!-- 单张图片预览 -->
    <el-dialog
      v-model="showImagePreview"
      title="图片预览"
      width="70%"
      class="single-image-preview-dialog"
      destroy-on-close
    >
      <div class="single-image-container" v-if="result?.images?.length">
        <img
          :src="`data:image/png;base64,${result.images[previewImageIndex]}`"
          :alt="`图片 ${previewImageIndex + 1}`"
        />
        <div class="image-nav" v-if="result.images.length > 1">
          <el-button
            size="small"
            :disabled="previewImageIndex === 0"
            @click="previewImageIndex--"
          >
            上一张
          </el-button>
          <span class="image-counter">{{ previewImageIndex + 1 }} / {{ result.images.length }}</span>
          <el-button
            size="small"
            :disabled="previewImageIndex === result.images.length - 1"
            @click="previewImageIndex++"
          >
            下一张
          </el-button>
        </div>
      </div>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, DocumentCopy, Picture, Delete, Loading } from '@element-plus/icons-vue'
import { codeExecuteApi, type CodeExecuteResponse } from '@/api/codeExecute'

const props = defineProps<{
  modelValue: boolean
  code: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const visible = ref(false)
const executing = ref(false)
const result = ref<CodeExecuteResponse | null>(null)
const showImages = ref(false)
const consoleRef = ref<HTMLElement | null>(null)
const previewImageIndex = ref(0)
const showImagePreview = ref(false)

watch(() => props.modelValue, (v) => {
  visible.value = v
})

watch(visible, (v) => {
  emit('update:modelValue', v)
})

async function executeCode() {
  if (!props.code.trim() || executing.value) return

  executing.value = true
  result.value = null

  try {
    const res = await codeExecuteApi.executeCode({
      code: props.code,
      timeout: 30
    })
    result.value = res
    nextTick(() => scrollToBottom())
  } catch (e: any) {
    ElMessage.error(e?.message || '代码执行失败')
    result.value = {
      success: false,
      stdout: '',
      stderr: '',
      images: [],
      error: e?.message || '执行失败'
    }
  } finally {
    executing.value = false
  }
}

function copyCode() {
  navigator.clipboard.writeText(props.code).then(() => {
    ElMessage.success('代码已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function clearOutput() {
  result.value = null
}

function scrollToBottom() {
  nextTick(() => {
    const el = consoleRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function openImagePreview(index: number) {
  previewImageIndex.value = index
  showImagePreview.value = true
}
</script>

<style scoped>
.panel-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
}

.code-section,
.console-section {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}

.code-section {
  flex: 1;
  min-height: 200px;
}

.console-section {
  flex: 1;
  min-height: 200px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.section-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.section-actions {
  display: flex;
  gap: 8px;
}

.code-editor {
  flex: 1;
  overflow: auto;
  background: #1e1e1e;
  padding: 16px;
}

.code-editor pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.console-output {
  flex: 1;
  overflow: auto;
  background: #0d0d0d;
  padding: 16px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.empty-tip,
.executing-tip {
  color: #666;
  text-align: center;
  padding: 40px 0;
}

.executing-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.output-block {
  margin-bottom: 16px;
}

.output-label {
  color: #888;
  font-size: 12px;
  margin-bottom: 4px;
  text-transform: uppercase;
}

.output-content {
  margin: 0;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
}

.output-content.stdout {
  background: #1a1a1a;
  color: #4ec9b0;
}

.output-content.stderr {
  background: #2d1a1a;
  color: #f48771;
}

.output-content.error {
  background: #2d1a1a;
  color: #f48771;
  border-left: 3px solid #f48771;
}

.images-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  padding: 16px;
}

.image-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.image-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.image-item img {
  max-width: 100%;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

:deep(.code-execute-panel .el-drawer__body) {
  padding: 16px;
  overflow: hidden;
  height: calc(100vh - 80px);
}

:deep(.code-execute-panel.el-drawer) {
  top: 40px;
  height: calc(100vh - 80px);
  border-radius: 8px 0 0 8px;
}

/* 内联图片样式 */
.images-output-block {
  border-top: 1px solid #333;
  padding-top: 12px;
}

.images-inline-container {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 0;
}

.image-inline-item {
  position: relative;
  width: 200px;
  height: 150px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid #444;
  background: #1a1a1a;
}

.image-inline-item img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 12px;
  padding: 4px 8px;
  text-align: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-inline-item:hover .image-overlay {
  opacity: 1;
}

/* 单张图片预览 */
.single-image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.single-image-container img {
  max-width: 100%;
  max-height: 70vh;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.image-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.image-counter {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
</style>
