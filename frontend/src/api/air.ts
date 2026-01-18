import request from './request'

// ============ AIR 模块 API ============

// 工作簿相关
export const createWorkbook = (data: any) => request.post('/api/v1/air/workbooks', data)
export const getWorkbooks = () => request.get('/api/v1/air/workbooks')
export const deleteWorkbook = (id: number) => request.delete(`/api/v1/air/workbooks/${id}`)

// 集成任务相关
export const createIntegrationTask = (data: any) => request.post('/api/v1/air/integration-tasks', data)
export const getIntegrationTasks = () => request.get('/api/v1/air/integration-tasks')
export const toggleIntegrationTask = (id: number) => request.put(`/api/v1/air/integration-tasks/${id}/toggle`)

// 整合规则相关
export const createConsolidationRule = (data: any) => request.post('/api/v1/air/consolidation-rules', data)
export const getConsolidationRules = () => request.get('/api/v1/air/consolidation-rules')

// 数据加速相关
export const createDataAcceleration = (data: any) => request.post('/api/v1/air/accelerations', data)
export const getDataAccelerations = () => request.get('/api/v1/air/accelerations')
export const toggleDataAcceleration = (id: number) => request.put(`/api/v1/air/accelerations/${id}/toggle`)
