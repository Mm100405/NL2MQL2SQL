<template>
  <div class="dataset-list">
    <a-layout>
      <!-- 左侧数据源列表 -->
      <a-layout-sider class="datasource-sider" :width="260">
        <div class="sider-header">
          <span class="sider-title">数据源</span>
          <a-button type="text" size="small" @click="refreshDataSources">
            <template #icon><icon-refresh /></template>
          </a-button>
        </div>
        <div class="sider-filter">
          <a-select
            v-model="statusFilter"
            placeholder="筛选状态"
            size="small"
            allow-clear
            style="width: 100%"
          >
            <a-option value="">全部</a-option>
            <a-option value="active">正常</a-option>
            <a-option value="inactive">未连接</a-option>
            <a-option value="error">异常</a-option>
          </a-select>
        </div>
        <div class="datasource-list">
          <div
            v-for="ds in filteredDataSources"
            :key="ds.id"
            class="datasource-item"
            :class="{ active: selectedDatasource === ds.id }"
            @click="selectDatasource(ds.id)"
          >
            <div class="datasource-name">
              <icon-storage />
              <span>{{ ds.name }}</span>
            </div>
            <div class="datasource-info">
              <a-tooltip :content="getStatusTooltip(ds.status)">
                <a-tag size="small" :color="getStatusColor(ds.status)">
                  <template #icon>
                    <component :is="getStatusIcon(ds.status)" />
                  </template>
                  {{ getStatusText(ds.status) }}
                </a-tag>
              </a-tooltip>
              <span class="datasource-count">{{ getDatasourceCount(ds.id) }} 个表</span>
            </div>
          </div>
          <a-empty v-if="filteredDataSources.length === 0" description="暂无数据源" size="small" />
        </div>
      </a-layout-sider>

      <!-- 右侧物理表列表 -->
      <a-layout-content class="dataset-content">
        <a-card v-if="selectedDatasource" :title="`${selectedDatasourceInfo?.name} - 物理表`">
          <template #extra>
            <a-space>
              <a-input-search
                v-model="searchKeyword"
                placeholder="搜索表名或物理表名"
                style="width: 280px"
                allow-clear
                @search="handleSearch"
              />
              <a-button type="primary" @click="showCreateModal">
                <template #icon><icon-plus /></template>
                新增
              </a-button>
              <a-button @click="syncTables" :loading="loading">
                <template #icon><icon-sync /></template>
                同步物理表
              </a-button>
            </a-space>
          </template>

          <div class="table-wrapper">
            <a-table
              :columns="columns"
              :data="filteredDatasets"
              :loading="loading"
              :pagination="false"
              :bordered="false"
              :stripe="true"
              :scroll="{ x: 1000 }"
            />
          </div>
          <div class="pagination-wrapper">
            <a-pagination
              :current="pagination.current"
              :page-size="pagination.pageSize"
              :default-page-size="7"
              :total="pagination.total"
              :show-total="pagination.showTotal"
              :show-page-size="pagination.showPageSize"
              :page-size-options="pagination.pageSizeOptions"
              @change="onPageChange"
              @page-size-change="onPageSizeChange"
            />
          </div>
        </a-card>

        <a-empty v-else description="请选择数据源查看物理表" />
      </a-layout-content>
    </a-layout>

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
              <a-select v-model="formData.datasource_id" placeholder="请选择数据源" disabled>
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
import { Message, Button, Space, Popconfirm, Tag, Tooltip } from '@arco-design/web-vue'
import {
  IconStorage,
  IconPlus,
  IconSync,
  IconEdit,
  IconDelete,
  IconRefresh,
  IconCheckCircle,
  IconClockCircle,
  IconExclamationCircle
} from '@arco-design/web-vue/es/icon'
import { getDatasets, getDataSources, deleteDataset, createDataset, updateDataset, syncDatasetFromSource, syncPhysicalTables } from '@/api/semantic'
import type { Dataset, DataSource, ColumnInfo } from '@/api/types'

const loading = ref(false)
const syncing = ref(false)
const datasets = ref<Dataset[]>([])
const dataSources = ref<DataSource[]>([])
const selectedDatasource = ref('')
const searchKeyword = ref('')
const statusFilter = ref('')
const drawerVisible = ref(false)
const modalVisible = ref(false)
const currentDataset = ref<Dataset | null>(null)
const editingDataset = ref<Dataset | null>(null)

// 分页配置
const pagination = computed(() => {
  let filtered = datasets.value.filter(d => d.datasource_id === selectedDatasource.value)

  // 根据搜索关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = filtered.filter(d =>
      d.name.toLowerCase().includes(keyword) ||
      d.physical_name.toLowerCase().includes(keyword) ||
      d.description?.toLowerCase().includes(keyword)
    )
  }

  return {
    current: paginationState.current,
    pageSize: paginationState.pageSize,
    total: filtered.length,
    showTotal: true,
    showPageSize: true,
    pageSizeOptions: [7, 14, 20, 50]
  }
})

const paginationState = ref({
  current: 1,
  pageSize: 7
})

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
  { title: '数据集名称', dataIndex: 'name', width: 200 },
  { title: '物理表名', dataIndex: 'physical_name', width: 180 },
  { title: 'Schema', dataIndex: 'schema_name', width: 120 },
  {
    title: '字段数',
    width: 100,
    align: 'center',
    render: ({ record }: { record: Dataset }) => {
      if (record && record.columns && Array.isArray(record.columns)) {
        return h(Tag, {}, { default: () => `${record.columns.length} 列` })
      }
      return h(Tag, {}, { default: () => '0 列' })
    }
  },
  { title: '描述', dataIndex: 'description', ellipsis: true, width: 250 },
  {
    title: '操作',
    width: 260,
    fixed: 'right',
    render: ({ record }: { record: Dataset }) => {
      if (!record) {
        return h(Space, {}, { default: () => [] })
      }

      return h(Space, { size: 4 }, {
        default: () => [
          h(Button, {
            type: 'text',
            size: 'small',
            onClick: () => handleViewColumns(record)
          }, { default: () => '查看字段' }),

          h(Button, {
            type: 'text',
            size: 'small',
            status: 'normal',
            onClick: () => handleEdit(record)
          }, { default: () => [h('icon-edit'), ' 编辑'] }),

          h(Popconfirm, {
            content: '确定删除此数据集？',
            onOk: () => handleDelete(record.id)
          }, {
            default: () => h(Button, {
              type: 'text',
              size: 'small',
              status: 'danger',
              danger: true
            }, { default: () => [h('icon-delete'), ' 删除'] })
          })
        ]
      })
    }
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

// 获取当前选中的数据源信息
const selectedDatasourceInfo = computed(() => {
  return dataSources.value.find(ds => ds.id === selectedDatasource.value)
})

// 过滤后的数据源列表
const filteredDataSources = computed(() => {
  if (!statusFilter.value) {
    return dataSources.value
  }
  return dataSources.value.filter(ds => ds.status === statusFilter.value)
})

// 过滤后的数据集（需要分页）
const filteredDatasets = computed(() => {
  let result = datasets.value.filter(d => d.datasource_id === selectedDatasource.value)

  // 根据搜索关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(d =>
      d.name.toLowerCase().includes(keyword) ||
      d.physical_name.toLowerCase().includes(keyword) ||
      d.description?.toLowerCase().includes(keyword)
    )
  }

  // 手动分页：根据当前页和每页条数截取数据
  const start = (paginationState.value.current - 1) * paginationState.value.pageSize
  const end = start + paginationState.value.pageSize
  return result.slice(start, end)
})

// 获取数据源下的表数量
function getDatasourceCount(datasourceId: string) {
  return datasets.value.filter(d => d.datasource_id === datasourceId).length
}

// 获取数据源状态颜色
function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    active: 'green',
    inactive: 'blue',
    error: 'red'
  }
  return colors[status] || 'gray'
}

// 获取数据源状态文本
function getStatusText(status: string) {
  const texts: Record<string, string> = {
    active: '正常',
    inactive: '未连接',
    error: '异常'
  }
  return texts[status] || status
}

// 获取数据源状态图标
function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: IconCheckCircle,
    inactive: IconClockCircle,
    error: IconExclamationCircle
  }
  return icons[status] || IconClockCircle
}

// 获取数据源状态提示
function getStatusTooltip(status: string) {
  const tooltips: Record<string, string> = {
    active: '数据源连接成功，可以正常使用',
    inactive: '数据源刚创建，还未进行连接测试',
    error: '数据源连接测试失败，请检查配置'
  }
  return tooltips[status] || status
}

// 选择数据源
async function selectDatasource(datasourceId: string) {
  selectedDatasource.value = datasourceId
  paginationState.value.current = 1
  searchKeyword.value = ''

  // 切换数据源时自动同步物理表
  if (datasourceId) {
    await syncTables()
  }
}

// 搜索处理
function handleSearch() {
  paginationState.value.current = 1
}

// 分页变化处理
function onPageChange(current: number) {
  paginationState.value.current = current
}

function onPageSizeChange(pageSize: number) {
  paginationState.value.pageSize = pageSize
  paginationState.value.current = 1
}

async function fetchData() {
  loading.value = true
  try {
    const [datasetsResult, sources] = await Promise.all([
      getDatasets(),
      getDataSources()
    ])
    datasets.value = datasetsResult
    dataSources.value = sources

    // 如果已选择数据源，保持选中；否则选择第一个数据源
    if (selectedDatasource.value) {
      if (!sources.find(ds => ds.id === selectedDatasource.value)) {
        selectedDatasource.value = sources.length > 0 ? sources[0].id : ''
      }
    } else {
      selectedDatasource.value = sources.length > 0 ? sources[0].id : ''
    }
  } catch (error) {
    console.error('Failed to fetch data:', error)
    datasets.value = []
    dataSources.value = []
    selectedDatasource.value = ''
  } finally {
    loading.value = false
  }
}

// 刷新数据源列表
async function refreshDataSources() {
  try {
    const sources = await getDataSources()
    dataSources.value = sources
    Message.success('刷新成功')
  } catch (error) {
    Message.error('刷新失败')
  }
}

function showCreateModal() {
  editingDataset.value = null
  formData.value = {
    datasource_id: selectedDatasource.value || '',
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
      if (formData.value.physical_name) {
        const matchedTable = tables.find((t: any) => t.name === formData.value.physical_name)
        if (matchedTable && matchedTable.columns) {
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

async function syncTables() {
  if (!selectedDatasource.value) {
    Message.warning('请先选择数据源')
    return
  }

  loading.value = true
  try {
    const result = await syncPhysicalTables(selectedDatasource.value)
    Message.success(`同步成功，发现 ${result.count} 个表`)
    // 重新加载数据集，不再调用 fetchData 避免循环
    datasets.value = await getDatasets()
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '同步失败'
    Message.error(errorMsg)
    console.error('Sync tables error:', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchData()
  // 进入页面后自动同步默认数据源的物理表
  if (selectedDatasource.value) {
    await syncTables()
  }
})
</script>

<style scoped>
.dataset-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dataset-list :deep(.arco-layout) {
  height: 100%;
}

.dataset-list :deep(.arco-layout-content) {
  height: 100%;
  overflow: hidden;
}

/* 左侧数据源列表样式 */
.datasource-sider {
  background: #fff;
  border-right: 1px solid #e5e6eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e6eb;
  background: #f7f8fa;
}

.sider-title {
  font-weight: 600;
  font-size: 14px;
  color: #1d2129;
}

.sider-filter {
  padding: 12px 16px;
  border-bottom: 1px solid #e5e6eb;
  background: #fff;
}

.datasource-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.datasource-item {
  padding: 12px;
  margin-bottom: 8px;
  background: #f7f8fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.datasource-item:hover {
  background: #e8f3ff;
  border-color: #165dff;
  transform: translateX(4px);
}

.datasource-item.active {
  background: #e6f7ff;
  border-color: #165dff;
  box-shadow: 0 2px 8px rgba(22, 93, 255, 0.15);
}

.datasource-name {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 500;
  color: #1d2129;
}

.datasource-name span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datasource-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #86909c;
}

.datasource-count {
  color: #4e5969;
}

/* 右侧内容区域样式 */
.dataset-content {
  padding: 16px;
  background: #f5f7fa;
  height: 100%;
  overflow: hidden;
}

.dataset-content :deep(.arco-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dataset-content :deep(.arco-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  min-height: 0;
}

.table-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 0;
  padding: 16px;
}

.table-wrapper :deep(.arco-table) {
  margin-bottom: 0;
}

/* 固定操作列样式 - 兼容多种 Arco Design 版本 */
.dataset-content :deep(.arco-table-th-fixed-right),
.dataset-content :deep(.arco-table-td-fixed-right),
.dataset-content :deep(.arco-table-th-fixed-last),
.dataset-content :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 10 !important;
  box-shadow: -6px 0 12px -4px rgba(0, 0, 0, 0.08) !important;
}

.dataset-content :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.dataset-content :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.dataset-content :deep(.arco-table-th-fixed-right)::before,
.dataset-content :deep(.arco-table-td-fixed-right)::before,
.dataset-content :deep(.arco-table-th-fixed-last)::before,
.dataset-content :deep(.arco-table-td-fixed-last)::before {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 1px !important;
  background: #e5e6eb !important;
}

.pagination-wrapper {
  flex-shrink: 0;
  height: 72px;
  padding: 16px 16px 16px 0;
  text-align: right;
  background: #fff;
  border-top: 1px solid #f0f1f2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
</style>
