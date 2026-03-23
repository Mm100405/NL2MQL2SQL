import { request } from './request'

// ============ 视图类型定义 ============
export interface ViewColumn {
  name: string
  source_table?: string
  source_column?: string
  alias?: string
  type?: string
  description?: string
}

export interface JoinCondition {
  left_column: string
  right_column: string
  operator: string
}

export interface JoinConfig {
  left_table: string
  right_table: string
  join_type: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  conditions: JoinCondition[]
}

export interface TableConfig {
  id: string
  alias: string
  position?: { x: number; y: number }
}

export interface ViewJoinConfig {
  tables: TableConfig[]
  joins: JoinConfig[]
}

export interface View {
  id: string
  name: string
  display_name?: string
  datasource_id: string
  category_id?: string
  category_name?: string
  is_default?: boolean
  view_type: 'single_table' | 'joined' | 'sql'
  base_table_id?: string
  join_config?: ViewJoinConfig
  custom_sql?: string
  columns?: ViewColumn[]
  canvas_config?: any
  description?: string
  created_at: string
  updated_at: string
}

export interface ViewCreate {
  name: string
  display_name?: string
  datasource_id: string
  category_id?: string
  category_name?: string
  view_type: 'single_table' | 'joined' | 'sql'
  base_table_id?: string
  join_config?: ViewJoinConfig
  custom_sql?: string
  columns?: ViewColumn[]
  canvas_config?: any
  description?: string
}

export interface ViewUpdate {
  name?: string
  display_name?: string
  category_id?: string
  category_name?: string
  view_type?: string
  base_table_id?: string
  join_config?: ViewJoinConfig
  custom_sql?: string
  columns?: ViewColumn[]
  canvas_config?: any
  description?: string
}

export interface ViewPreviewResult {
  sql: string
  columns: string[]
  data: any[][]
  total: number
  page: number
  page_size: number
}

export interface PreviewParams {
  limit?: number
  page?: number
  page_size?: number
}

// ============ 字典类型定义 ============
export interface DictMapping {
  value: string
  label: string
  synonyms?: string[]
}

export interface FieldDictionary {
  id: string
  name: string
  display_name?: string
  source_type: 'manual' | 'view_ref' | 'auto'
  mappings?: DictMapping[]
  ref_view_id?: string
  ref_value_column?: string
  ref_label_column?: string
  auto_source_dataset_id?: string
  auto_source_column?: string
  auto_last_sync?: string
  description?: string
  created_at: string
  updated_at: string
}

export interface DictionaryCreate {
  name: string
  display_name?: string
  source_type: 'manual' | 'view_ref' | 'auto'
  mappings?: DictMapping[]
  ref_view_id?: string
  ref_value_column?: string
  ref_label_column?: string
  auto_source_dataset_id?: string
  auto_source_column?: string
  description?: string
}

// ============ 视图 API ============
export function getViews(datasourceId?: string): Promise<View[]> {
  return request.get('/views', { params: { datasource_id: datasourceId } })
}

export function getView(id: string): Promise<View> {
  return request.get(`/views/${id}`)
}

export function createView(data: ViewCreate): Promise<View> {
  return request.post('/views', data)
}

export function updateView(id: string, data: ViewUpdate): Promise<View> {
  return request.put(`/views/${id}`, data)
}

export function deleteView(id: string): Promise<void> {
  return request.delete(`/views/${id}`)
}

export function previewView(id: string, params?: PreviewParams): Promise<ViewPreviewResult> {
  return request.post(`/views/${id}/preview`, {
    limit: params?.limit || 100,
    page: params?.page || 1,
    page_size: params?.page_size || 10
  })
}

export function getViewColumns(id: string): Promise<ViewColumn[]> {
  return request.get(`/views/${id}/columns`)
}

export function generateViewSQL(id: string): Promise<{ sql: string; view_type: string; from_clause: string }> {
  return request.post(`/views/${id}/generate-sql`)
}

export function getViewTables(id: string): Promise<any[]> {
  return request.get(`/views/${id}/tables`)
}

// 可过滤字段接口
export interface FilterableField {
  name: string
  display_name: string
  description?: string
  type?: string
  value_config?: {
    type: string
    values?: string[]
  }
  filter_operators?: string[]
  synonyms?: string[]
  is_time_field?: boolean  // 是否为时间字段
}

export interface FilterableFieldsResponse {
  view_id: string
  view_name: string
  view_display_name?: string
  fields: FilterableField[]
}

// 获取视图可过滤字段列表
export function getFilterableFields(viewId: string): Promise<FilterableFieldsResponse> {
  return request.get(`/views/${viewId}/filterable-fields`)
}

export function getCategoryStats(datasourceId?: string): Promise<{ categories: Array<{ category_id: string | null; category_name: string; view_count: number }> }> {
  return request.get('/views/categories/stats', { params: { datasource_id: datasourceId } })
}

// ============ 视图分类 API ============
export interface ViewCategory {
  id: string
  name: string
  description?: string
  parent_id?: string | null
  created_at: string
  updated_at: string
}

export interface CategoryCreate {
  name: string
  description?: string
  parent_id?: string | null
}

export interface CategoryUpdate {
  name?: string
  description?: string
  parent_id?: string | null
}

export function getCategories(): Promise<ViewCategory[]> {
  return request.get('/views/categories')
}

export function getCategory(id: string): Promise<ViewCategory> {
  return request.get(`/views/categories/${id}`)
}

export function createCategory(data: CategoryCreate): Promise<ViewCategory> {
  return request.post('/views/categories', data)
}

export function updateCategory(id: string, data: CategoryUpdate): Promise<ViewCategory> {
  return request.put(`/views/categories/${id}`, data)
}

export function deleteCategory(id: string): Promise<{ message: string }> {
  return request.delete(`/views/categories/${id}`)
}

export function getCategoryTree(): Promise<any[]> {
  return request.get('/views/categories/tree')
}

export function getDefaultView(): Promise<View | null> {
  return request.get('/views/default')
}

export function setDefaultView(id: string): Promise<View> {
  return request.put(`/views/${id}/default`)
}

// ============ 字典 API ============
export function getDictionaries(sourceType?: string): Promise<FieldDictionary[]> {
  return request.get('/dictionaries', { params: { source_type: sourceType } })
}

export function getDictionary(id: string): Promise<FieldDictionary> {
  return request.get(`/dictionaries/${id}`)
}

export function createDictionary(data: DictionaryCreate): Promise<FieldDictionary> {
  return request.post('/dictionaries', data)
}

export function updateDictionary(id: string, data: Partial<DictionaryCreate>): Promise<FieldDictionary> {
  return request.put(`/dictionaries/${id}`, data)
}

export function deleteDictionary(id: string): Promise<void> {
  return request.delete(`/dictionaries/${id}`)
}

export function getDictionaryValues(id: string): Promise<{ source_type: string; values: DictMapping[] }> {
  return request.get(`/dictionaries/${id}/values`)
}

export function autoGenerateDictionary(params: {
  datasource_id: string
  dataset_id: string
  column_name: string
  dictionary_name: string
  limit?: number
}): Promise<FieldDictionary> {
  return request.post('/dictionaries/auto-generate', params)
}

export function syncDictionary(id: string): Promise<FieldDictionary> {
  return request.post(`/dictionaries/${id}/sync`)
}

export function addDictionaryMapping(id: string, mapping: DictMapping): Promise<FieldDictionary> {
  return request.post(`/dictionaries/${id}/mappings`, mapping)
}

export function deleteDictionaryMapping(id: string, value: string): Promise<FieldDictionary> {
  return request.delete(`/dictionaries/${id}/mappings/${encodeURIComponent(value)}`)
}
