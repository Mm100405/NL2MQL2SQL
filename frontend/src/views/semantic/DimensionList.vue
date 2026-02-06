<template>
  <div class="dimension-list">
    <a-card title="维度管理">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><icon-plus /></template>
          新增维度
        </a-button>
      </template>

      <a-table
        :columns="columns"
        :data="dimensions"
        :loading="loading"
        :scroll="{ x: 1300 }"
        :bordered="false"
        :stripe="true"
      >
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
          <a-space :size="8" class="action-btns">
            <a-button type="text" size="mini" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
              编辑
            </a-button>
            <a-divider direction="vertical" class="action-divider" />
            <a-popconfirm content="确定删除此维度？" @ok="handleDelete(record.id)">
              <a-button type="text" size="mini" status="danger">
                <template #icon><icon-delete /></template>
                删除
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
            <a-radio value="normal">普通</a-radio>
            <a-radio value="time">时间</a-radio>
            <a-radio value="geo">地理</a-radio>
            <a-radio value="categorical">分类</a-radio>
            <a-radio value="numerical">数值</a-radio>
          </a-radio-group>
        </a-form-item>

        <!-- 时间维度格式化配置 -->
        <template v-if="form.dimension_type === 'time'">
          <a-divider>时间格式化配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item field="format_config.default_format" label="默认格式">
                <a-select v-model="form.format_config.default_format" placeholder="选择默认展示格式">
                  <a-option v-for="opt in timeFormatOptions" :key="opt.name" :value="opt.name">
                    {{ opt.name }} ({{ opt.label }})
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item field="format_config.options" label="可选格式列表">
                <a-select v-model="form.format_config.options" multiple placeholder="选择可选的展示格式">
                  <a-option v-for="opt in timeFormatOptions" :key="opt.name" :value="opt.name">
                    {{ opt.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </template>
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
import { getSystemSetting } from '@/api/settings'
import type { Dimension, Dataset, DimensionType } from '@/api/types'

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const dimensions = ref<Dimension[]>([])
const datasets = ref<Dataset[]>([])
const timeFormatOptions = ref<any[]>([])

const form = reactive({
  name: '',
  display_name: '',
  dataset_id: '',
  physical_column: '',
  data_type: 'string' as 'string' | 'number' | 'date' | 'datetime',
  dimension_type: 'normal' as DimensionType,
  format_config: {
    default_format: 'YYYY-MM-DD',
    options: ['YYYY-MM-DD', 'YYYY-MM', 'YYYY']
  },
  synonyms: [] as string[],
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入维度名称' }],
  dataset_id: [{ required: true, message: '请选择数据集' }],
  physical_column: [{ required: true, message: '请输入物理字段' }]
}

const columns = [
  { title: '维度名称', dataIndex: 'name', width: 200, ellipsis: true },
  { title: '显示名称', dataIndex: 'display_name', width: 180, ellipsis: true },
  { title: '物理字段', dataIndex: 'physical_column', width: 200, ellipsis: true },
  { title: '类型', slotName: 'dimension_type', width: 100, align: 'center' },
  { title: '同义词', slotName: 'synonyms', ellipsis: true, width: 200 },
  { title: '描述', dataIndex: 'description', ellipsis: true, width: 250 },
  { title: '操作', slotName: 'actions', width: 180, fixed: 'right', align: 'center' }
]

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    normal: 'blue',
    time: 'green',
    geo: 'orange',
    categorical: 'purple',
    numerical: 'cyan'
  }
  return colors[type] || 'gray'
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    normal: '普通',
    time: '时间',
    geo: '地理',
    categorical: '分类',
    numerical: '数值',
    user_defined: '自定义'
  }
  return labels[type] || type
}

async function fetchData() {
  loading.value = true
  try {
    const [dims, ds, setting] = await Promise.all([
      getDimensions(),
      getDatasets(),
      getSystemSetting('time_formats').catch(() => ({ value: [] }))
    ])
    dimensions.value = dims
    datasets.value = ds
    timeFormatOptions.value = (setting as any).value || []
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
    format_config: record.format_config || { default_format: 'YYYY-MM-DD', options: ['YYYY-MM-DD', 'YYYY-MM', 'YYYY'] },
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
    format_config: {
      default_format: 'YYYY-MM-DD',
      options: ['YYYY-MM-DD', 'YYYY-MM', 'YYYY']
    },
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

/* 表格容器样式 */
.dimension-list :deep(.arco-table) {
  overflow: visible;
}

.dimension-list :deep(.arco-table-container) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* 固定操作列样式 - 兼容多种 Arco Design 版本 */
.dimension-list :deep(.arco-table-th-fixed-right),
.dimension-list :deep(.arco-table-td-fixed-right),
.dimension-list :deep(.arco-table-th-fixed-last),
.dimension-list :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 100 !important;
  box-shadow: -4px 0 8px rgba(0, 0, 0, 0.08) !important;
}

/* 表头固定列 */
.dimension-list :deep(.arco-table-th-fixed-right),
.dimension-list :deep(.arco-table-th-fixed-last) {
  background: #f7f8fa !important;
}

/* 行悬停时固定列背景 */
.dimension-list :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.dimension-list :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.dimension-list :deep(.arco-table-th-fixed-right)::before,
.dimension-list :deep(.arco-table-td-fixed-right)::before,
.dimension-list :deep(.arco-table-th-fixed-last)::before,
.dimension-list :deep(.arco-table-td-fixed-last)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #e5e6eb;
}

/* 操作按钮样式 */
.dimension-list .action-btns {
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.dimension-list .action-divider {
  margin: 0 4px;
  height: 16px;
}

.dimension-list :deep(.arco-btn-size-mini) {
  padding: 0 4px;
  font-size: 12px;
}

/* 确保表格单元格内容不溢出 */
.dimension-list :deep(.arco-table-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作列单元格 */
.dimension-list :deep(.arco-table-td:last-child) {
  padding: 8px 12px;
}
</style>
