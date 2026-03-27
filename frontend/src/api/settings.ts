import { request } from './request'
import type { ModelConfig, ModelConfigStatus } from './types'

export type { ModelConfig, ModelConfigStatus }

// 获取模型配置列表
export function getModelConfigs(): Promise<ModelConfig[]> {
  return request.get('/settings/model')
}

// 获取模型配置详情
export function getModelConfig(id: string): Promise<ModelConfig> {
  return request.get(`/settings/model/${id}`)
}

// 创建模型配置
export function createModelConfig(data: Partial<ModelConfig>): Promise<ModelConfig> {
  return request.post('/settings/model', data)
}

// 更新模型配置
export function updateModelConfig(id: string, data: Partial<ModelConfig>): Promise<ModelConfig> {
  return request.put(`/settings/model/${id}`, data)
}

// 删除模型配置
export function deleteModelConfig(id: string): Promise<void> {
  return request.delete(`/settings/model/${id}`)
}

// 测试模型连接
export function testModelConnection(id: string): Promise<{ success: boolean; message: string }> {
  return request.post(`/settings/model/${id}/test`)
}

// 设为默认模型
export function activateModelConfig(id: string): Promise<ModelConfig> {
  return request.put(`/settings/model/${id}/activate`)
}

// 获取模型配置状态
export function getModelConfigStatus(): Promise<ModelConfigStatus> {
  return request.get('/settings/model/status')
}

// --- System Settings ---

export interface SystemSetting {
  id: string
  key: string
  value: any
  category: string
  description?: string
  created_at: string
  updated_at: string
}

// 获取系统设置
export function getSystemSettings(category?: string): Promise<SystemSetting[]> {
  return request.get('/settings/system', { params: { category } })
}

// 获取单个系统设置
export function getSystemSetting(key: string): Promise<SystemSetting> {
  return request.get(`/settings/system/${key}`)
}

// 更新系统设置
export function updateSystemSetting(key: string, data: { value: any, description?: string }): Promise<SystemSetting> {
  return request.put(`/settings/system/${key}`, data)
}

// --- LLM 供应商 & 模型动态查询 ---

export interface ProviderGroup {
  key: string
  label: string
}

export interface ProviderConfig {
  group: string
  label: string
  shortLabel: string
  color: string
  needApiKey: boolean
  showApiBase: boolean
  apiBase: string
  popularModels: string[]
}

export interface LLMProvidersResponse {
  groups: ProviderGroup[]
  providers: Record<string, ProviderConfig>
}

// 获取供应商列表
export function getLLMProviders(): Promise<LLMProvidersResponse> {
  return request.get('/settings/llm/providers')
}

// 动态查询供应商可用模型
export function fetchLLMModels(data: {
  provider: string
  api_key?: string
  api_base?: string
}): Promise<{ models: string[]; fallback?: boolean; error?: string }> {
  return request.post('/settings/llm/models', data)
}
