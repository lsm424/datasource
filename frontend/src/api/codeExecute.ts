import request from '@/utils/request'

export interface CodeExecuteRequest {
  code: string
  timeout?: number
}

export interface CodeExecuteResponse {
  success: boolean
  stdout: string
  stderr: string
  images: string[]
  error: string | null
}

export const codeExecuteApi = {
  executeCode(params: CodeExecuteRequest) {
    return request.post<CodeExecuteResponse>('/code/execute', params)
  }
}
