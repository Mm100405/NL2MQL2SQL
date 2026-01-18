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
      :width="700"
      :ok-loading="submitting"
      @ok="handleSubmit"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item field="name" label="指标名称">
              <a-input v-model="form.name" placeholder="请输入指标名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item field="display_name" label="显示名称">
              <a-input v-model="form.display_name" placeholder="请输入显示名称" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item field="metric_type" label="指标类型">
          <a-radio-group v-model="form.metric_type">
            <a-radio value="basic">基础指标</a-radio>
            <a-radio value="derived">派生指标</a-radio>
            <a-radio value="composite">复合指标</a-radio>
          </a-radio-group>
        </a-form-item>
        
        <!-- 基础指标配置 -->
        <template v-if="form.metric_type === 'basic'">
          <a-form-item field="dataset_id" label="数据集">
            <a-select v-model="form.dataset_id" placeholder="选择数据集">
              <a-option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
            </a-select>
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item field="aggregation" label="聚合函数">
                <a-select v-model="form.aggregation" placeholder="选择聚合函数">
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
              <a-form-item field="measure_column" label="度量字段">
                <a-input v-model="form.measure_column" placeholder="选择度量字段" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- 派生/复合指标配置 -->
        <template v-else>
          <a-form-item field="calculation_formula" label="计算公式">
            <a-textarea
              v-model="form.calculation_formula"
              placeholder="输入MQL计算公式，如：SUM(销售额) / COUNT(订单ID)"
              :auto-size="{ minRows: 3 }"
            />
          </a-form-item>
        </template>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item field="unit" label="单位">
              <a-input v-model="form.unit" placeholder="如：元、个、%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item field="synonyms" label="同义词">
              <a-input-tag v-model="form.synonyms" placeholder="输入后回车添加" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item field="description" label="描述">
          <a-textarea v-model="form.description" placeholder="指标描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
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

const form = reactive({
  name: '',
  display_name: '',
  metric_type: 'basic' as const,
  dataset_id: '',
  aggregation: 'SUM' as const,
  measure_column: '',
  calculation_formula: '',
  unit: '',
  synonyms: [] as string[],
  description: ''
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
    measure_column: record.measure_column || '',
    calculation_formula: record.calculation_formula || '',
    unit: record.unit || '',
    synonyms: record.synonyms || [],
    description: record.description || ''
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
    measure_column: '',
    calculation_formula: '',
    unit: '',
    synonyms: [],
    description: ''
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
