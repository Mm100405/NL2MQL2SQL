import request from './request'

// ============ CAN 模块 API ============

// 指标目录相关
export const createMetricCatalog = (data: any) => request.post('/api/v1/can/catalogs', data)
export const getMetricCatalogs = () => request.get('/api/v1/can/catalogs')
export const publishMetric = (id: number) => request.put(`/api/v1/can/catalogs/${id}/publish`)
export const deprecateMetric = (id: number) => request.put(`/api/v1/can/catalogs/${id}/deprecate`)

// 指标应用相关
export const createMetricApplication = (data: any) => request.post('/api/v1/can/applications', data)
export const getMetricApplications = () => request.get('/api/v1/can/applications')

// 指标加速相关
export const createMetricAcceleration = (data: any) => request.post('/api/v1/can/accelerations', data)
export const getMetricAccelerations = () => request.get('/api/v1/can/accelerations')
export const toggleMetricAcceleration = (id: number) => request.put(`/api/v1/can/accelerations/${id}/toggle`)

// 角色相关
export const createSystemRole = (data: any) => request.post('/api/v1/can/roles', data)
export const getSystemRoles = () => request.get('/api/v1/can/roles')

// 审计日志相关
export const getAuditLogs = () => request.get('/api/v1/can/audit-logs')
export const createAuditLog = (data: { user: string; action: string; target: string; details: string }) => 
  request.post('/api/v1/can/audit-logs', data)
