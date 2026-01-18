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
