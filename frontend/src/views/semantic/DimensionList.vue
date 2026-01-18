<template>
  <div class="dimension-list">
    <a-card title="维度管理">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><icon-plus /></template>
          新增维度
        </a-button>
      </template>

      <a-table :columns="columns" :data="dimensions" :loading="loading">
        <template #dimension_type="{ record }">
          <a-tag :color="getTypeColor(record.dimension_type)">
            {{ getTypeLabel(record.dimension_type) }}
          </a-tag>
        </template>
        <template #synonyms="{ record }">
          <a-space v-if="record.synonyms?.length">
            <a-tag v-for="s in record.synonyms.slice(0, 3)" :key="s" size="small">{{ s }}</a-tag>
            <span v-if="record.synonyms.length > 3">+{{ record.synonyms.length - 3 }}</span>
          </a-space>
          <span v-else>-</span>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
            </a-button>
            <a-popconfirm content="确定删除此维度？" @ok="handleDelete(record.id)">
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
      :title="isEdit ? '编辑维度' : '新增维度'"
      :ok-loading="submitting"
      @ok="handleSubmit"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item field="name" label="维度名称">
              <a-input v-model="form.name" placeholder="请输入维度名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item field="display_name" label="显示名称">
              <a-input v-model="form.display_name" placeholder="请输入显示名称" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item field="dataset_id" label="数据集">
          <a-select v-model="form.dataset_id" placeholder="选择数据集">
            <a-option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item field="physical_column" label="物理字段">
              <a-input v-model="form.physical_column" placeholder="物理字段名" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item field="data_type" label="数据类型">
              <a-select v-model="form.data_type" placeholder="选择数据类型">
                <a-option value="string">字符串</a-option>
                <a-option value="number">数值</a-option>
                <a-option value="date">日期</a-option>
                <a-option value="datetime">日期时间</a-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item field="dimension_type" label="维度类型">
          <a-radio-group v-model="form.dimension_type">
            <a-radio value="normal">普通维度</a-radio>
            <a-radio value="time">时间维度</a-radio>
            <a-radio value="geo">地理维度</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item field="synonyms" label="同义词">
          <a-input-tag v-model="form.synonyms" placeholder="输入后回车添加" />
        </a-form-item>
        <a-form-item field="description" label="描述">
          <a-textarea v-model="form.description" placeholder="维度描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import { getDimensions, getDatasets, createDimension, updateDimension, deleteDimension } from '@/api/semantic'
import type { Dimension, Dataset } from '@/api/types'

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const dimensions = ref<Dimension[]>([])
const datasets = ref<Dataset[]>([])

const form = reactive({
  name: '',
  display_name: '',
  dataset_id: '',
  physical_column: '',
  data_type: 'string' as const,
  dimension_type: 'normal' as const,
  synonyms: [] as string[],
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入维度名称' }],
  dataset_id: [{ required: true, message: '请选择数据集' }],
  physical_column: [{ required: true, message: '请输入物理字段' }]
}

const columns = [
  { title: '维度名称', dataIndex: 'name' },
  { title: '显示名称', dataIndex: 'display_name' },
  { title: '物理字段', dataIndex: 'physical_column' },
  { title: '类型', slotName: 'dimension_type' },
  { title: '同义词', slotName: 'synonyms' },
  { title: '操作', slotName: 'actions', width: 120 }
]

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    normal: 'blue',
    time: 'green',
    geo: 'orange'
  }
  return colors[type] || 'gray'
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    normal: '普通',
    time: '时间',
    geo: '地理'
  }
  return labels[type] || type
}

async function fetchData() {
  loading.value = true
  try {
    const [dims, ds] = await Promise.all([
      getDimensions(),
      getDatasets()
    ])
    dimensions.value = dims
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

function handleEdit(record: Dimension) {
  isEdit.value = true
  editingId.value = record.id
  Object.assign(form, {
    name: record.name,
    display_name: record.display_name,
    dataset_id: record.dataset_id,
    physical_column: record.physical_column,
    data_type: record.data_type,
    dimension_type: record.dimension_type,
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
      await updateDimension(editingId.value, form)
      Message.success('更新成功')
    } else {
      await createDimension(form)
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
    dataset_id: '',
    physical_column: '',
    data_type: 'string',
    dimension_type: 'normal',
    synonyms: [],
    description: ''
  })
}

async function handleDelete(id: string) {
  try {
    await deleteDimension(id)
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
.dimension-list {
  height: 100%;
}
</style>
