import { request } from './request'
import type {
  QueryRequest,
  NL2MQLResponse,
  MQL2SQLResponse,
  QueryExecuteResponse,
  FullQueryResponse,
  QueryHistory,
  PaginatedResponse
} from './types'

// NL转MQL
export function nl2mql(data: QueryRequest): Promise<NL2MQLResponse> {
  return request.post('/query/nl2mql', data)
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

// 端到端查询（NL直接到结果）
export function executeFullQuery(data: QueryRequest): Promise<FullQueryResponse> {
  return request.post('/query/nl2result', data)
}

// 下钻分析
export function drillDown(params: {
  query_id: string
  drill_dimension: string
  filter?: Record<string, any>
}): Promise<FullQueryResponse> {
  return request.post('/query/drill-down', params)
}

// 归因分析
export function attribution(params: {
  metric: string
  dimensions: string[]
  date_range?: { start: string; end: string }
}): Promise<any> {
  return request.post('/query/attribution', params)
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
