import { request } from './request'

/**
 * 生成数据格式配置请求
 */
export interface GenerateConfigRequest {
  natural_language: string
  target_format_example: Record<string, any>
  api_parameters: string
  // 可选的前置查询结果，避免重复执行
  existing_mql?: Record<string, any>  // 前面 generate-mql 的返回 mql
  existing_sql?: string  // 前面 mql2sql 的返回 sql
  existing_query_result?: {  // 前面 execute 的返回结果（包含样本数据）
    columns: string[]
    data: any[][]
    total_count: number
    execution_time: number
  }
}

/**
 * 生成数据格式配置
 */
export function generateDataFormatConfig(data: GenerateConfigRequest) {
  return request.post('/data-format/generate-config', data, { timeout: 120000 })
}

/**
 * 获取所有数据格式配置
 */
export function getDataFormatConfigs() {
  return request.get('/data-format/configs')
}

/**
 * 获取单个数据格式配置
 */
export function getDataFormatConfig(configId: string) {
  return request.get(`/data-format/configs/${configId}`)
}

/**
 * 更新数据格式配置
 */
export function updateDataFormatConfig(configId: string, data: { name?: string; status?: string }) {
  return request.put(`/data-format/configs/${configId}`, data)
}

/**
 * 删除数据格式配置
 */
export function deleteDataFormatConfig(configId: string) {
  return request.delete(`/data-format/configs/${configId}`)
}

/**
 * 调用自定义API
 */
export function callCustomApi(configId: string, params: Record<string, any>) {
  return request.post(`/data-format/custom/${configId}`, params)
}

/**
 * 获取自定义API文档
 */
export function getCustomApiDocs(configId: string) {
  return request.get(`/data-format/custom/${configId}/docs`)
}

/**
 * 获取可用的参数列表
 */
export function getAvailableParameters(viewId?: string) {
  return request.get('/data-format/parameters/available', { params: { view_id: viewId } })
}

/**
 * 重新生成数据格式配置
 */
export function regenerateDataFormatConfig(configId: string) {
  return request.post(`/data-format/configs/${configId}/regenerate`)
}
