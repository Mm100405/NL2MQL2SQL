import { request } from './request'
import type { DataSource, Dataset, Dimension, Metric } from './types'
import type { FieldDictionary, View } from './views'

export interface SemanticTableProfile {
  id: string
  name: string
  physical_name: string
  schema_name?: string
  description?: string
  column_count: number
  score: number
  time_columns: string[]
  dimension_candidates: string[]
  metric_candidates: string[]
  identifier_candidates: string[]
}

export interface SemanticProfileRequest {
  datasource_id: string
  table_names?: string[]
}

export interface SemanticProfileResponse {
  datasource: DataSource
  tables: SemanticTableProfile[]
}

export interface SemanticDraftRequest {
  datasource_id: string
  business_goal: string
  main_table?: string
  related_tables?: string[]
  max_fields?: number
  use_llm?: boolean
}

export interface SemanticDraftColumn {
  name: string
  source_column?: string
  type?: string
  display_name?: string
  description?: string
  filterable?: boolean
  value_config?: Record<string, any>
}

export interface SemanticDraftDimension {
  name: string
  display_name?: string
  physical_column: string
  data_type: string
  dimension_type: string
  synonyms?: string[]
  description?: string
}

export interface SemanticDraftMetric {
  name: string
  display_name?: string
  aggregation?: string
  measure_column?: string
  unit?: string
  synonyms?: string[]
  description?: string
}

export interface SemanticDraftDictionary {
  name: string
  display_name?: string
  target_column: string
  value_column: string
  label_column: string
  description?: string
}

export interface SemanticDraft {
  business_subject: string
  generation_method: string
  category_name?: string
  datasource: DataSource
  main_dataset: Dataset
  related_datasets?: SemanticTableProfile[]
  view: {
    name: string
    display_name?: string
    view_type: 'sql'
    custom_sql: string
    columns: SemanticDraftColumn[]
    default_time_column?: string
    description?: string
  }
  dimensions: SemanticDraftDimension[]
  metrics: SemanticDraftMetric[]
  dictionaries: SemanticDraftDictionary[]
  validation_questions: string[]
  warnings: string[]
}

export interface SemanticDraftResponse {
  draft: SemanticDraft
  profile: SemanticTableProfile
}

export interface SemanticPublishRequest {
  datasource_id: string
  draft: SemanticDraft
  set_default?: boolean
}

export interface SemanticPublishResponse {
  view: View
  dimensions: Dimension[]
  metrics: Metric[]
  dictionaries: FieldDictionary[]
  validation_questions: string[]
}

export function profileSemanticTables(data: SemanticProfileRequest): Promise<SemanticProfileResponse> {
  return request.post('/semantic-modeling/profile', data)
}

export function generateSemanticDraft(data: SemanticDraftRequest): Promise<SemanticDraftResponse> {
  return request.post('/semantic-modeling/draft', data)
}

export function publishSemanticDraft(data: SemanticPublishRequest): Promise<SemanticPublishResponse> {
  return request.post('/semantic-modeling/publish', data)
}
