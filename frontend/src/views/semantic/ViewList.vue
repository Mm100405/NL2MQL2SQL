<template>
  <div class="view-list">
    <a-card title="视图管理">
      <template #extra>
        <a-space>
          <a-select v-model="filterDatasource" placeholder="筛选数据源" allow-clear style="width: 200px">
            <a-option v-for="ds in dataSources" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
          </a-select>
          <a-button type="primary" @click="handleCreate">
            <template #icon><icon-plus /></template>
            新建视图
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data="filteredViews"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        :scroll="{ x: 1200 }"
        :bordered="false"
        :stripe="true"
      >
        <template #view_type="{ record }">
          <a-tag v-if="record?.view_type === 'single_table'" color="blue">单表</a-tag>
          <a-tag v-else-if="record?.view_type === 'joined'" color="green">多表聚合</a-tag>
          <a-tag v-else-if="record?.view_type === 'sql'" color="orange">自定义SQL</a-tag>
          <span v-else>-</span>
        </template>
        <template #column_count="{ record }">
          <a-tag>{{ (record?.columns || []).length }} 列</a-tag>
        </template>
        <template #actions="{ record }">
          <a-space v-if="record" :size="4">
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
              编辑
            </a-button>
            <a-button type="text" size="small" @click="handlePreview(record)">
              <template #icon><icon-eye /></template>
              预览
            </a-button>
            <a-popconfirm content="确定删除此视图？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
                <template #icon><icon-delete /></template>
                删除
              </a-button>
            </a-popconfirm>
          </a-space>
          <span v-else>-</span>
        </template>
      </a-table>
    </a-card>

    <!-- 预览弹窗 -->
    <a-modal v-model:visible="previewVisible" :title="`预览: ${previewView?.name || ''}`" width="900px" :footer="false">
      <div class="preview-sql">
        <div class="sql-label">生成的SQL:</div>
        <pre>{{ previewSql }}</pre>
      </div>
      <a-divider />
      <a-table 
        :columns="previewColumns" 
        :data="previewData" 
        :loading="previewing"
        :pagination="{ pageSize: 10 }"
        size="small"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getViews, deleteView, previewView, generateViewSQL } from '@/api/views'
import { getDataSources } from '@/api/semantic'
import type { View } from '@/api/views'
import type { DataSource } from '@/api/types'

const router = useRouter()
const loading = ref(false)
const previewing = ref(false)
const views = ref<View[]>([])
const dataSources = ref<DataSource[]>([])
const filterDatasource = ref('')
const previewVisible = ref(false)
const previewView = ref<View | null>(null)
const previewSql = ref('')
const previewColumns = ref<any[]>([])
const previewData = ref<any[]>([])

const columns = [
  { title: '视图名称', dataIndex: 'name', width: 200 },
  { title: '显示名称', dataIndex: 'display_name', width: 180 },
  { title: '类型', slotName: 'view_type', width: 100, align: 'center' },
  { title: '字段数', slotName: 'column_count', width: 80, align: 'center' },
  { title: '描述', dataIndex: 'description', ellipsis: true, width: 250 },
  { title: '更新时间', dataIndex: 'updated_at', width: 180 },
  { title: '操作', slotName: 'actions', width: 260, fixed: 'right' }
]

const filteredViews = computed(() => {
  if (!filterDatasource.value) return views.value
  return views.value.filter(v => v.datasource_id === filterDatasource.value)
})

async function fetchData() {
  loading.value = true
  try {
    const [viewsResult, sources] = await Promise.all([
      getViews(),
      getDataSources()
    ])
    views.value = viewsResult
    dataSources.value = sources
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  router.push('/semantic/views/new')
}

function handleEdit(record: View) {
  if (!record?.id) return
  router.push(`/semantic/views/${record.id}`)
}

async function handlePreview(record: View) {
  if (!record?.id) return
  
  previewView.value = record
  previewVisible.value = true
  previewing.value = true
  previewColumns.value = []
  previewData.value = []
  
  try {
    // 获取SQL
    const sqlResult = await generateViewSQL(record.id)
    previewSql.value = sqlResult.sql
    
    // 获取数据
    const result = await previewView(record.id, 100)
    previewColumns.value = result.columns.map(c => ({
      title: c,
      dataIndex: c
    }))
    previewData.value = result.data.map((row, idx) => {
      const obj: Record<string, any> = { _key: idx }
      result.columns.forEach((col, i) => {
        obj[col] = row[i]
      })
      return obj
    })
  } catch (e: any) {
    Message.error(e.message || '预览失败')
  } finally {
    previewing.value = false
  }
}

async function handleDelete(id: string) {
  if (!id) return
  try {
    await deleteView(id)
    Message.success('删除成功')
    fetchData()
  } catch (e: any) {
    Message.error(e.message || '删除失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.view-list {
  height: 100%;
}

.view-list :deep(.arco-table) {
  overflow: visible;
  table-layout: fixed;
}

.view-list :deep(.arco-table-container) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* 固定操作列样式 - 兼容多种 Arco Design 版本 */
.view-list :deep(.arco-table-th-fixed-right),
.view-list :deep(.arco-table-td-fixed-right),
.view-list :deep(.arco-table-th-fixed-last),
.view-list :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 10 !important;
  box-shadow: -6px 0 12px -4px rgba(0, 0, 0, 0.08) !important;
}

.view-list :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.view-list :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.view-list :deep(.arco-table-th-fixed-right)::before,
.view-list :deep(.arco-table-td-fixed-right)::before,
.view-list :deep(.arco-table-th-fixed-last)::before,
.view-list :deep(.arco-table-td-fixed-last)::before {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 1px !important;
  background: #e5e6eb !important;
}

/* 确保表格单元格内容不溢出 */
.view-list :deep(.arco-table-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-sql {
  background: #f7f8fa;
  border-radius: 4px;
  padding: 12px;
}

.sql-label {
  font-weight: 500;
  margin-bottom: 8px;
  color: #86909c;
}

.preview-sql pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  color: #1d2129;
}
</style>
