<template>
  <div class="semantic-modeling-assistant">
    <a-page-header
      title="AI语义建模"
      subtitle="由 AI 生成视图、维度、指标和字典草案，人工确认后发布为问数主题"
    />

    <a-row :gutter="16" class="content-row">
      <a-col :span="8">
        <a-card title="1. 输入建模目标" :bordered="false">
          <a-form :model="form" layout="vertical">
            <a-form-item label="数据源" required>
              <a-select
                v-model="form.datasource_id"
                placeholder="请选择已同步物理表的数据源"
                allow-search
                @change="handleDatasourceChange"
              >
                <a-option v-for="source in dataSources" :key="source.id" :value="source.id">
                  {{ source.name }}
                </a-option>
              </a-select>
            </a-form-item>

            <a-form-item label="业务目标" required>
              <a-textarea
                v-model="form.business_goal"
                placeholder="例如：基于 stat_info 建立城市案件上报、处置、归档分析主题"
                :auto-size="{ minRows: 4, maxRows: 6 }"
              />
            </a-form-item>

            <a-form-item label="主表（可选）">
              <a-select
                v-model="form.main_table"
                placeholder="不选择则由 AI 根据字段和目标自动判断"
                allow-clear
                allow-search
                :loading="profiling"
              >
                <a-option v-for="table in profiles" :key="table.id" :value="table.physical_name">
                  {{ table.physical_name }}
                  <span class="muted">（{{ table.column_count }}列，评分{{ table.score }}）</span>
                </a-option>
              </a-select>
            </a-form-item>

            <a-form-item label="相关表（可选）">
              <a-select
                v-model="form.related_tables"
                placeholder="MVP 会作为审核参考，暂不自动生成 JOIN"
                multiple
                allow-clear
                allow-search
                :loading="profiling"
              >
                <a-option v-for="table in profiles" :key="table.id" :value="table.physical_name">
                  {{ table.physical_name }}
                </a-option>
              </a-select>
            </a-form-item>

            <a-form-item label="最大字段数">
              <a-input-number v-model="form.max_fields" :min="20" :max="150" style="width: 100%" />
            </a-form-item>

            <a-form-item>
              <a-space direction="vertical" fill>
                <a-checkbox v-model="form.use_llm">使用默认模型润色中文名称和验收问题</a-checkbox>
                <a-button type="primary" long :loading="generating" @click="handleGenerateDraft">
                  <template #icon><icon-thunderbolt /></template>
                  生成语义草案
                </a-button>
              </a-space>
            </a-form-item>
          </a-form>
        </a-card>

        <a-card v-if="profiles.length" title="表识别结果" class="side-card" :bordered="false">
          <a-list :bordered="false" size="small" :max-height="360">
            <a-list-item v-for="table in profiles.slice(0, 12)" :key="table.id">
              <a-list-item-meta :title="table.physical_name">
                <template #description>
                  <div class="profile-desc">
                    <span>{{ table.column_count }} 列</span>
                    <span>评分 {{ table.score }}</span>
                    <span v-if="table.time_columns.length">时间：{{ table.time_columns.slice(0, 2).join('、') }}</span>
                  </div>
                </template>
              </a-list-item-meta>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>

      <a-col :span="16">
        <a-card :bordered="false">
          <template #title>
            <span>2. 审核语义草案</span>
          </template>
          <template #extra>
            <a-space v-if="draft">
              <a-checkbox v-model="setDefault">发布后设为默认视图</a-checkbox>
              <a-button type="primary" status="success" :loading="publishing" @click="handlePublish">
                <template #icon><icon-check /></template>
                发布问数主题
              </a-button>
            </a-space>
          </template>

          <a-empty v-if="!draft" description="请先选择数据源并生成语义草案" />

          <div v-else class="draft-content">
            <a-alert v-if="draft.warnings?.length" type="warning" class="section-alert">
              <template #title>生成提示</template>
              <div v-for="warning in draft.warnings" :key="warning">{{ warning }}</div>
            </a-alert>

            <a-descriptions :column="2" bordered size="small" class="section-block">
              <a-descriptions-item label="业务主题">{{ draft.business_subject }}</a-descriptions-item>
              <a-descriptions-item label="生成方式">{{ generationMethodText }}</a-descriptions-item>
              <a-descriptions-item label="主表">{{ draft.main_dataset.physical_name }}</a-descriptions-item>
              <a-descriptions-item label="分类">{{ draft.category_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="视图名称">{{ draft.view.name }}</a-descriptions-item>
              <a-descriptions-item label="视图显示名">{{ draft.view.display_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="默认时间字段">{{ draft.view.default_time_column || '-' }}</a-descriptions-item>
              <a-descriptions-item label="字段数">{{ draft.view.columns.length }}</a-descriptions-item>
            </a-descriptions>

            <a-tabs default-active-key="fields">
              <a-tab-pane key="fields" title="视图字段">
                <a-table
                  :columns="fieldColumns"
                  :data="draft.view.columns"
                  :pagination="{ pageSize: 10 }"
                  :scroll="{ x: 1000 }"
                  size="small"
                >
                  <template #filterable="{ record }">
                    <a-tag :color="record.filterable ? 'green' : 'gray'">
                      {{ record.filterable ? '可过滤' : '不可过滤' }}
                    </a-tag>
                  </template>
                  <template #value_config="{ record }">
                    <a-tag v-if="record.value_config?.type === 'dict'" color="purple">字典</a-tag>
                    <a-tag v-else color="gray">无</a-tag>
                  </template>
                </a-table>
              </a-tab-pane>

              <a-tab-pane key="dimensions" title="维度">
                <a-table
                  :columns="dimensionColumns"
                  :data="draft.dimensions"
                  :pagination="{ pageSize: 10 }"
                  :scroll="{ x: 900 }"
                  size="small"
                />
              </a-tab-pane>

              <a-tab-pane key="metrics" title="指标">
                <a-table
                  :columns="metricColumns"
                  :data="draft.metrics"
                  :pagination="{ pageSize: 10 }"
                  :scroll="{ x: 900 }"
                  size="small"
                />
              </a-tab-pane>

              <a-tab-pane key="dictionaries" title="字典">
                <a-table
                  :columns="dictionaryColumns"
                  :data="draft.dictionaries"
                  :pagination="{ pageSize: 10 }"
                  size="small"
                />
              </a-tab-pane>

              <a-tab-pane key="sql" title="视图SQL">
                <pre class="sql-preview">{{ draft.view.custom_sql }}</pre>
              </a-tab-pane>

              <a-tab-pane key="questions" title="验收问题">
                <a-list :bordered="false">
                  <a-list-item v-for="question in draft.validation_questions" :key="question">
                    <template #meta>
                      <a-list-item-meta :title="question" />
                    </template>
                  </a-list-item>
                </a-list>
              </a-tab-pane>
            </a-tabs>
          </div>
        </a-card>

        <a-card v-if="publishResult" title="3. 发布结果" class="result-card" :bordered="false">
          <a-result status="success" title="问数主题发布成功">
            <template #subtitle>
              已创建视图 {{ publishResult.view.display_name || publishResult.view.name }}，以及
              {{ publishResult.dimensions.length }} 个维度、{{ publishResult.metrics.length }} 个指标、{{ publishResult.dictionaries.length }} 个字典。
            </template>
            <template #extra>
              <a-space>
                <a-button type="primary" @click="goToViewDesigner">查看视图</a-button>
                <a-button @click="goToAgentQuery">去问数验证</a-button>
              </a-space>
            </template>
          </a-result>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getDataSources } from '@/api/semantic'
import {
  generateSemanticDraft,
  profileSemanticTables,
  publishSemanticDraft,
  type SemanticDraft,
  type SemanticPublishResponse,
  type SemanticTableProfile
} from '@/api/semantic_modeling'
import type { DataSource } from '@/api/types'

const router = useRouter()

const dataSources = ref<DataSource[]>([])
const profiles = ref<SemanticTableProfile[]>([])
const draft = ref<SemanticDraft | null>(null)
const publishResult = ref<SemanticPublishResponse | null>(null)
const profiling = ref(false)
const generating = ref(false)
const publishing = ref(false)
const setDefault = ref(true)

const form = reactive({
  datasource_id: '',
  business_goal: '',
  main_table: '',
  related_tables: [] as string[],
  max_fields: 80,
  use_llm: true
})

const fieldColumns = [
  { title: '字段名', dataIndex: 'name', width: 180 },
  { title: '显示名', dataIndex: 'display_name', width: 160 },
  { title: '类型', dataIndex: 'type', width: 120 },
  { title: '过滤', slotName: 'filterable', width: 100, align: 'center' },
  { title: '值域', slotName: 'value_config', width: 100, align: 'center' },
  { title: '说明', dataIndex: 'description', width: 300 }
]

const dimensionColumns = [
  { title: '维度名', dataIndex: 'name', width: 180 },
  { title: '显示名', dataIndex: 'display_name', width: 160 },
  { title: '字段', dataIndex: 'physical_column', width: 180 },
  { title: '数据类型', dataIndex: 'data_type', width: 100 },
  { title: '维度类型', dataIndex: 'dimension_type', width: 110 },
  { title: '说明', dataIndex: 'description', width: 300 }
]

const metricColumns = [
  { title: '指标名', dataIndex: 'name', width: 180 },
  { title: '显示名', dataIndex: 'display_name', width: 180 },
  { title: '聚合', dataIndex: 'aggregation', width: 100 },
  { title: '度量字段', dataIndex: 'measure_column', width: 180 },
  { title: '单位', dataIndex: 'unit', width: 80 },
  { title: '说明', dataIndex: 'description', width: 300 }
]

const dictionaryColumns = [
  { title: '字典名', dataIndex: 'name', width: 180 },
  { title: '显示名', dataIndex: 'display_name', width: 180 },
  { title: '目标字段', dataIndex: 'target_column', width: 180 },
  { title: '值字段', dataIndex: 'value_column', width: 160 },
  { title: '标签字段', dataIndex: 'label_column', width: 160 },
  { title: '说明', dataIndex: 'description' }
]

const generationMethodText = computed(() => {
  if (!draft.value) return '-'
  return draft.value.generation_method === 'rule_based_with_llm_enrichment' ? '规则生成 + 默认模型润色' : '规则生成'
})

async function loadDataSources() {
  dataSources.value = await getDataSources()
  if (!form.datasource_id && dataSources.value.length) {
    form.datasource_id = dataSources.value[0]?.id || ''
    await loadProfiles()
  }
}

async function loadProfiles() {
  if (!form.datasource_id) return
  profiling.value = true
  try {
    const result = await profileSemanticTables({ datasource_id: form.datasource_id })
    profiles.value = result.tables
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || '加载物理表画像失败')
  } finally {
    profiling.value = false
  }
}

async function handleDatasourceChange() {
  form.main_table = ''
  form.related_tables = []
  draft.value = null
  publishResult.value = null
  await loadProfiles()
}

async function handleGenerateDraft() {
  if (!form.datasource_id) {
    Message.warning('请选择数据源')
    return
  }
  if (!form.business_goal.trim()) {
    Message.warning('请输入业务目标')
    return
  }
  generating.value = true
  publishResult.value = null
  try {
    const result = await generateSemanticDraft({
      datasource_id: form.datasource_id,
      business_goal: form.business_goal.trim(),
      main_table: form.main_table || undefined,
      related_tables: form.related_tables,
      max_fields: form.max_fields,
      use_llm: form.use_llm
    })
    draft.value = result.draft
    Message.success('语义草案已生成，请审核后发布')
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || '生成语义草案失败')
  } finally {
    generating.value = false
  }
}

async function handlePublish() {
  if (!draft.value || !form.datasource_id) return
  publishing.value = true
  try {
    publishResult.value = await publishSemanticDraft({
      datasource_id: form.datasource_id,
      draft: draft.value,
      set_default: setDefault.value
    })
    Message.success('问数主题发布成功')
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || '发布语义配置失败')
  } finally {
    publishing.value = false
  }
}

function goToViewDesigner() {
  if (publishResult.value?.view?.id) {
    router.push(`/management/data/views/${publishResult.value.view.id}`)
  }
}

function goToAgentQuery() {
  router.push('/agent-query')
}

onMounted(loadDataSources)
</script>

<style scoped>
.semantic-modeling-assistant {
  padding: 0;
}

.content-row {
  margin-top: 16px;
}

.side-card,
.result-card {
  margin-top: 16px;
}

.muted {
  color: var(--color-text-3);
  font-size: 12px;
}

.profile-desc {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--color-text-3);
  font-size: 12px;
}

.draft-content {
  min-height: 520px;
}

.section-alert,
.section-block {
  margin-bottom: 16px;
}

.sql-preview {
  margin: 0;
  padding: 16px;
  max-height: 420px;
  overflow: auto;
  border-radius: 4px;
  background: #f7f8fa;
  color: var(--color-text-1);
  font-family: Consolas, Monaco, 'Courier New', monospace;
  line-height: 1.6;
}
</style>
