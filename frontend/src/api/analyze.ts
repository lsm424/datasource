import request from '@/utils/request'

export interface AnalyzeSession {
  id: string
  userId: string
  resourceKey: string
  resourceDisplayName: string
  datasourceType: string
  datasourceId: string
  createdAt: string
  updatedAt: string
}

export interface AnalyzeMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
}

export const analyzeApi = {
  getOrCreateSession(params: {
    resourceKey: string
    resourceDisplayName: string
    datasourceType: string
    datasourceId: string
  }) {
    return request.post<AnalyzeSession>('/analyze/sessions', params)
  },

  getMessages(sessionId: string) {
    return request.get<{ items: AnalyzeMessage[] }>(`/analyze/sessions/${sessionId}/messages`)
  },

  /** 流式对话：使用 fetch + EventSource 或 fetch 读 stream，此处返回 fetch 的 URL 与 options 供调用方使用 */
  chatStreamUrl(sessionId: string) {
    const token = localStorage.getItem('auth_token')
    return `${import.meta.env.VITE_API_BASE_URL || ''}/api/analyze/sessions/${sessionId}/chat`
  },
}
