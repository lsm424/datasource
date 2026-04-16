<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`AI对话：${resourceDisplayName}`"
    width="720px"
    class="resource-analyze-dialog"
    destroy-on-close
    @closed="onClosed"
  >
    <div class="analyze-body">
      <div class="messages" ref="messagesRef">
        <template v-for="(msg, idx) in displayMessages" :key="msg.id || idx">
          <div :class="['msg-row', msg.role]">
            <div class="msg-bubble">
              <!-- 支持 Markdown 渲染 -->
              <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
              <div class="msg-time">{{ formatTime(msg.createdAt) }}</div>
            </div>
          </div>
        </template>
        <div v-if="streaming" class="msg-row assistant">
          <div class="msg-bubble">
            <div class="msg-content">
              <span v-html="renderMarkdown(streamingContent)"></span>
              <el-icon class="cursor-blink"><Loading /></el-icon>
            </div>
          </div>
        </div>
      </div>
      <div class="input-area" :class="{ 'is-default-prompt': isDefaultPrompt }">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder=""
          :disabled="streaming"
          @keydown.enter.exact.prevent="send"
        />
        <el-button type="primary" :loading="streaming" @click="send" class="send-btn">发送</el-button>
      </div>
    </div>
  </el-dialog>

  <!-- 代码执行侧边面板 -->
  <CodeExecutePanel v-model="codePanelVisible" :code="selectedCode" />
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, VideoPlay, DocumentCopy } from '@element-plus/icons-vue'
import { analyzeApi } from '@/api/analyze'
import { marked } from 'marked'
import CodeExecutePanel from './CodeExecutePanel.vue'

const DEFAULT_PROMPT = '请帮我分析/解读这个数据/图片/视频'

const props = defineProps<{
  visible: boolean
  resourceKey: string
  resourceDisplayName: string
  datasourceType: string
  datasourceId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
}>()

const dialogVisible = ref(false)
const sessionId = ref<string | null>(null)
const displayMessages = ref<Array<{ id: string; role: string; content: string; createdAt: string }>>([])
const inputText = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const messagesRef = ref<HTMLElement | null>(null)
const codePanelVisible = ref(false)
const selectedCode = ref('')

const isDefaultPrompt = computed(() => (inputText.value || '').trim() === DEFAULT_PROMPT)

// 自定义渲染器，为代码块添加操作按钮
const renderer = new marked.Renderer()
renderer.code = (codeObj: any) => {
  // 兼容新旧版本的 marked
  const code = typeof codeObj === 'string' ? codeObj : (codeObj.text || codeObj.code || '')
  const lang = typeof codeObj === 'string' ? '' : (codeObj.lang || codeObj.language || 'text')
  const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const isPython = lang === 'python' || lang === 'py'

  let actions = ''
  if (isPython) {
    actions = `
      <div class="code-actions">
        <button class="code-action-btn run" onclick="window.runPythonCode(this)" data-code="${encodeURIComponent(code)}">
          <svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M128 128v768h768V128H128zm64 64h640v640H192V192zm160 160l320 160-320 160V352z"/></svg>
          运行
        </button>
        <button class="code-action-btn copy" onclick="window.copyCode(this)" data-code="${encodeURIComponent(code)}">
          <svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M832 64H296c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h496v688c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8V96c0-17.7-14.3-32-32-32zM704 192H192c-17.7 0-32 14.3-32 32v530.7c0 8.5 3.4 16.6 9.4 22.6l173.3 173.3c2.8 2.8 6.3 4.1 9.8 4.1h416c17.7 0 32-14.3 32-32V224c0-17.7-14.3-32-32-32z"/></svg>
          复制
        </button>
      </div>
    `
  }

  return `
    <div class="code-block-wrapper">
      <div class="code-block-header">
        <span class="code-language">${lang}</span>
        ${actions}
      </div>
      <pre class="code-block"><code class="language-${lang}">${escapedCode}</code></pre>
    </div>
  `
}

marked.setOptions({ renderer })

function renderMarkdown(text: string) {
  return marked.parse(text || '')
}

// 全局函数供代码块按钮调用
onMounted(() => {
  (window as any).runPythonCode = (btn: HTMLButtonElement) => {
    const code = decodeURIComponent(btn.getAttribute('data-code') || '')
    if (code) {
      selectedCode.value = code
      codePanelVisible.value = true
    }
  }

  (window as any).copyCode = (btn: HTMLButtonElement) => {
    const code = decodeURIComponent(btn.getAttribute('data-code') || '')
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        ElMessage.success('代码已复制到剪贴板')
      }).catch(() => {
        ElMessage.error('复制失败')
      })
    }
  }
})

watch(() => props.visible, async (v) => {
  dialogVisible.value = v
  if (v && props.resourceKey) {
    inputText.value = DEFAULT_PROMPT
    await openSession()
  }
}, { immediate: true })

watch(dialogVisible, (v) => {
  emit('update:visible', v)
})

function formatTime(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function openSession() {
  try {
    const res: any = await analyzeApi.getOrCreateSession({
      resourceKey: props.resourceKey,
      resourceDisplayName: props.resourceDisplayName,
      datasourceType: props.datasourceType,
      datasourceId: props.datasourceId
    })
    const data = res && typeof res === 'object' ? res : {}
    sessionId.value = data.id ?? data.session_id ?? null
    if (sessionId.value) {
      const msgRes: any = await analyzeApi.getMessages(sessionId.value)
      const raw = msgRes && typeof msgRes === 'object' ? msgRes : {}
      const items = Array.isArray(raw.items) ? raw.items : []
      displayMessages.value = items.map((m: any) => ({
        id: m.id,
        role: m.role || 'user',
        content: m.content || '',
        createdAt: m.createdAt ?? m.created_at ?? ''
      }))
      // 打开对话框后，自动滚动到历史记录底部
      scrollToBottom()
    } else {
      displayMessages.value = []
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '获取会话失败')
    displayMessages.value = []
  }
}

async function send() {
  const text = (inputText.value || '').trim()
  if (!text || !sessionId.value || streaming.value) return

  displayMessages.value = [...displayMessages.value, { id: '', role: 'user', content: text, createdAt: new Date().toISOString() }]
  inputText.value = ''
  streaming.value = true
  streamingContent.value = ''

  const token = localStorage.getItem('auth_token')
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  const url = `${origin}/api/analyze/sessions/${sessionId.value}/chat`

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token || ''}`
      },
      body: JSON.stringify({ content: text })
    })
    if (!response.ok) {
      const err = await response.text()
      const msg = err || `请求失败 (${response.status})`
      throw new Error(msg)
    }
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    if (reader) {
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const json = JSON.parse(line.slice(6))
              if (json.content) streamingContent.value += json.content
              if (json.error) streamingContent.value += '\n' + json.error
            } catch (_) {}
          }
        }
      }
    }
    displayMessages.value = [...displayMessages.value, { id: '', role: 'assistant', content: streamingContent.value, createdAt: new Date().toISOString() }]
  } catch (e: any) {
    const msg = e?.message || '发送失败'
    if (msg.includes('fetch') || msg.includes('Failed to fetch')) {
      ElMessage.error('网络请求失败，请确认后端服务已启动且地址正确')
    } else {
      ElMessage.error(msg)
    }
    displayMessages.value = [...displayMessages.value, { id: '', role: 'assistant', content: '[错误] ' + msg, createdAt: new Date().toISOString() }]
  } finally {
    streaming.value = false
    streamingContent.value = ''
    nextTick(() => scrollToBottom())
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function onClosed() {
  sessionId.value = null
  displayMessages.value = []
  inputText.value = DEFAULT_PROMPT
  streamingContent.value = ''
}
</script>

<style scoped>
.resource-analyze-dialog :deep(.el-dialog) {
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.resource-analyze-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 16px 20px;
}
.resource-analyze-dialog :deep(.el-dialog__body) {
  padding: 16px 20px 20px;
  border-radius: 0 0 12px 12px;
}
.analyze-body {
  display: flex;
  flex-direction: column;
  min-height: 360px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-blank);
}
.messages {
  flex: 1;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
}
.msg-row {
  display: flex;
  margin-bottom: 12px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--el-fill-color-light);
}
.msg-row.user .msg-bubble {
  background: var(--el-color-primary-light-9);
}
.msg-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4 !important;
}
.msg-content :deep(p),
.msg-content :deep(ul),
.msg-content :deep(ol),
.msg-content :deep(li),
.msg-content :deep(h1),
.msg-content :deep(h2),
.msg-content :deep(h3),
.msg-content :deep(h4),
.msg-content :deep(h5),
.msg-content :deep(h6) {
  margin-top: 2px !important;
  margin-bottom: 2px !important;
  line-height: 1.4 !important;
}
.msg-content :deep(ul),
.msg-content :deep(ol) {
  padding-left: 16px !important;
}
.msg-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.cursor-blink {
  animation: blink 0.8s infinite;
}
@keyframes blink {
  50% { opacity: 0.3; }
}
.input-area {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.input-area :deep(.el-textarea__inner) {
  border-radius: 8px;
}
.input-area.is-default-prompt :deep(.el-textarea__inner) {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
}
.input-area .el-textarea {
  flex: 1;
}
.send-btn {
  flex-shrink: 0;
}

/* 代码块样式 */
.msg-content :deep(.code-block-wrapper) {
  margin: 8px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

.msg-content :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #2d2d2d;
  border-bottom: 1px solid #3d3d3d;
}

.msg-content :deep(.code-language) {
  font-size: 12px;
  color: #888;
  text-transform: uppercase;
  font-weight: 500;
}

.msg-content :deep(.code-actions) {
  display: flex;
  gap: 6px;
}

.msg-content :deep(.code-action-btn) {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  font-size: 11px;
  line-height: 1.4;
  color: #ccc;
  background: #3d3d3d;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  height: 22px;
}

.msg-content :deep(.code-action-btn svg) {
  width: 12px;
  height: 12px;
}

.msg-content :deep(.code-action-btn:hover) {
  background: #4d4d4d;
  color: #fff;
}

.msg-content :deep(.code-action-btn.run) {
  background: var(--el-color-primary);
  color: #fff;
}

.msg-content :deep(.code-action-btn.run:hover) {
  background: var(--el-color-primary-light-3);
}

.msg-content :deep(.code-block) {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  background: #1e1e1e;
}

.msg-content :deep(.code-block code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre;
}

/* 代码高亮颜色 */
.msg-content :deep(.code-block .language-python) {
  color: #d4d4d4;
}
</style>
