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
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { analyzeApi } from '@/api/analyze'
import { marked } from 'marked'

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

const isDefaultPrompt = computed(() => (inputText.value || '').trim() === DEFAULT_PROMPT)

function renderMarkdown(text: string) {
  return marked.parse(text || '')
}

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
</style>
