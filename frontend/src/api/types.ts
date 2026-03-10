// 通用响应类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页请求参数
export interface PaginationParams {
  page?: number
  page_size?: number
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 数据源类型
export type DataSourceType = string

// 数据源
export interface DataSource {
  id: string
  name: string
  type: string
  connection_config: {
    host?: string
    port?: number
    database: string
    username?: string
    password?: string
  }
  status: string
  created_at: string
  updated_at: string
}

// 数据集
export interface Dataset {
  id: string
  datasource_id: string
  name: string
  physical_name: string
  schema_name?: string
  columns: ColumnInfo[]
  description?: string
  created_at: string
  updated_at: string
}

// 列信息
export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  comment?: string
}

// 通用列信息（用于选择下拉）
export interface CommonColumnInfo {
  name: string
  type?: string
  comment?: string
  description?: string
}

// 指标类型
export type MetricType = 'basic' | 'derived' | 'composite'

// 聚合函数
export type AggregationType = 'SUM' | 'COUNT' | 'AVG' | 'MAX' | 'MIN' | 'COUNT_DISTINCT'

// 指标
export interface Metric {
  id: string
  name: string
  display_name: string
  metric_type: MetricType
  source_type?: 'physical' | 'view'  // 数据来源类型
  dataset_id?: string
  view_id?: string  // 视图ID
  aggregation?: AggregationType
  calculation_method?: 'field' | 'expression'
  measure_column?: string
  calculation_formula?: string
  is_semi_additive?: any
  date_column_id?: string
  base_metric_id?: string
  derivation_type?: string
  time_constraint?: string
  analysis_dimensions?: string[]
  filters?: MetricFilter[]
  synonyms?: string[]
  unit?: string
  format?: string
  description?: string
  created_at: string
  updated_at: string
}

// 指标过滤条件
export interface MetricFilter {
  field: string
  operator: string
  value: any
}

// 维度类型
export type DimensionType = 'time' | 'geo' | 'normal' | 'categorical' | 'numerical' | 'user_defined'

// 维度
export interface Dimension {
  id: string
  source_type?: 'physical' | 'view'  // 数据来源类型
  dataset_id: string
  view_id?: string  // 视图ID
  name: string
  display_name: string
  physical_column: string
  data_type: 'string' | 'number' | 'date' | 'datetime'
  dimension_type: DimensionType
  hierarchy?: DimensionHierarchy
  format_config?: {
    default_format?: string
    options?: string[]
  }
  synonyms?: string[]
  description?: string
  created_at: string
  updated_at: string
}

// 维度层级
export interface DimensionHierarchy {
  levels: string[]
}

// 数据关联
export interface DataRelation {
  id: string
  left_dataset_id: string
  right_dataset_id: string
  join_type: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  join_conditions: JoinCondition[]
  relationship_type: '1:1' | '1:N' | 'N:M'
  description?: string
  created_at: string
}

// 关联条件
export interface JoinCondition {
  left_column: string
  right_column: string
  operator: '='
}

// 分析步骤
export interface AnalysisStep {
  title: string
  content: string
  status: 'success' | 'loading' | 'pending' | 'error'
}

// 查询历史
export interface QueryHistory {
  id: string
  conversation_id?: string  // 对话ID，用于对话历史记录
  natural_language: string
  mql_query: any
  sql_query: string
  execution_time: number
  result_count: number
  status: 'success' | 'failed' | 'timeout'
  error_message?: string
  chart_config?: ChartConfig
  created_at: string
  messages?: any[]  // 完整对话消息历史
}

// 图表配置
export interface ChartConfig {
  type: 'line' | 'bar' | 'pie' | 'table'
  x_axis?: string
  y_axis?: string[]
  title?: string
}

// 模型提供商
export type ModelProvider = string

// 模型配置
export interface ModelConfig {
  id: string
  name: string
  provider: string
  model_name: string
  api_key?: string
  api_base?: string
  is_active: boolean
  is_default: boolean
  config_params?: {
    temperature?: number
    max_tokens?: number
    [key: string]: any
  }
  created_at: string
  updated_at: string
}

// 模型配置状态
export interface ModelConfigStatus {
  is_configured: boolean
  default_model?: ModelConfig
}

// 查询请求
export interface QueryRequest {
  natural_language: string
  context?: {
    dataset_ids?: string[]
    user_history?: string[]
    suggested_metrics?: string[]
    suggested_dimensions?: string[]
    quoted_mql?: any
  }
}

// NL转MQL响应
export interface NL2MQLResponse {
  mql: any
  steps: AnalysisStep[]
  confidence: number
  interpretation: string
}

// MQL转SQL响应
export interface MQL2SQLResponse {
  sql: string
  datasources: string[]
  lineage?: any
}

// 查询执行响应
export interface QueryExecuteResponse {
  columns: string[]
  data: any[][]
  total_count: number
  execution_time: number
  chart_recommendation?: string
}

// 完整查询响应
export interface FullQueryResponse {
  natural_language: string
  mql: any
  sql: string
  result: QueryExecuteResponse
  steps: AnalysisStep[]
  query_id: string
  viewType?: 'table' | 'chart'
}
