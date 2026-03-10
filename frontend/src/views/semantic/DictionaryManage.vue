<template>
  <div class="dictionary-manage">
    <a-card title="字典管理">
      <template #extra>
        <a-space>
          <a-select v-model="filterSourceType" placeholder="筛选类型" style="width: 140px" allow-clear>
            <a-option value="manual">手动配置</a-option>
            <a-option value="view_ref">引用视图</a-option>
            <a-option value="auto">自动生成</a-option>
          </a-select>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><icon-plus /></template>
            新增字典
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data="filteredDictionaries"
        :loading="loading"
        :scroll="{ x: 1200 }"
        :bordered="false"
        :stripe="true"
      >
        <template #source_type="{ record }">
          <a-tag :color="getTypeColor(record.source_type)">
            {{ getTypeLabel(record.source_type) }}
          </a-tag>
        </template>
        <template #mapping_count="{ record }">
          <a-badge
            :count="record.mappings?.length || 0"
            :max-count="99"
            :number-style="{ backgroundColor: '#165dff' }"
          />
        </template>
        <template #auto_last_sync="{ record }">
          <span v-if="record.auto_last_sync">{{ formatDate(record.auto_last_sync) }}</span>
          <span v-else style="color: var(--color-text-4)">-</span>
        </template>
        <template #actions="{ record }">
          <a-space :size="4">
            <a-button type="text" size="small" @click="handleViewValues(record)">
              值管理
            </a-button>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
              编辑
            </a-button>
            <a-button v-if="record.source_type === 'auto'" type="text" size="small" @click="handleSync(record)">
              <template #icon><icon-refresh /></template>
              同步
            </a-button>
            <a-popconfirm content="确定删除此字典？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
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
      :title="isEdit ? '编辑字典' : '新增字典'"
      :width="700"
      :ok-loading="submitting"
      @ok="handleSubmit"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item field="name" label="字典名称">
              <a-input v-model="form.name" placeholder="英文/拼音标识" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item field="display_name" label="显示名称">
              <a-input v-model="form.display_name" placeholder="中文展示名" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item field="source_type" label="字典类型">
          <a-radio-group v-model="form.source_type" type="button" :disabled="isEdit">
            <a-radio value="manual">手动配置</a-radio>
            <a-radio value="view_ref">引用视图</a-radio>
            <a-radio value="auto">自动生成</a-radio>
          </a-radio-group>
        </a-form-item>

        <!-- 手动配置类型 -->
        <template v-if="form.source_type === 'manual'">
          <a-form-item label="映射配置">
            <div class="mapping-editor">
              <a-table
                :columns="mappingColumns"
                :data="form.mappings"
                :bordered="true"
                :pagination="false"
                size="small"
              >
                <template #value="{ rowIndex }">
                  <a-input v-model="form.mappings[rowIndex].value" placeholder="实际值" />
                </template>
                <template #label="{ rowIndex }">
                  <a-input v-model="form.mappings[rowIndex].label" placeholder="展示标签" />
                </template>
                <template #synonyms="{ rowIndex }">
                  <a-input-tag v-model="form.mappings[rowIndex].synonyms" placeholder="同义词" />
                </template>
                <template #actions="{ rowIndex }">
                  <a-button type="text" status="danger" size="small" @click="removeDictMapping(rowIndex)">
                    <icon-delete />
                  </a-button>
                </template>
              </a-table>
              <a-button type="outline" size="small" @click="addDictMapping" style="margin-top: 8px">
                <template #icon><icon-plus /></template>
                添加映射
              </a-button>
            </div>
          </a-form-item>
        </template>

        <!-- 引用视图类型 -->
        <template v-else-if="form.source_type === 'view_ref'">
          <a-form-item field="ref_view_id" label="引用视图" required>
            <a-select v-model="form.ref_view_id" placeholder="选择视图" allow-search>
              <a-option v-for="v in views" :key="v.id" :value="v.id">
                {{ v.display_name || v.name }}
              </a-option>
            </a-select>
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item field="ref_value_column" label="值字段">
                <a-select v-model="form.ref_value_column" placeholder="选择字段" allow-search allow-clear>
                  <a-option v-for="col in viewColumns" :key="col.name" :value="col.name">
                    {{ col.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item field="ref_label_column" label="标签字段">
                <a-select v-model="form.ref_label_column" placeholder="选择字段" allow-search allow-clear>
                  <a-option v-for="col in viewColumns" :key="col.name" :value="col.name">
                    {{ col.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
          <div class="form-help" style="color: var(--color-text-3); font-size: 12px; margin-top: -8px;">
            提示：引用视图类型的字典会动态从视图查询可选值
          </div>
        </template>

        <!-- 自动生成类型 -->
        <template v-else>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="数据源" required>
                <a-select v-model="selectedDatasourceId" placeholder="选择数据源" @change="form.auto_source_dataset_id = ''">
                  <a-option v-for="ds in datasources" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="物理表" required>
                <a-select v-model="form.auto_source_dataset_id" placeholder="选择物理表" :disabled="!selectedDatasourceId" allow-search>
                  <a-option v-for="dt in filteredDatasets" :key="dt.id" :value="dt.id">
                    {{ dt.name }} ({{ dt.physical_name }})
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="字段" required>
            <a-select v-model="form.auto_source_column" placeholder="选择字段" allow-search>
              <a-option v-for="col in datasetColumns" :key="col.name" :value="col.name">
                {{ col.name }} <span v-if="col.comment" style="color: var(--color-text-3)">（{{ col.comment }}）</span>
              </a-option>
            </a-select>
          </a-form-item>
          
          <!-- 过滤条件配置 -->
          <a-form-item>
            <template #label>
              <div class="filter-label">
                <span>筛选条件</span>
                <a-switch 
                  v-model="showFilters" 
                  size="small"
                  :checked-text="'开启'"
                  :unchecked-text="'关闭'"
                />
              </div>
            </template>
            
            <div v-if="showFilters" class="filters-wrapper">
              <div 
                v-for="(filter, idx) in form.auto_filters" 
                :key="idx"
                class="filter-card"
              >
                <div class="filter-content">
                  <a-select 
                    v-model="filter.column" 
                    placeholder="字段"
                    size="small"
                    class="filter-field"
                    allow-search
                  >
                    <a-option 
                      v-for="col in datasetColumns" 
                      :key="col.name" 
                      :value="col.name"
                    >
                      {{ col.name }}
                    </a-option>
                  </a-select>
                  
                  <a-select 
                    v-model="filter.operator" 
                    size="small"
                    class="filter-operator"
                  >
                    <a-option value="=">=</a-option>
                    <a-option value="!=">≠</a-option>
                    <a-option value=">">&gt;</a-option>
                    <a-option value="<">&lt;</a-option>
                    <a-option value=">=">≥</a-option>
                    <a-option value="<=">≤</a-option>
                    <a-option value="LIKE">LIKE</a-option>
                    <a-option value="IN">IN</a-option>
                    <a-option value="IS NULL">IS NULL</a-option>
                    <a-option value="IS NOT NULL">IS NOT NULL</a-option>
                  </a-select>
                  
                  <a-input 
                    v-if="!['IS NULL', 'IS NOT NULL'].includes(filter.operator)"
                    v-model="filter.value" 
                    placeholder="值"
                    size="small"
                    class="filter-value"
                  />
                </div>
                
                <a-button 
                  type="text" 
                  size="mini" 
                  status="danger"
                  class="filter-delete"
                  @click="removeFilter(idx)"
                >
                  <icon-delete />
                </a-button>
              </div>
              
              <a-button 
                size="small" 
                type="dashed" 
                long
                class="add-btn"
                @click="addFilter"
              >
                <template #icon><icon-plus /></template>
                添加筛选
              </a-button>
            </div>
          </a-form-item>
          
          <div class="form-help" style="color: var(--color-text-3); font-size: 12px; margin-top: -8px;">
            提示：自动生成类型的字典会从指定表字段查询去重值，可随时同步更新
          </div>
        </template>

        <a-form-item field="description" label="描述">
          <a-textarea v-model="form.description" placeholder="字典描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 值管理弹窗 -->
    <a-modal
      v-model:visible="valuesModalVisible"
      :title="`值管理 - ${currentDictionary?.display_name || currentDictionary?.name}`"
      :width="800"
      :footer="false"
    >
      <div class="values-header">
        <a-space>
          <a-button v-if="currentDictionary?.source_type === 'manual'" type="primary" size="small" @click="showAddValueModal">
            <template #icon><icon-plus /></template>
            添加值
          </a-button>
          <a-button v-if="currentDictionary?.source_type === 'auto'" size="small" @click="handleSync(currentDictionary)">
            <template #icon><icon-refresh /></template>
            同步
          </a-button>
        </a-space>
        <a-input-search v-model="searchValue" placeholder="搜索值或标签" style="width: 200px" allow-clear />
      </div>

      <a-table
        :columns="valuesColumns"
        :data="filteredValues"
        :loading="valuesLoading"
        :pagination="{ pageSize: 20, showTotal: true }"
        :bordered="true"
        size="small"
        style="margin-top: 12px"
      >
        <template #value="{ record }">
          <span style="font-family: monospace">{{ record.value }}</span>
        </template>
        <template #label="{ record }">
          <a-input v-if="editingValue === record.value" v-model="editingLabel" size="small" @press-enter="saveLabel(record)" @blur="saveLabel(record)" />
          <span v-else @dblclick="startEditLabel(record)">{{ record.label }}</span>
        </template>
        <template #synonyms="{ record }">
          <a-space v-if="record.synonyms?.length">
            <a-tag v-for="s in record.synonyms.slice(0, 3)" :key="s" size="small">{{ s }}</a-tag>
            <span v-if="record.synonyms.length > 3" style="color: var(--color-text-4)">+{{ record.synonyms.length - 3 }}</span>
          </a-space>
          <span v-else style="color: var(--color-text-4)">-</span>
        </template>
        <template #actions="{ record }">
          <a-button v-if="currentDictionary?.source_type === 'manual'" type="text" size="small" @click="startEditLabel(record)">
            编辑
          </a-button>
          <a-popconfirm v-if="currentDictionary?.source_type === 'manual'" content="确定删除？" @ok="handleDeleteValue(record.value)">
            <a-button type="text" size="small" status="danger">
              删除
            </a-button>
          </a-popconfirm>
        </template>
      </a-table>
    </a-modal>

    <!-- 添加值弹窗 -->
    <a-modal
      v-model:visible="addValueModalVisible"
      title="添加字典值"
      @ok="handleAddValue"
      :ok-loading="addingValue"
    >
      <a-form :model="newValue" layout="vertical">
        <a-form-item label="实际值" required>
          <a-input v-model="newValue.value" placeholder="数据库中的实际值" />
        </a-form-item>
        <a-form-item label="展示标签" required>
          <a-input v-model="newValue.label" placeholder="用户可见的展示名称" />
        </a-form-item>
        <a-form-item label="同义词">
          <a-input-tag v-model="newValue.synonyms" placeholder="输入后回车添加" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import {
  getDictionaries,
  createDictionary,
  updateDictionary,
  deleteDictionary,
  getDictionaryValues,
  syncDictionary,
  addMapping,
  deleteMapping,
  type Dictionary,
  type DictMapping
} from '@/api/dictionaries'
import { getDataSources, getDatasets } from '@/api/semantic'
import { getViews } from '@/api/views'
import type { DataSource, Dataset, CommonColumnInfo } from '@/api/types'
import type { View } from '@/api/views'

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()

// 列表数据
const dictionaries = ref<Dictionary[]>([])
const datasources = ref<DataSource[]>([])
const datasets = ref<Dataset[]>([])
const views = ref<View[]>([])
const filterSourceType = ref('')

// 值管理弹窗
const valuesModalVisible = ref(false)
const valuesLoading = ref(false)
const currentDictionary = ref<Dictionary | null>(null)
const dictionaryValues = ref<DictMapping[]>([])
const searchValue = ref('')
const editingValue = ref('')
const editingLabel = ref('')

// 添加值弹窗
const addValueModalVisible = ref(false)
const addingValue = ref(false)
const newValue = reactive({ value: '', label: '', synonyms: [] as string[] })

// 选择的辅助字段
const selectedDatasourceId = ref('')

// 筛选条件开关
const showFilters = ref(false)

const form = reactive({
  name: '',
  display_name: '',
  source_type: 'manual' as 'manual' | 'view_ref' | 'auto',
  mappings: [] as DictMapping[],
  ref_view_id: '',
  ref_value_column: '',
  ref_label_column: '',
  auto_source_dataset_id: '',
  auto_source_column: '',
  auto_filters: [] as Array<{ column: string; operator: string; value: string }>,
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入字典名称' }],
  source_type: [{ required: true, message: '请选择字典类型' }]
}

// 表格列定义
const columns = [
  { title: '字典名称', dataIndex: 'name', width: 200 },
  { title: '显示名称', dataIndex: 'display_name', width: 180 },
  { title: '类型', slotName: 'source_type', width: 120 },
  { title: '映射数量', slotName: 'mapping_count', width: 100, align: 'center' },
  { title: '最后同步', slotName: 'auto_last_sync', width: 180 },
  { title: '描述', dataIndex: 'description', ellipsis: true, width: 200 },
  { title: '操作', slotName: 'actions', width: 350, fixed: 'right' }
]

const mappingColumns = [
  { title: '实际值', slotName: 'value', width: 150 },
  { title: '展示标签', slotName: 'label', width: 150 },
  { title: '同义词', slotName: 'synonyms', width: 200 },
  { title: '操作', slotName: 'actions', width: 60 }
]

const valuesColumns = [
  { title: '实际值', slotName: 'value', width: 200 },
  { title: '展示标签', slotName: 'label', width: 200 },
  { title: '同义词', slotName: 'synonyms', width: 250 },
  { title: '操作', slotName: 'actions', width: 120 }
]

// 计算属性
const filteredDictionaries = computed(() => {
  if (!filterSourceType.value) return dictionaries.value
  return dictionaries.value.filter(d => d.source_type === filterSourceType.value)
})

const filteredDatasets = computed(() => {
  if (!selectedDatasourceId.value) return []
  return datasets.value.filter(d => d.datasource_id === selectedDatasourceId.value)
})

const datasetColumns = computed((): CommonColumnInfo[] => {
  if (!form.auto_source_dataset_id) return []
  const dataset = datasets.value.find(d => d.id === form.auto_source_dataset_id)
  return (dataset?.columns || []).map(col => ({
    name: col.name,
    type: col.type,
    comment: col.comment
  }))
})

const viewColumns = computed((): CommonColumnInfo[] => {
  if (!form.ref_view_id) return []
  const view = views.value.find(v => v.id === form.ref_view_id)
  return (view?.columns || []).map(col => ({
    name: col.name,
    type: col.type,
    comment: col.description
  }))
})

const filteredValues = computed(() => {
  if (!searchValue.value) return dictionaryValues.value
  const kw = searchValue.value.toLowerCase()
  return dictionaryValues.value.filter(v =>
    v.value.toLowerCase().includes(kw) ||
    v.label.toLowerCase().includes(kw) ||
    v.synonyms?.some(s => s.toLowerCase().includes(kw))
  )
})

// 方法
function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    manual: 'blue',
    view_ref: 'green',
    auto: 'orange'
  }
  return colors[type] || 'gray'
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    manual: '手动配置',
    view_ref: '引用视图',
    auto: '自动生成'
  }
  return labels[type] || type
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function addDictMapping() {
  form.mappings.push({ value: '', label: '', synonyms: [] })
}

function removeDictMapping(index: number) {
  form.mappings.splice(index, 1)
}

async function fetchData() {
  loading.value = true
  try {
    const [dictRes, dsRes, ds, allViews] = await Promise.all([
      getDictionaries(),
      getDataSources(),
      getDatasets(),
      getViews()
    ])
    dictionaries.value = dictRes
    datasources.value = dsRes
    datasets.value = ds
    views.value = allViews
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

function handleEdit(record: Dictionary) {
  isEdit.value = true
  editingId.value = record.id

  Object.assign(form, {
    name: record.name,
    display_name: record.display_name || '',
    source_type: record.source_type,
    mappings: record.mappings ? [...record.mappings] : [],
    ref_view_id: record.ref_view_id || '',
    ref_value_column: record.ref_value_column || '',
    ref_label_column: record.ref_label_column || '',
    auto_source_dataset_id: record.auto_source_dataset_id || '',
    auto_source_column: record.auto_source_column || '',
    auto_filters: record.auto_filters ? [...record.auto_filters] : [],
    description: record.description || ''
  })
  
  // 设置筛选条件开关
  showFilters.value = !!(record.auto_filters && record.auto_filters.length > 0)

  // 设置数据源ID（如果是自动生成类型）
  if (record.source_type === 'auto' && record.auto_source_dataset_id) {
    const dataset = datasets.value.find(d => d.id === record.auto_source_dataset_id)
    if (dataset) {
      selectedDatasourceId.value = dataset.datasource_id
    }
  }

  modalVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateDictionary(editingId.value, form)
      Message.success('更新成功')
    } else {
      await createDictionary(form)
      Message.success('创建成功')
    }
    modalVisible.value = false
    fetchData()
  } catch (error: any) {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    display_name: '',
    source_type: 'manual',
    mappings: [],
    ref_view_id: '',
    ref_value_column: '',
    ref_label_column: '',
    auto_source_dataset_id: '',
    auto_source_column: '',
    auto_filters: [],
    description: ''
  })
  selectedDatasourceId.value = ''
  showFilters.value = false
}

function addFilter() {
  form.auto_filters.push({
    column: '',
    operator: '=',
    value: ''
  })
}

function removeFilter(idx: number) {
  form.auto_filters.splice(idx, 1)
}

async function handleDelete(id: string) {
  try {
    await deleteDictionary(id)
    Message.success('删除成功')
    fetchData()
  } catch (error) {
    Message.error('删除失败')
  }
}

async function handleSync(record: Dictionary) {
  try {
    await syncDictionary(record.id)
    Message.success('同步成功')
    if (valuesModalVisible.value && currentDictionary.value?.id === record.id) {
      await loadDictionaryValues(record.id)
    }
    fetchData()
  } catch (error) {
    Message.error('同步失败')
  }
}

async function handleViewValues(record: Dictionary) {
  currentDictionary.value = record
  valuesModalVisible.value = true
  await loadDictionaryValues(record.id)
}

async function loadDictionaryValues(id: string) {
  valuesLoading.value = true
  try {
    const res = await getDictionaryValues(id)
    dictionaryValues.value = res.values || []
  } catch (error) {
    console.error('Failed to load values:', error)
    dictionaryValues.value = []
  } finally {
    valuesLoading.value = false
  }
}

function showAddValueModal() {
  newValue.value = ''
  newValue.label = ''
  newValue.synonyms = []
  addValueModalVisible.value = true
}

async function handleAddValue() {
  if (!newValue.value || !newValue.label) {
    Message.warning('请填写实际值和展示标签')
    return
  }
  addingValue.value = true
  try {
    await addMapping(currentDictionary.value!.id, {
      value: newValue.value,
      label: newValue.label,
      synonyms: newValue.synonyms
    })
    Message.success('添加成功')
    addValueModalVisible.value = false
    await loadDictionaryValues(currentDictionary.value!.id)
    fetchData()
  } catch (error) {
    Message.error('添加失败')
  } finally {
    addingValue.value = false
  }
}

async function handleDeleteValue(value: string) {
  try {
    await deleteMapping(currentDictionary.value!.id, value)
    Message.success('删除成功')
    await loadDictionaryValues(currentDictionary.value!.id)
    fetchData()
  } catch (error) {
    Message.error('删除失败')
  }
}

function startEditLabel(record: DictMapping) {
  editingValue.value = record.value
  editingLabel.value = record.label
}

async function saveLabel(record: DictMapping) {
  if (editingLabel.value !== record.label) {
    try {
      // 删除旧值，添加新值
      await deleteMapping(currentDictionary.value!.id, record.value)
      await addMapping(currentDictionary.value!.id, {
        value: record.value,
        label: editingLabel.value,
        synonyms: record.synonyms || []
      })
      Message.success('更新成功')
      await loadDictionaryValues(currentDictionary.value!.id)
      fetchData()
    } catch (error) {
      Message.error('更新失败')
    }
  }
  editingValue.value = ''
  editingLabel.value = ''
}

// 监听视图选择变化
watch(() => form.ref_view_id, () => {
  form.ref_value_column = ''
  form.ref_label_column = ''
})

// 监听自动生成数据源变化
watch(() => selectedDatasourceId.value, () => {
  form.auto_source_dataset_id = ''
  form.auto_source_column = ''
})

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.dictionary-manage {
  height: 100%;
}

.dictionary-manage :deep(.arco-table) {
  overflow: visible;
  table-layout: fixed;
}

.dictionary-manage :deep(.arco-table-container) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* 固定操作列样式 */
.dictionary-manage :deep(.arco-table-th-fixed-right),
.dictionary-manage :deep(.arco-table-td-fixed-right),
.dictionary-manage :deep(.arco-table-th-fixed-last),
.dictionary-manage :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 10 !important;
  box-shadow: -6px 0 12px -4px rgba(0, 0, 0, 0.08) !important;
}

.dictionary-manage :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.dictionary-manage :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.dictionary-manage :deep(.arco-table-th-fixed-right)::before,
.dictionary-manage :deep(.arco-table-td-fixed-right)::before,
.dictionary-manage :deep(.arco-table-th-fixed-last)::before,
.dictionary-manage :deep(.arco-table-td-fixed-last)::before {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 1px !important;
  background: #e5e6eb !important;
}

/* 确保表格单元格内容不溢出 */
.dictionary-manage :deep(.arco-table-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 值管理弹窗样式 */
.values-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.mapping-editor :deep(.arco-table-cell) {
  padding: 4px 8px !important;
}

/* 筛选条件样式 */
.filter-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filters-wrapper {
  border: 1px dashed var(--color-border-2);
  border-radius: 4px;
  padding: 12px;
  background: var(--color-fill-2);
}

.filter-card {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding: 8px;
  background: var(--color-bg-2);
  border-radius: 4px;
  border: 1px solid var(--color-border-2);
}

.filter-content {
  flex: 1;
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-field {
  flex: 1;
  min-width: 120px;
}

.filter-operator {
  width: 80px;
  flex-shrink: 0;
}

.filter-value {
  flex: 1;
  min-width: 100px;
}

.filter-delete {
  flex-shrink: 0;
}

.add-btn {
  margin-top: 4px;
}
</style>
