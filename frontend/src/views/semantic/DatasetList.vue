<template>
  <div class="dataset-list">
    <a-card title="数据集管理">
      <template #extra>
        <a-space>
          <a-select v-model="filterDatasource" placeholder="筛选数据源" allow-clear style="width: 200px">
            <a-option v-for="ds in dataSources" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
          </a-select>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><icon-plus /></template>
            新增数据集
          </a-button>
        </a-space>
      </template>

      <a-table :columns="columns" :data="filteredDatasets" :loading="loading">
      </a-table>
    </a-card>

    <!-- 新增/编辑数据集弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :title="editingDataset ? '编辑数据集' : '新增数据集'"
      width="800px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form :model="formData" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="数据源" required>
              <a-select v-model="formData.datasource_id" placeholder="请选择数据源">
                <a-option v-for="ds in dataSources" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="数据集名称" required>
              <a-input v-model="formData.name" placeholder="请输入数据集名称" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="物理表名" required>
              <a-input v-model="formData.physical_name" placeholder="请输入物理表名" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Schema">
              <a-input v-model="formData.schema_name" placeholder="例如: public" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述">
          <a-textarea v-model="formData.description" placeholder="请输入数据集描述" :auto-size="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>
        <a-form-item label="字段列表">
          <a-button type="dashed" @click="handleSyncFromSource" :loading="syncing" style="margin-bottom: 12px">
            <template #icon><icon-sync /></template>
            从数据源同步
          </a-button>
          <a-table :columns="columnEditColumns" :data="formData.columns" :pagination="false" bordered>
            <template #actions="{ record, rowIndex }">
              <a-button type="text" size="small" status="danger" @click="removeColumn(rowIndex)">
                <icon-delete />
              </a-button>
            </template>
          </a-table>
          <a-button type="dashed" long style="margin-top: 12px" @click="addColumn">
            <template #icon><icon-plus /></template>
            添加字段
          </a-button>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 字段详情抽屉 -->
    <a-drawer
      v-model:visible="drawerVisible"
      :title="`${currentDataset?.name} - 字段列表`"
      :width="500"
    >
      <a-table :columns="columnColumns" :data="currentDataset?.columns || []" :pagination="false" />
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { Message, Button, Space, Popconfirm, Tag } from '@arco-design/web-vue'
import { getDatasets, getDataSources, deleteDataset, createDataset, updateDataset, syncDatasetFromSource } from '@/api/semantic'
import type { Dataset, DataSource, ColumnInfo } from '@/api/types'

const loading = ref(false)
const syncing = ref(false)
const datasets = ref<Dataset[]>([])
const dataSources = ref<DataSource[]>([])
const filterDatasource = ref('')
const drawerVisible = ref(false)
const modalVisible = ref(false)
const currentDataset = ref<Dataset | null>(null)
const editingDataset = ref<Dataset | null>(null)

const formData = ref<{
  datasource_id: string
  name: string
  physical_name: string
  schema_name: string
  description: string
  columns: ColumnInfo[]
}>({
  datasource_id: '',
  name: '',
  physical_name: '',
  schema_name: 'public',
  description: '',
  columns: []
})

const columns = [
  { title: '数据集名称', dataIndex: 'name' },
  { title: '物理表名', dataIndex: 'physical_name' },
  { 
    title: '字段数', 
    render: ({ record }: { record: Dataset }) => {
      if (record && record.columns && Array.isArray(record.columns)) {
        return h(Tag, {}, { default: () => `${record.columns.length} 列` })
      }
      return h(Tag, {}, { default: () => '0 列' })
    }
  },
  { title: '描述', dataIndex: 'description', ellipsis: true },
  { 
    title: '操作', 
    render: ({ record }: { record: Dataset }) => {
      if (!record) {
        return h(Space, {}, { default: () => [] })
      }
      
      return h(Space, {}, {
        default: () => [
          h(Button, { 
            type: 'text', 
            size: 'small',
            onClick: () => handleViewColumns(record)
          }, { default: () => '查看字段' }),
          
          h(Button, { 
            type: 'text', 
            size: 'small',
            onClick: () => handleEdit(record)
          }, { default: () => h('icon-edit') }),
          
          h(Popconfirm, { 
            content: '确定删除此数据集？',
            onOk: () => handleDelete(record.id)
          }, {
            default: () => h(Button, { 
              type: 'text', 
              size: 'small', 
              status: 'danger'
            }, { default: () => h('icon-delete') })
          })
        ]
      })
    },
    width: 200 
  }
]

const columnColumns = [
  { title: '字段名', dataIndex: 'name' },
  { title: '类型', dataIndex: 'type' },
  { title: '可空', dataIndex: 'nullable', render: (record: any) => record?.nullable ? '是' : '否' },
  { title: '备注', dataIndex: 'comment' }
]

const columnEditColumns = [
  { title: '字段名', dataIndex: 'name', width: 150 },
  { title: '类型', dataIndex: 'type', width: 120 },
  { title: '可空', dataIndex: 'nullable', width: 80, render: (record: any) => record?.nullable ? '是' : '否' },
  { title: '备注', dataIndex: 'comment' },
  { title: '操作', slotName: 'actions', width: 80 }
]

const filteredDatasets = computed(() => {
  if (!filterDatasource.value) return datasets.value
  return datasets.value.filter(d => d.datasource_id === filterDatasource.value)
})

async function fetchData() {
  loading.value = true
  try {
    const [datasetsResult, sources] = await Promise.all([
      getDatasets(),
      getDataSources()
    ])
    datasets.value = datasetsResult
    dataSources.value = sources
  } catch (error) {
    console.error('Failed to fetch data:', error)
    // 初始化为空数组以防止渲染错误
    datasets.value = []
    dataSources.value = []
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  editingDataset.value = null
  formData.value = {
    datasource_id: '',
    name: '',
    physical_name: '',
    schema_name: 'public',
    description: '',
    columns: []
  }
  modalVisible.value = true
}

function handleEdit(record: Dataset) {
  if (!record) {
    console.error('Record is undefined in handleEdit')
    return
  }
  editingDataset.value = record
  formData.value = {
    datasource_id: record.datasource_id || '',
    name: record.name,
    physical_name: record.physical_name,
    schema_name: record.schema_name || 'public',
    description: record.description || '',
    columns: record.columns || []
  }
  modalVisible.value = true
}

function handleCancel() {
  modalVisible.value = false
  editingDataset.value = null
}

async function handleSubmit() {
  if (!formData.value.datasource_id || !formData.value.name || !formData.value.physical_name) {
    Message.error('请填写必填字段')
    return
  }

  try {
    if (editingDataset.value) {
      await updateDataset(editingDataset.value.id, formData.value)
      Message.success('更新成功')
    } else {
      await createDataset(formData.value)
      Message.success('创建成功')
    }
    modalVisible.value = false
    fetchData()
  } catch (error) {
    Message.error(editingDataset.value ? '更新失败' : '创建失败')
  }
}

async function handleSyncFromSource() {
  if (!formData.value.datasource_id) {
    Message.warning('请先选择数据源')
    return
  }

  syncing.value = true
  try {
    const tables = await syncDatasetFromSource(formData.value.datasource_id)
    if (tables && tables.length > 0) {
      // 如果物理表名已填写，尝试匹配对应的表结构
      if (formData.value.physical_name) {
        const matchedTable = tables.find((t: any) => t.name === formData.value.physical_name)
        if (matchedTable && matchedTable.columns) {
          // API 返回的 columns 已经是 ColumnInfo 对象数组，直接使用
          formData.value.columns = matchedTable.columns
          Message.success('同步字段成功')
        } else {
          Message.warning(`未找到表 ${formData.value.physical_name}`)
        }
      } else {
        Message.info(`发现 ${tables.length} 个表，请先填写物理表名`)
      }
    }
  } catch (error) {
    Message.error('同步失败')
  } finally {
    syncing.value = false
  }
}

function addColumn() {
  formData.value.columns.push({
    name: '',
    type: 'VARCHAR',
    nullable: true,
    comment: ''
  })
}

function removeColumn(index: number) {
  formData.value.columns.splice(index, 1)
}

function handleViewColumns(record: Dataset) {
  if (!record) {
    console.error('Record is undefined in handleViewColumns')
    return
  }
  currentDataset.value = record
  drawerVisible.value = true
}

async function handleDelete(id: string) {
  if (!id) {
    console.error('ID is undefined in handleDelete')
    return
  }
  try {
    await deleteDataset(id)
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
.dataset-list {
  height: 100%;
}
</style>
