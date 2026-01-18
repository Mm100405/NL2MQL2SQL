<template>
  <div class="catalog-page">
    <a-page-header title="指标目录" subtitle="浏览和管理企业指标资产目录">
      <template #extra>
        <a-space>
          <a-input-search v-model="searchText" placeholder="搜索指标" style="width: 240px" />
          <a-button type="primary" @click="showCreateModal = true">
            <template #icon><icon-plus /></template>
            新建指标
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <div class="catalog-content">
      <!-- 左侧分类树 -->
      <a-card class="category-tree" title="指标分类">
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

      <!-- 右侧指标列表 -->
      <div class="metric-list">
        <!-- 筛选条件 -->
        <a-card class="filter-card">
          <a-space wrap>
            <a-select v-model="filterType" placeholder="指标类型" style="width: 120px" allow-clear>
              <a-option value="basic">基础指标</a-option>
              <a-option value="derived">派生指标</a-option>
              <a-option value="composite">复合指标</a-option>
            </a-select>
            <a-select v-model="filterStatus" placeholder="状态" style="width: 100px" allow-clear>
              <a-option value="published">已发布</a-option>
              <a-option value="draft">草稿</a-option>
              <a-option value="deprecated">已废弃</a-option>
            </a-select>
            <a-select v-model="filterOwner" placeholder="负责人" style="width: 120px" allow-clear>
              <a-option value="admin">admin</a-option>
              <a-option value="analyst">analyst</a-option>
              <a-option value="data_team">data_team</a-option>
            </a-select>
            <a-range-picker v-model="filterDate" style="width: 240px" />
          </a-space>
        </a-card>

        <!-- 指标卡片列表 -->
        <div class="metric-grid">
          <a-card
            v-for="metric in filteredMetrics"
            :key="metric.id"
            class="metric-card"
            hoverable
            @click="viewMetricDetail(metric)"
          >
            <div class="metric-header">
              <div class="metric-title-row">
                <span class="metric-name">{{ metric.name }}</span>
                <a-tag :color="getTypeColor(metric.type)" size="small">{{ getTypeName(metric.type) }}</a-tag>
              </div>
              <a-tag :color="getStatusColor(metric.status)" size="small">{{ getStatusName(metric.status) }}</a-tag>
            </div>
            <div class="metric-code">{{ metric.code }}</div>
            <div class="metric-desc">{{ metric.description }}</div>
            <div class="metric-meta">
              <div class="meta-item">
                <icon-user /> {{ metric.owner }}
              </div>
              <div class="meta-item">
                <icon-clock-circle /> {{ metric.updatedAt }}
              </div>
            </div>
            <div class="metric-tags">
              <a-tag v-for="tag in metric.tags" :key="tag" size="small">{{ tag }}</a-tag>
            </div>
            <div class="metric-actions">
              <a-button type="text" size="small" @click.stop="editMetric(metric)">
                <icon-edit />
              </a-button>
              <a-button type="text" size="small" @click.stop="applyMetric(metric)">
                <icon-apps />
              </a-button>
              <a-button type="text" size="small" @click.stop="viewLineage(metric)">
                <icon-branch />
              </a-button>
              <a-dropdown>
                <a-button type="text" size="small" @click.stop><icon-more /></a-button>
                <template #content>
                  <a-doption @click="duplicateMetric(metric)">复制</a-doption>
                  <a-doption @click="exportMetric(metric)">导出</a-doption>
                  <a-doption v-if="metric.status === 'published'" @click="deprecateMetric(metric)">废弃</a-doption>
                  <a-doption v-if="metric.status === 'draft'" @click="publishMetric(metric)">发布</a-doption>
                  <a-doption class="danger" @click="deleteMetric(metric)">删除</a-doption>
                </template>
              </a-dropdown>
            </div>
          </a-card>
        </div>

        <a-pagination
          :total="totalMetrics"
          :current="currentPage"
          :page-size="pageSize"
          show-total
          show-jumper
          @change="handlePageChange"
          style="margin-top: 16px; text-align: right"
        />
      </div>
    </div>

    <!-- 指标详情抽屉 -->
    <a-drawer
      v-model:visible="showDetailDrawer"
      :title="currentMetric?.name || '指标详情'"
      width="640px"
    >
      <template v-if="currentMetric">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="指标编码">{{ currentMetric.code }}</a-descriptions-item>
          <a-descriptions-item label="指标类型">{{ getTypeName(currentMetric.type) }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="getStatusColor(currentMetric.status)">{{ getStatusName(currentMetric.status) }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="负责人">{{ currentMetric.owner }}</a-descriptions-item>
          <a-descriptions-item label="所属分类" :span="2">{{ currentMetric.category }}</a-descriptions-item>
          <a-descriptions-item label="描述" :span="2">{{ currentMetric.description }}</a-descriptions-item>
          <a-descriptions-item label="计算逻辑" :span="2">
            <pre class="formula-code">{{ currentMetric.formula }}</pre>
          </a-descriptions-item>
          <a-descriptions-item label="关联维度" :span="2">
            <a-space>
              <a-tag v-for="dim in currentMetric.dimensions" :key="dim">{{ dim }}</a-tag>
            </a-space>
          </a-descriptions-item>
          <a-descriptions-item label="标签" :span="2">
            <a-space>
              <a-tag v-for="tag in currentMetric.tags" :key="tag" color="arcoblue">{{ tag }}</a-tag>
            </a-space>
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">{{ currentMetric.createdAt }}</a-descriptions-item>
          <a-descriptions-item label="更新时间">{{ currentMetric.updatedAt }}</a-descriptions-item>
        </a-descriptions>

        <a-divider>使用统计</a-divider>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-statistic title="查询次数" :value="currentMetric.queryCount" />
          </a-col>
          <a-col :span="8">
            <a-statistic title="应用数量" :value="currentMetric.applicationCount" />
          </a-col>
          <a-col :span="8">
            <a-statistic title="依赖指标数" :value="currentMetric.dependencyCount" />
          </a-col>
        </a-row>
      </template>
    </a-drawer>

    <!-- 新建指标弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建指标"
      width="720px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="指标名称" required>
              <a-input v-model="createForm.name" placeholder="请输入指标名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="指标编码" required>
              <a-input v-model="createForm.code" placeholder="请输入指标编码" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="指标类型" required>
              <a-select v-model="createForm.type" placeholder="请选择">
                <a-option value="basic">基础指标</a-option>
                <a-option value="derived">派生指标</a-option>
                <a-option value="composite">复合指标</a-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="所属分类" required>
              <a-tree-select
                v-model="createForm.category"
                :data="categoryTree"
                placeholder="请选择分类"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="计算逻辑" required>
          <a-textarea v-model="createForm.formula" placeholder="SUM(amount)" :auto-size="{ minRows: 3, maxRows: 6 }" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入指标描述" />
        </a-form-item>
        <a-form-item label="标签">
          <a-input-tag v-model="createForm.tags" placeholder="输入后按回车添加标签" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Metric {
  id: number
  name: string
  code: string
  type: 'basic' | 'derived' | 'composite'
  status: 'published' | 'draft' | 'deprecated'
  category: string
  description: string
  formula: string
  owner: string
  tags: string[]
  dimensions: string[]
  createdAt: string
  updatedAt: string
  queryCount: number
  applicationCount: number
  dependencyCount: number
}

const searchText = ref('')
const filterType = ref('')
const filterStatus = ref('')
const filterOwner = ref('')
const filterDate = ref<string[]>([])
const selectedCategory = ref<string[]>(['all'])
const currentPage = ref(1)
const pageSize = ref(12)
const showCreateModal = ref(false)
const showCategoryModal = ref(false)
const showDetailDrawer = ref(false)
const currentMetric = ref<Metric | null>(null)

const createForm = ref({
  name: '',
  code: '',
  type: 'basic',
  category: '',
  formula: '',
  description: '',
  tags: [] as string[]
})

const categoryTree = ref([
  {
    key: 'all',
    title: '全部指标',
    count: 24,
    children: [
      {
        key: 'sales',
        title: '销售指标',
        count: 8,
        children: [
          { key: 'sales-revenue', title: '收入类', count: 4 },
          { key: 'sales-order', title: '订单类', count: 4 }
        ]
      },
      {
        key: 'user',
        title: '用户指标',
        count: 6,
        children: [
          { key: 'user-growth', title: '增长类', count: 3 },
          { key: 'user-retention', title: '留存类', count: 3 }
        ]
      },
      {
        key: 'product',
        title: '产品指标',
        count: 5
      },
      {
        key: 'finance',
        title: '财务指标',
        count: 5
      }
    ]
  }
])

const metrics = ref<Metric[]>([
  {
    id: 1,
    name: '销售额',
    code: 'gmv',
    type: 'basic',
    status: 'published',
    category: '销售指标/收入类',
    description: '统计周期内所有已完成订单的总金额',
    formula: 'SUM(order_amount) WHERE order_status = "completed"',
    owner: 'admin',
    tags: ['核心', '销售'],
    dimensions: ['日期', '渠道', '地区', '商品类目'],
    createdAt: '2024-01-01 10:00',
    updatedAt: '2024-01-15 16:30',
    queryCount: 1256,
    applicationCount: 8,
    dependencyCount: 0
  },
  {
    id: 2,
    name: '订单量',
    code: 'order_count',
    type: 'basic',
    status: 'published',
    category: '销售指标/订单类',
    description: '统计周期内的订单总数',
    formula: 'COUNT(DISTINCT order_id)',
    owner: 'admin',
    tags: ['核心', '销售'],
    dimensions: ['日期', '渠道', '地区'],
    createdAt: '2024-01-01 10:00',
    updatedAt: '2024-01-14 14:20',
    queryCount: 892,
    applicationCount: 6,
    dependencyCount: 0
  },
  {
    id: 3,
    name: '客单价',
    code: 'avg_order_value',
    type: 'derived',
    status: 'published',
    category: '销售指标/收入类',
    description: '平均每个订单的金额',
    formula: 'gmv / order_count',
    owner: 'analyst',
    tags: ['销售', '分析'],
    dimensions: ['日期', '渠道'],
    createdAt: '2024-01-02 11:00',
    updatedAt: '2024-01-15 09:00',
    queryCount: 456,
    applicationCount: 4,
    dependencyCount: 2
  },
  {
    id: 4,
    name: '新增用户数',
    code: 'new_users',
    type: 'basic',
    status: 'published',
    category: '用户指标/增长类',
    description: '统计周期内新注册的用户数量',
    formula: 'COUNT(DISTINCT user_id) WHERE is_new = 1',
    owner: 'data_team',
    tags: ['用户', '增长'],
    dimensions: ['日期', '渠道', '来源'],
    createdAt: '2024-01-03 09:00',
    updatedAt: '2024-01-15 11:00',
    queryCount: 678,
    applicationCount: 5,
    dependencyCount: 0
  },
  {
    id: 5,
    name: '用户留存率',
    code: 'retention_rate',
    type: 'composite',
    status: 'draft',
    category: '用户指标/留存类',
    description: 'N日后仍活跃的用户占比',
    formula: 'retained_users / new_users * 100',
    owner: 'analyst',
    tags: ['用户', '留存'],
    dimensions: ['日期', '留存天数'],
    createdAt: '2024-01-10 14:00',
    updatedAt: '2024-01-15 16:00',
    queryCount: 123,
    applicationCount: 2,
    dependencyCount: 2
  },
  {
    id: 6,
    name: '毛利率',
    code: 'gross_margin',
    type: 'derived',
    status: 'deprecated',
    category: '财务指标',
    description: '(收入-成本)/收入*100%',
    formula: '(revenue - cost) / revenue * 100',
    owner: 'finance',
    tags: ['财务', '利润'],
    dimensions: ['日期', '业务线'],
    createdAt: '2024-01-05 10:00',
    updatedAt: '2024-01-12 15:00',
    queryCount: 89,
    applicationCount: 1,
    dependencyCount: 2
  }
])

const totalMetrics = computed(() => metrics.value.length)

const filteredMetrics = computed(() => {
  let result = metrics.value
  if (searchText.value) {
    result = result.filter(m => 
      m.name.includes(searchText.value) || 
      m.code.includes(searchText.value) ||
      m.description.includes(searchText.value)
    )
  }
  if (filterType.value) {
    result = result.filter(m => m.type === filterType.value)
  }
  if (filterStatus.value) {
    result = result.filter(m => m.status === filterStatus.value)
  }
  if (filterOwner.value) {
    result = result.filter(m => m.owner === filterOwner.value)
  }
  return result
})

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    basic: 'blue',
    derived: 'green',
    composite: 'purple'
  }
  return colors[type] || 'gray'
}

function getTypeName(type: string) {
  const names: Record<string, string> = {
    basic: '基础',
    derived: '派生',
    composite: '复合'
  }
  return names[type] || type
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    published: 'green',
    draft: 'orange',
    deprecated: 'gray'
  }
  return colors[status] || 'gray'
}

function getStatusName(status: string) {
  const names: Record<string, string> = {
    published: '已发布',
    draft: '草稿',
    deprecated: '已废弃'
  }
  return names[status] || status
}

function handleCategorySelect(keys: string[]) {
  selectedCategory.value = keys
}

function handlePageChange(page: number) {
  currentPage.value = page
}

function viewMetricDetail(metric: Metric) {
  currentMetric.value = metric
  showDetailDrawer.value = true
}

function editMetric(metric: Metric) {
  Message.info(`编辑指标: ${metric.name}`)
}

function applyMetric(metric: Metric) {
  Message.info(`应用指标: ${metric.name}`)
}

function viewLineage(metric: Metric) {
  Message.info(`查看血缘: ${metric.name}`)
}

function duplicateMetric(metric: Metric) {
  Message.info(`复制指标: ${metric.name}`)
}

function exportMetric(metric: Metric) {
  Message.info(`导出指标: ${metric.name}`)
}

function deprecateMetric(metric: Metric) {
  metric.status = 'deprecated'
  Message.success('指标已废弃')
}

function publishMetric(metric: Metric) {
  metric.status = 'published'
  Message.success('指标已发布')
}

function deleteMetric(metric: Metric) {
  Message.warning(`删除指标: ${metric.name}`)
}

function handleCreate() {
  if (!createForm.value.name || !createForm.value.code || !createForm.value.formula) {
    Message.error('请填写必填项')
    return
  }
  Message.success('创建成功')
  showCreateModal.value = false
}
</script>

<style scoped>
.catalog-page {
  padding: 0;
}

.catalog-content {
  display: flex;
  gap: 16px;
  margin-top: 16px;
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

.metric-list {
  flex: 1;
  min-width: 0;
}

.filter-card {
  margin-bottom: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.metric-card {
  cursor: pointer;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.metric-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-name {
  font-size: 16px;
  font-weight: 500;
}

.metric-code {
  font-size: 12px;
  color: #86909c;
  font-family: monospace;
  margin-bottom: 8px;
}

.metric-desc {
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.metric-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.metric-tags {
  margin-bottom: 12px;
}

.metric-actions {
  display: flex;
  gap: 4px;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}

.formula-code {
  background: #f7f8fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  margin: 0;
  white-space: pre-wrap;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
