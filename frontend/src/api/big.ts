import request from './request'

// ============ BIG 模块 API ============

// 血缘节点相关
export const createLineageNode = (data: any) => request.post('/api/v1/big/lineage-nodes', data)
export const getLineageNodes = () => request.get('/api/v1/big/lineage-nodes')
export const getLineageNode = (nodeId: string) => request.get(`/api/v1/big/lineage-nodes/${nodeId}`)

// 血缘连接相关
export const createLineageConnection = (data: any) => request.post('/api/v1/big/lineage-connections', data)
export const getLineageConnections = () => request.get('/api/v1/big/lineage-connections')

// SQL分析相关
export const analyzeSql = (data: { sql: string; depth: string }) => request.post('/api/v1/big/sql-analysis', data)
export const getSqlAnalyses = () => request.get('/api/v1/big/sql-analysis')

// 血缘图谱相关
export const getLineageGraph = (target: string, direction: string = 'both') => 
  request.get(`/api/v1/big/lineage-graph/${target}`, { params: { direction } })
