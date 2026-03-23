<template>
  <div class="view-list">
    <div class="page-header">
      <a-page-header title="视图管理" subtitle="浏览和管理数据视图">
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
      </a-page-header>
    </div>

    <div class="catalog-content">
      <!-- 左侧分类树 -->
      <a-card class="category-tree" title="视图分类">
        <template #extra>
          <a-button type="text" size="small" @click="showCategoryModal = true">
            <icon-plus />
          </a-button>
        </template>
        <a-tree
          :data="categoryTree"
          :default-expand-all="true"
          :selected-keys="selectedCategory"
          @select="handleCategorySelect"
        >
          <template #title="node">
            <div class="tree-node">
              <span>{{ node.title }}</span>
              <span class="node-count">({{ node.count || 0 }})</span>
            </div>
          </template>
        </a-tree>
      </a-card>

      <!-- 右侧视图列表 -->
      <div class="view-list-content">
        <a-card>
          <a-table
            :columns="columns"
            :data="filteredViews"
            :loading="loading"
            :pagination="{ pageSize: 10 }"
            :scroll="{ x: 1200 }"
            :bordered="false"
            :stripe="true"
          >
            <template #category_name="{ record }">
              <a-tag v-if="record?.category_name">{{ record.category_name }}</a-tag>
              <a-tag v-else color="gray">未分类</a-tag>
            </template>
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
      </div>
    </div>

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

    <!-- 新增分类弹窗 -->
    <a-modal
      v-model:visible="showCategoryModal"
      title="新增分类"
      width="400px"
      @ok="handleCreateCategory"
    >
      <a-form :model="categoryForm" layout="vertical">
        <a-form-item label="分类名称" required>
          <a-input v-model="categoryForm.name" placeholder="请输入分类名称" />
        </a-form-item>
        <a-form-item label="父分类">
          <a-tree-select
            v-model="categoryForm.parent_id"
            :data="parentCategoryTree"
            placeholder="选择父分类（可选）"
            allow-clear
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { 
  getViews, 
  deleteView, 
  previewView, 
  generateViewSQL, 
  getCategoryStats, 
  getCategoryTree,
  createCategory,
  type ViewCategory 
} from '@/api/views'
import { getDataSources } from '@/api/semantic'
import type { View } from '@/api/views'
import type { DataSource } from '@/api/types'

const router = useRouter()
const loading = ref(false)
const previewing = ref(false)
const views = ref<View[]>([])
const dataSources = ref<DataSource[]>([])
const filterDatasource = ref('')
const categories = ref<ViewCategory[]>([])
const selectedCategory = ref<string[]>(['all'])
const showCategoryModal = ref(false)
const previewVisible = ref(false)
const previewView = ref<View | null>(null)
const previewSql = ref('')
const previewColumns = ref<any[]>([])
const previewData = ref<any[]>([])

// 分类表单
const categoryForm = ref({
  name: '',
  parent_id: null as string | null
})

const columns = [
  { title: '分类', slotName: 'category_name', width: 120 },
  { title: '视图名称', dataIndex: 'name', width: 200 },
  { title: '显示名称', dataIndex: 'display_name', width: 180 },
  { title: '类型', slotName: 'view_type', width: 100, align: 'center' },
  { title: '字段数', slotName: 'column_count', width: 80, align: 'center' },
  { title: '描述', dataIndex: 'description', ellipsis: true, width: 250 },
  { title: '更新时间', dataIndex: 'updated_at', width: 180 },
  { title: '操作', slotName: 'actions', width: 260, fixed: 'right' }
]

// 分类树数据
const categoryTree = computed(() => {
  const tree = [
    {
      key: 'all',
      title: '全部视图',
      count: views.value.length,
      children: []
    }
  ]

  // 添加定义的分类
  categories.value.forEach(cat => {
    if (!cat.parent_id) {
      tree[0].children.push({
        key: cat.id,
        title: cat.name,
        count: views.value.filter(v => v.category_id === cat.id).length,
        children: getChildren(cat.id)
      })
    }
  })

  // 添加"未分类"节点
  const unclassifiedCount = views.value.filter(v => !v.category_id).length
  if (unclassifiedCount > 0) {
    tree[0].children.push({
      key: 'null',
      title: '未分类',
      count: unclassifiedCount
    })
  }

  return tree
})

// 获取子分类
function getChildren(parentId: string): any[] {
  return categories.value
    .filter(cat => cat.parent_id === parentId)
    .map(cat => ({
      key: cat.id,
      title: cat.name,
      count: views.value.filter(v => v.category_id === cat.id).length,
      children: getChildren(cat.id)
    }))
}

// 父分类选择树（排除"全部视图"和"未分类"）
const parentCategoryTree = computed(() => {
  return buildCategoryTree(categories.value)
})

// 构建分类树用于选择
function buildCategoryTree(cats: ViewCategory[]): any[] {
  const catMap = new Map<string, any>()
  
  // 创建节点映射
  cats.forEach(cat => {
    catMap.set(cat.id, { key: cat.id, title: cat.name, children: [] })
  })
  
  // 构建树结构
  const tree: any[] = []
  cats.forEach(cat => {
    const node = catMap.get(cat.id)!
    if (cat.parent_id && catMap.has(cat.parent_id)) {
      catMap.get(cat.parent_id)!.children.push(node)
    } else {
      tree.push(node)
    }
  })
  
  return tree
}

const filteredViews = computed(() => {
  let result = views.value
  if (filterDatasource.value) {
    result = result.filter(v => v.datasource_id === filterDatasource.value)
  }
  if (selectedCategory.value.length > 0 && selectedCategory.value[0] !== 'all') {
    const selectedId = selectedCategory.value[0]
    if (selectedId === 'null') {
      result = result.filter(v => !v.category_id)
    } else {
      result = result.filter(v => v.category_id === selectedId)
    }
  }
  return result
})

async function fetchData() {
  loading.value = true
  try {
    const [viewsResult, sources, categoryStats, categoryList] = await Promise.all([
      getViews(),
      getDataSources(),
      getCategoryStats(),
      getCategoryTree()
    ])
    views.value = viewsResult
    dataSources.value = sources
    categories.value = flattenCategories(categoryList)
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

// 扁平化分类树
function flattenCategories(tree: any[]): ViewCategory[] {
  const result: ViewCategory[] = []
  function traverse(nodes: any[]) {
    nodes.forEach(node => {
      const cat: ViewCategory = {
        id: node.key,
        name: node.title,
        description: node.description,
        parent_id: node.parent_id || null,
        created_at: node.created_at || new Date().toISOString(),
        updated_at: node.updated_at || new Date().toISOString()
      }
      result.push(cat)
      if (node.children && node.children.length > 0) {
        traverse(node.children)
      }
    })
  }
  traverse(tree)
  return result
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

function handleCategorySelect(keys: string[]) {
  selectedCategory.value = keys
}

// 新增分类
async function handleCreateCategory() {
  if (!categoryForm.value.name) {
    Message.error('请输入分类名称')
    return
  }

  try {
    await createCategory({
      name: categoryForm.value.name,
      description: '',
      parent_id: categoryForm.value.parent_id
    })
    Message.success('分类创建成功')
    showCategoryModal.value = false
    categoryForm.value.name = ''
    categoryForm.value.parent_id = null
    
    // 重新加载分类
    await fetchData()
  } catch (e: any) {
    Message.error(e.message || '创建分类失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.view-list {
  padding: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  flex-shrink: 0;
}

.catalog-content {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow: hidden;
  padding: 16px;
}

.category-tree {
  width: 240px;
  flex-shrink: 0;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

.node-count {
  font-size: 12px;
  color: #86909c;
}

.view-list-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.view-list-content :deep(.arco-table) {
  overflow: visible;
  table-layout: fixed;
}

.view-list-content :deep(.arco-table-container) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* 固定操作列样式 - 兼容多种 Arco Design 版本 */
.view-list-content :deep(.arco-table-th-fixed-right),
.view-list-content :deep(.arco-table-td-fixed-right),
.view-list-content :deep(.arco-table-th-fixed-last),
.view-list-content :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 10 !important;
  box-shadow: -6px 0 12px -4px rgba(0, 0, 0, 0.08) !important;
}

.view-list-content :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.view-list-content :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.view-list-content :deep(.arco-table-th-fixed-right)::before,
.view-list-content :deep(.arco-table-td-fixed-right)::before,
.view-list-content :deep(.arco-table-th-fixed-last)::before,
.view-list-content :deep(.arco-table-td-fixed-last)::before {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 1px !important;
  background: #e5e6eb !important;
}

/* 确保表格单元格内容不溢出 */
.view-list-content :deep(.arco-table-cell) {
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
