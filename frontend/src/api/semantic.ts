import { request } from './request'
import type {
  DataSource,
  Dataset,
  Metric,
  Dimension,
  DataRelation,
  PaginatedResponse
} from './types'

// ============ 数据源管理 ============
export function getDataSources(): Promise<DataSource[]> {
  return request.get('/semantic/datasources')
}

export function getDataSource(id: string): Promise<DataSource> {
  return request.get(`/semantic/datasources/${id}`)
}

export function createDataSource(data: Partial<DataSource>): Promise<DataSource> {
  return request.post('/semantic/datasources', data)
}

export function updateDataSource(id: string, data: Partial<DataSource>): Promise<DataSource> {
  return request.put(`/semantic/datasources/${id}`, data)
}

export function deleteDataSource(id: string): Promise<void> {
  return request.delete(`/semantic/datasources/${id}`)
}

export function testDataSourceConnection(id: string): Promise<{ success: boolean; message: string }> {
  return request.post(`/semantic/datasources/${id}/test`)
}

export function testConnectionConfig(data: {
  type: string
  connection_config: any
}): Promise<{ success: boolean; message: string }> {
  return request.post('/semantic/datasources/test', data)
}

// ============ 数据集管理 ============
export function getDatasets(params?: { datasource_id?: string }): Promise<Dataset[]> {
  return request.get('/semantic/datasets', { params })
}

export function getDataset(id: string): Promise<Dataset> {
  return request.get(`/semantic/datasets/${id}`)
}

export function createDataset(data: Partial<Dataset>): Promise<Dataset> {
  return request.post('/semantic/datasets', data)
}

export function updateDataset(id: string, data: Partial<Dataset>): Promise<Dataset> {
  return request.put(`/semantic/datasets/${id}`, data)
}

export function deleteDataset(id: string): Promise<void> {
  return request.delete(`/semantic/datasets/${id}`)
}

export function syncDatasetFromSource(datasourceId: string): Promise<Dataset[]> {
  return request.post('/semantic/datasets/sync', { datasource_id: datasourceId })
}

export function syncPhysicalTables(datasourceId: string): Promise<{ message: string; count: number }> {
  return request.post(`/semantic/datasources/${datasourceId}/sync`)
}

// ============ 指标管理 ============
export function getMetrics(params?: { metric_type?: string; dataset_id?: string }): Promise<Metric[]> {
  return request.get('/semantic/metrics', { params })
}

export function getMetric(id: string): Promise<Metric> {
  return request.get(`/semantic/metrics/${id}`)
}

export function createMetric(data: Partial<Metric>): Promise<Metric> {
  return request.post('/semantic/metrics', data)
}

export function updateMetric(id: string, data: Partial<Metric>): Promise<Metric> {
  return request.put(`/semantic/metrics/${id}`, data)
}

export function deleteMetric(id: string): Promise<void> {
  return request.delete(`/semantic/metrics/${id}`)
}

export function validateMetricFormula(formula: string): Promise<{ valid: boolean; message?: string }> {
  return request.post('/semantic/metrics/validate', { formula })
}

// ============ 维度管理 ============
export function getDimensions(params?: { dataset_id?: string; view_id?: string }): Promise<Dimension[]> {
  return request.get('/semantic/dimensions', { params })
}

export function getDimension(id: string): Promise<Dimension> {
  return request.get(`/semantic/dimensions/${id}`)
}

export function createDimension(data: Partial<Dimension>): Promise<Dimension> {
  return request.post('/semantic/dimensions', data)
}

export function updateDimension(id: string, data: Partial<Dimension>): Promise<Dimension> {
  return request.put(`/semantic/dimensions/${id}`, data)
}

export function deleteDimension(id: string): Promise<void> {
  return request.delete(`/semantic/dimensions/${id}`)
}

// ============ 关联关系管理 ============
export function getRelations(): Promise<DataRelation[]> {
  return request.get('/semantic/relations')
}

export function getRelation(id: string): Promise<DataRelation> {
  return request.get(`/semantic/relations/${id}`)
}

export function createRelation(data: Partial<DataRelation>): Promise<DataRelation> {
  return request.post('/semantic/relations', data)
}

export function updateRelation(id: string, data: Partial<DataRelation>): Promise<DataRelation> {
  return request.put(`/semantic/relations/${id}`, data)
}

export function deleteRelation(id: string): Promise<void> {
  return request.delete(`/semantic/relations/${id}`)
}

// ============ 血缘管理 ============
export function getMetricLineage(id: string): Promise<any> {
  return request.get(`/semantic/lineage/metric/${id}`)
}

export function getDatasetLineage(id: string): Promise<any> {
  return request.get(`/semantic/lineage/dataset/${id}`)
}

export function getFullLineageGraph(): Promise<any> {
  return request.get('/semantic/lineage/graph')
}

export function getMetricAllowedDimensions(id: string): Promise<any[]> {
  return request.get(`/semantic/metrics/${id}/allowed-dimensions`)
}

export function getMetricsAllowedDimensions(metricIds: string[]): Promise<any[]> {
  return request.post('/semantic/metrics/allowed-dimensions', metricIds)
}
