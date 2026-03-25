import { request } from './request'
import type {
  QueryRequest,
  NL2MQLResponse,
  MQL2SQLResponse,
  QueryExecuteResponse,
  QueryHistory,
  PaginatedResponse
} from './types'

// 分析意图
export function analyzeIntent(data: QueryRequest): Promise<any> {
  return request.post('/query/analyze-intent', data)
}

// 生成MQL
export function generateMQL(data: QueryRequest): Promise<NL2MQLResponse> {
  return request.post('/query/generate-mql', data)
}

// MQL转SQL
export function mql2sql(mql: string): Promise<MQL2SQLResponse> {
  return request.post('/query/mql2sql', { mql })
}

// 执行SQL
export function executeSQL(params: {
  sql: string
  datasource_id: string
  limit?: number
}): Promise<QueryExecuteResponse> {
  return request.post('/query/execute', params)
}

// 开始新的对话
export function startConversation(): Promise<{ conversation_id: string }> {
  return request.post('/query/conversation/start')
}

// 保存对话历史
export function saveConversationHistory(conversation_id: string, messages: any[]): Promise<any> {
  return request.post(`/query/conversation/${conversation_id}/save`, { messages })
}

// 获取对话历史
export function getConversationHistory(conversation_id: string): Promise<any> {
  return request.get(`/query/conversation/${conversation_id}`)
}

// 获取查询历史
export function getQueryHistory(params?: {
  page?: number
  page_size?: number
}): Promise<PaginatedResponse<QueryHistory>> {
  return request.get('/query/history', { params })
}

// 获取单条查询历史详情
export function getQueryHistoryDetail(id: string): Promise<QueryHistory> {
  return request.get(`/query/history/${id}`)
}

// 删除查询历史
export function deleteQueryHistory(id: string): Promise<void> {
  return request.delete(`/query/history/${id}`)
}

// 解析时间范围
export function parseTimeRanges(params: {
  mql?: any
  filters?: any
}): Promise<any> {
  return request.post('/agent/parse-time-ranges', params)
}

