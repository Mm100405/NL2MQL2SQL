<template>
  <div class="metric-list">
    <a-card title="指标管理">
      <template #extra>
        <a-space>
          <a-radio-group v-model="filterType" type="button">
            <a-radio value="">全部</a-radio>
            <a-radio value="basic">基础指标</a-radio>
            <a-radio value="derived">派生指标</a-radio>
            <a-radio value="composite">复合指标</a-radio>
          </a-radio-group>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><icon-plus /></template>
            新增指标
          </a-button>
        </a-space>
      </template>

      <a-table :columns="columns" :data="filteredMetrics" :loading="loading">
        <template #metric_type="{ record }">
          <a-tag :color="getTypeColor(record.metric_type)">
            {{ getTypeLabel(record.metric_type) }}
          </a-tag>
        </template>
        <template #aggregation="{ record }">
          <a-tag v-if="record.aggregation">{{ record.aggregation }}</a-tag>
          <span v-else>-</span>
        </template>
        <template #analysis_dimensions="{ record }">
          <a-tag v-if="record.analysis_dimensions?.length" color="arcoblue">
            {{ record.analysis_dimensions.length }} 个维度
          </a-tag>
          <span v-else style="color: var(--color-text-4)">未配置</span>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="handleViewLineage(record)">
              血缘
            </a-button>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
            </a-button>
            <a-popconfirm content="确定删除此指标？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
                <template #icon><icon-delete /></template>
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑指标' : '新增指标'"
      :width="900"
      :ok-loading="submitting"
      @ok="handleSubmit"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-row :gutter="24">
          <!-- 左侧配置区 -->
          <a-col :span="16">
            <a-form-item field="metric_type" label="指标类型">
              <a-radio-group v-model="form.metric_type" type="button">
                <a-radio value="basic">基础指标</a-radio>
                <a-radio value="derived">派生指标</a-radio>
                <a-radio value="composite">复合指标</a-radio>
              </a-radio-group>
            </a-form-item>

            <!-- 1. 基础指标配置 -->
            <template v-if="form.metric_type === 'basic'">
              <a-form-item field="dataset_id" label="数据集" required>
                <a-select v-model="form.dataset_id" placeholder="选择数据集">
                  <a-option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
                </a-select>
              </a-form-item>

              <a-form-item label="统计方式">
                <a-radio-group v-model="form.calculation_method">
                  <a-radio value="field">使用字段</a-radio>
                  <a-radio value="expression">使用表达式</a-radio>
                </a-radio-group>
              </a-form-item>

              <template v-if="form.calculation_method === 'field'">
                <a-row :gutter="16">
                  <a-col :span="12">
                    <a-form-item field="aggregation" label="聚合函数">
                      <a-select v-model="form.aggregation">
                        <a-option value="SUM">SUM</a-option>
                        <a-option value="COUNT">COUNT</a-option>
                        <a-option value="AVG">AVG</a-option>
                        <a-option value="MAX">MAX</a-option>
                        <a-option value="MIN">MIN</a-option>
                        <a-option value="COUNT_DISTINCT">COUNT_DISTINCT</a-option>
                      </a-select>
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item field="measure_column" label="度量字段" required>
                      <a-input v-model="form.measure_column" placeholder="输入物理字段名" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </template>

              <template v-else>
                <a-form-item field="calculation_formula" label="计算表达式">
                  <a-textarea
                    v-model="form.calculation_formula"
                    placeholder="输入SQL聚合表达式，如：sum(if(type='A', amount, 0))"
                    :auto-size="{ minRows: 4 }"
                  />
                </a-form-item>
              </template>

              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="指标日期标识">
                    <a-select v-model="form.date_column_id" placeholder="选择日期字段">
                      <a-option v-for="d in currentDatasetDimensions" :key="d.id" :value="d.id">{{ d.name }}</a-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="半累加指标">
                    <a-switch v-model="form.is_semi_additive.enabled" />
                    <a-select v-if="form.is_semi_additive.enabled" v-model="form.is_semi_additive.type" style="margin-left: 8px; width: 120px">
                      <a-option value="last_value">期末值</a-option>
                      <a-option value="first_value">期初值</a-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>
            </template>

            <!-- 2. 派生指标配置 -->
            <template v-else-if="form.metric_type === 'derived'">
              <a-form-item field="base_metric_id" label="基础/复合指标" required>
                <a-select v-model="form.base_metric_id" placeholder="选择原始指标">
                  <a-option v-for="m in metrics.filter(x => x.metric_type !== 'derived')" :key="m.id" :value="m.id">
                    {{ m.display_name || m.name }}
                  </a-option>
                </a-select>
              </a-form-item>

              <a-form-item label="时间限定">
                <a-input v-model="form.time_constraint" placeholder="如：LAST_30_DAYS" />
              </a-form-item>

              <a-form-item label="业务限定">
                <a-button type="outline" size="small" @click="addFilter"><template #icon><icon-plus /></template>添加筛选条件</a-button>
                <div v-for="(f, i) in form.filters" :key="i" class="filter-item" style="margin-top: 8px; display: flex; gap: 8px">
                   <a-input v-model="f.field" placeholder="字段" style="width: 100px" />
                   <a-select v-model="f.operator" style="width: 80px">
                     <a-option value="=">=</a-option>
                     <a-option value=">">></a-option>
                     <a-option value="<"><</a-option>
                     <a-option value="IN">IN</a-option>
                   </a-select>
                   <a-input v-model="f.value" placeholder="值" style="flex: 1" />
                   <a-button type="text" status="danger" @click="removeFilter(i)"><icon-delete /></a-button>
                </div>
              </a-form-item>

              <a-form-item label="衍生方式">
                <a-select v-model="form.derivation_type">
                  <a-option v-for="t in derivationTypes" :key="t.value" :value="t.value">{{ t.label }}</a-option>
                </a-select>
              </a-form-item>
            </template>

            <!-- 3. 复合指标配置 -->
            <template v-else>
              <a-form-item field="calculation_formula" label="复合表达式" required>
                <a-textarea
                  v-model="form.calculation_formula"
                  placeholder="使用[指标名]进行组合计算，如：[销售额] / [订单数]"
                  :auto-size="{ minRows: 6 }"
                />
                <div class="formula-tips">
                  提示：可用指标包括：{{ metrics.map(m => `[${m.name}]`).join(', ') }}
                </div>
              </a-form-item>
            </template>

            <!-- 公共配置：分析维度 -->
            <a-divider />
            <a-form-item label="分析维度">
              <a-select v-model="form.analysis_dimensions" multiple placeholder="请选择该指标关联的可分析维度">
                <a-option v-for="d in currentDatasetDimensions" :key="d.id" :value="d.id">{{ d.display_name || d.name }}</a-option>
              </a-select>
              <div class="form-help" style="color: var(--color-text-3); font-size: 12px; margin-top: 4px;">
                所选维度将作为问数对话中的建议维度，以及归因/下钻分析的推荐路径。
              </div>
            </a-form-item>
          </a-col>

          <!-- 右侧属性区 -->
          <a-col :span="8" style="border-left: 1px solid #f2f3f5">
            <div style="padding-left: 16px">
              <h3 style="margin-top: 0">基础属性</h3>
              <a-form-item field="name" label="指标名称" required>
                <a-input v-model="form.name" placeholder="英文/拼音标识" />
              </a-form-item>
              <a-form-item field="display_name" label="指标展示名" required>
                <a-input v-model="form.display_name" placeholder="中文展示名" />
              </a-form-item>
              <a-form-item field="unit" label="单位">
                <a-select v-model="form.unit">
                  <a-option value="元">元</a-option>
                  <a-option value="个">个</a-option>
                  <a-option value="%">%</a-option>
                  <a-option value="其他">其他</a-option>
                </a-select>
              </a-form-item>

              <h3 style="margin-top: 24px">业务属性</h3>
              <a-form-item label="业务口径">
                <a-textarea v-model="form.description" placeholder="请输入业务定义和计算逻辑描述" />
              </a-form-item>
              <a-form-item label="同义词">
                <a-input-tag v-model="form.synonyms" placeholder="输入同义词回车" />
              </a-form-item>
            </div>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import { getMetrics, getDatasets, createMetric, updateMetric, deleteMetric } from '@/api/semantic'
import type { Metric, Dataset } from '@/api/types'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const metrics = ref<Metric[]>([])
const datasets = ref<Dataset[]>([])
const filterType = ref('')
const datasetDimensionsMap = reactive<Record<string, any[]>>({})

const form = reactive({
  name: '',
  display_name: '',
  metric_type: 'basic' as const,
  dataset_id: '',
  aggregation: 'SUM' as const,
  calculation_method: 'field' as 'field' | 'expression',
  measure_column: '',
  calculation_formula: '',
  is_semi_additive: { enabled: false, type: 'last_value' },
  date_column_id: '',
  base_metric_id: '',
  derivation_type: 'none',
  time_constraint: '',
  analysis_dimensions: [] as string[],
  unit: '',
  synonyms: [] as string[],
  description: '',
  filters: [] as any[]
})

const derivationTypes = [
  { label: '无', value: 'none' },
  { label: '同比', value: 'yoy' },
  { label: '环比', value: 'mom' },
  { label: '同比增长率', value: 'yoy_growth' },
  { label: '环比增长率', value: 'mom_growth' }
]

const currentDatasetDimensions = computed(() => {
  if (!form.dataset_id) return []
  return datasetDimensionsMap[form.dataset_id] || []
})

// Watch for dataset changes to fetch dimensions
watch(() => form.dataset_id, async (newVal) => {
  if (newVal && !datasetDimensionsMap[newVal]) {
    try {
      const { getDimensions } = await import('@/api/semantic')
      const dims = await getDimensions({ dataset_id: newVal })
      datasetDimensionsMap[newVal] = dims
    } catch (e) {
      console.error('Failed to fetch dimensions:', e)
    }
  }
})

const rules = {
  name: [{ required: true, message: '请输入指标名称' }],
  metric_type: [{ required: true, message: '请选择指标类型' }]
}

const columns = [
  { title: '指标名称', dataIndex: 'name' },
  { title: '显示名称', dataIndex: 'display_name' },
  { title: '类型', slotName: 'metric_type' },
  { title: '聚合', slotName: 'aggregation' },
  { title: '分析维度', slotName: 'analysis_dimensions' },
  { title: '单位', dataIndex: 'unit' },
  { title: '操作', slotName: 'actions', width: 180 }
]

const filteredMetrics = computed(() => {
  if (!filterType.value) return metrics.value
  return metrics.value.filter(m => m.metric_type === filterType.value)
})

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    basic: 'blue',
    derived: 'green',
    composite: 'purple'
  }
  return colors[type] || 'gray'
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    basic: '基础指标',
    derived: '派生指标',
    composite: '复合指标'
  }
  return labels[type] || type
}

function addFilter() {
  form.filters.push({ field: '', operator: '=', value: '' })
}

function removeFilter(index: number) {
  form.filters.splice(index, 1)
}

async function fetchData() {
  loading.value = true
  try {
    const [m, ds] = await Promise.all([
      getMetrics(),
      getDatasets()
    ])
    metrics.value = m
    datasets.value = ds
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  isEdit.value = false
  resetForm()
  modalVisible.value = true
}

function handleEdit(record: Metric) {
  isEdit.value = true
  editingId.value = record.id
  Object.assign(form, {
    name: record.name,
    display_name: record.display_name,
    metric_type: record.metric_type,
    dataset_id: record.dataset_id || '',
    aggregation: record.aggregation || 'SUM',
    calculation_method: record.calculation_method || 'field',
    measure_column: record.measure_column || '',
    calculation_formula: record.calculation_formula || '',
    is_semi_additive: record.is_semi_additive || { enabled: false, type: 'last_value' },
    date_column_id: record.date_column_id || '',
    base_metric_id: record.base_metric_id || '',
    derivation_type: record.derivation_type || 'none',
    time_constraint: record.time_constraint || '',
    analysis_dimensions: record.analysis_dimensions || [],
    unit: record.unit || '',
    synonyms: record.synonyms || [],
    description: record.description || '',
    filters: record.filters || []
  })
  modalVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateMetric(editingId.value, form)
      Message.success('更新成功')
    } else {
      await createMetric(form)
      Message.success('创建成功')
    }
    modalVisible.value = false
    fetchData()
  } catch (error) {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    display_name: '',
    metric_type: 'basic',
    dataset_id: '',
    aggregation: 'SUM',
    calculation_method: 'field',
    measure_column: '',
    calculation_formula: '',
    is_semi_additive: { enabled: false, type: 'last_value' },
    date_column_id: '',
    base_metric_id: '',
    derivation_type: 'none',
    time_constraint: '',
    analysis_dimensions: [],
    unit: '',
    synonyms: [],
    description: '',
    filters: []
  })
}

function handleViewLineage(record: Metric) {
  router.push({ name: 'Lineage', query: { type: 'metric', id: record.id } })
}

async function handleDelete(id: string) {
  try {
    await deleteMetric(id)
    Message.success('删除成功')
    fetchData()
  } catch (error) {
    Message.error('删除失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.metric-list {
  height: 100%;
}
</style>
