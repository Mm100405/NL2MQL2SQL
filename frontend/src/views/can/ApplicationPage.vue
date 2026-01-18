<template>
  <div class="application-page">
    <a-page-header title="指标应用" subtitle="将指标应用到仪表盘、报表和数据产品">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建应用
        </a-button>
      </template>
    </a-page-header>

    <!-- 应用概览 -->
    <a-row :gutter="16" class="overview-cards">
      <a-col :span="6">
        <a-card>
          <a-statistic title="应用总数" :value="applications.length">
            <template #prefix><icon-apps /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="仪表盘" :value="dashboardCount">
            <template #prefix><icon-dashboard /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="报表" :value="reportCount">
            <template #prefix><icon-file /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="API" :value="apiCount">
            <template #prefix><icon-code /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 应用列表 -->
    <a-card class="application-list">
      <a-tabs default-active-key="all" @change="handleTabChange">
        <a-tab-pane key="all" title="全部">
          <div class="app-grid">
            <a-card v-for="app in filteredApplications" :key="app.id" class="app-card" hoverable>
              <div class="app-header">
                <div class="app-icon" :style="{ background: getAppIconBg(app.type) }">
                  <component :is="getAppIcon(app.type)" :size="24" />
                </div>
                <div class="app-info">
                  <div class="app-name">{{ app.name }}</div>
                  <div class="app-type">{{ getAppTypeName(app.type) }}</div>
                </div>
                <a-dropdown>
                  <a-button type="text" size="small"><icon-more /></a-button>
                  <template #content>
                    <a-doption @click="editApp(app)">编辑</a-doption>
                    <a-doption @click="viewApp(app)">预览</a-doption>
                    <a-doption @click="shareApp(app)">分享</a-doption>
                    <a-doption class="danger" @click="deleteApp(app)">删除</a-doption>
                  </template>
                </a-dropdown>
              </div>
              <div class="app-desc">{{ app.description }}</div>
              <div class="app-metrics">
                <div class="metrics-label">包含指标:</div>
                <div class="metrics-list">
                  <a-tag v-for="metric in app.metrics.slice(0, 3)" :key="metric" size="small">
                    {{ metric }}
                  </a-tag>
                  <a-tag v-if="app.metrics.length > 3" size="small">
                    +{{ app.metrics.length - 3 }}
                  </a-tag>
                </div>
              </div>
              <div class="app-footer">
                <div class="app-meta">
                  <span><icon-user /> {{ app.owner }}</span>
                  <span><icon-clock-circle /> {{ app.updatedAt }}</span>
                </div>
                <div class="app-stats">
                  <span><icon-eye /> {{ app.viewCount }}</span>
                </div>
              </div>
            </a-card>
          </div>
        </a-tab-pane>
        <a-tab-pane key="dashboard" title="仪表盘" />
        <a-tab-pane key="report" title="报表" />
        <a-tab-pane key="api" title="API服务" />
      </a-tabs>
    </a-card>

    <!-- 新建应用弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建指标应用"
      width="640px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="应用名称" required>
          <a-input v-model="createForm.name" placeholder="请输入应用名称" />
        </a-form-item>
        <a-form-item label="应用类型" required>
          <a-radio-group v-model="createForm.type">
            <a-radio value="dashboard">
              <div class="type-option">
                <icon-dashboard />
                <span>仪表盘</span>
              </div>
            </a-radio>
            <a-radio value="report">
              <div class="type-option">
                <icon-file />
                <span>报表</span>
              </div>
            </a-radio>
            <a-radio value="api">
              <div class="type-option">
                <icon-code />
                <span>API服务</span>
              </div>
            </a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="选择指标" required>
          <a-select v-model="createForm.metrics" placeholder="请选择要应用的指标" multiple>
            <a-option value="gmv">销售额 (gmv)</a-option>
            <a-option value="order_count">订单量 (order_count)</a-option>
            <a-option value="avg_order_value">客单价 (avg_order_value)</a-option>
            <a-option value="new_users">新增用户数 (new_users)</a-option>
            <a-option value="retention_rate">用户留存率 (retention_rate)</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入应用描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 应用预览弹窗 -->
    <a-modal
      v-model:visible="showPreviewModal"
      :title="currentApp?.name || '应用预览'"
      width="900px"
      :footer="false"
    >
      <div v-if="currentApp" class="preview-content">
        <div v-if="currentApp.type === 'dashboard'" class="dashboard-preview">
          <a-row :gutter="16">
            <a-col :span="8" v-for="metric in currentApp.metrics" :key="metric">
              <a-card class="metric-preview-card">
                <a-statistic :title="metric" :value="Math.floor(Math.random() * 10000)" />
              </a-card>
            </a-col>
          </a-row>
          <a-card class="chart-preview" style="margin-top: 16px">
            <div class="chart-placeholder">
              <icon-bar-chart :size="48" />
              <span>图表预览区域</span>
            </div>
          </a-card>
        </div>
        <div v-else-if="currentApp.type === 'report'" class="report-preview">
          <a-table :columns="reportColumns" :data="reportData" :pagination="false" />
        </div>
        <div v-else class="api-preview">
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="API端点">
              <code>GET /api/v1/metrics/query</code>
            </a-descriptions-item>
            <a-descriptions-item label="请求参数">
              <pre class="api-code">{{ apiRequestExample }}</pre>
            </a-descriptions-item>
            <a-descriptions-item label="响应示例">
              <pre class="api-code">{{ apiResponseExample }}</pre>
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Application {
  id: number
  name: string
  type: 'dashboard' | 'report' | 'api'
  description: string
  metrics: string[]
  owner: string
  updatedAt: string
  viewCount: number
}

const currentTab = ref('all')
const showCreateModal = ref(false)
const showPreviewModal = ref(false)
const currentApp = ref<Application | null>(null)

const createForm = ref({
  name: '',
  type: 'dashboard',
  metrics: [] as string[],
  description: ''
})

const applications = ref<Application[]>([
  {
    id: 1,
    name: '销售总览仪表盘',
    type: 'dashboard',
    description: '展示核心销售指标，包括销售额、订单量、客单价等',
    metrics: ['gmv', 'order_count', 'avg_order_value'],
    owner: 'admin',
    updatedAt: '2024-01-15',
    viewCount: 1256
  },
  {
    id: 2,
    name: '用户增长报表',
    type: 'report',
    description: '每日/每周用户增长数据报表',
    metrics: ['new_users', 'retention_rate'],
    owner: 'analyst',
    updatedAt: '2024-01-14',
    viewCount: 456
  },
  {
    id: 3,
    name: '指标查询API',
    type: 'api',
    description: '提供指标查询的REST API服务',
    metrics: ['gmv', 'order_count', 'new_users', 'retention_rate'],
    owner: 'data_team',
    updatedAt: '2024-01-13',
    viewCount: 892
  },
  {
    id: 4,
    name: '运营日报仪表盘',
    type: 'dashboard',
    description: '运营团队日常监控仪表盘',
    metrics: ['gmv', 'new_users'],
    owner: 'ops',
    updatedAt: '2024-01-12',
    viewCount: 678
  },
  {
    id: 5,
    name: '财务月报',
    type: 'report',
    description: '月度财务数据汇总报表',
    metrics: ['gmv', 'gross_margin'],
    owner: 'finance',
    updatedAt: '2024-01-10',
    viewCount: 234
  }
])

const reportColumns = [
  { title: '日期', dataIndex: 'date' },
  { title: '销售额', dataIndex: 'gmv' },
  { title: '订单量', dataIndex: 'order_count' },
  { title: '客单价', dataIndex: 'avg_order_value' }
]

const reportData = [
  { date: '2024-01-15', gmv: '¥125,680', order_count: 1256, avg_order_value: '¥100' },
  { date: '2024-01-14', gmv: '¥118,420', order_count: 1184, avg_order_value: '¥100' },
  { date: '2024-01-13', gmv: '¥132,560', order_count: 1326, avg_order_value: '¥100' }
]

const apiRequestExample = `{
  "metrics": ["gmv", "order_count"],
  "dimensions": ["date", "channel"],
  "filters": {
    "date": ["2024-01-01", "2024-01-15"]
  }
}`

const apiResponseExample = `{
  "success": true,
  "data": [
    { "date": "2024-01-15", "channel": "web", "gmv": 50000, "order_count": 500 },
    { "date": "2024-01-15", "channel": "app", "gmv": 75000, "order_count": 750 }
  ]
}`

const dashboardCount = computed(() => applications.value.filter(a => a.type === 'dashboard').length)
const reportCount = computed(() => applications.value.filter(a => a.type === 'report').length)
const apiCount = computed(() => applications.value.filter(a => a.type === 'api').length)

const filteredApplications = computed(() => {
  if (currentTab.value === 'all') return applications.value
  return applications.value.filter(a => a.type === currentTab.value)
})

function handleTabChange(key: string) {
  currentTab.value = key
}

function getAppIcon(type: string) {
  const icons: Record<string, string> = {
    dashboard: 'icon-dashboard',
    report: 'icon-file',
    api: 'icon-code'
  }
  return icons[type] || 'icon-apps'
}

function getAppIconBg(type: string) {
  const colors: Record<string, string> = {
    dashboard: '#e8f3ff',
    report: '#e8ffea',
    api: '#f5e8ff'
  }
  return colors[type] || '#f2f3f5'
}

function getAppTypeName(type: string) {
  const names: Record<string, string> = {
    dashboard: '仪表盘',
    report: '报表',
    api: 'API服务'
  }
  return names[type] || type
}

function editApp(app: Application) {
  Message.info(`编辑应用: ${app.name}`)
}

function viewApp(app: Application) {
  currentApp.value = app
  showPreviewModal.value = true
}

function shareApp(app: Application) {
  Message.info(`分享应用: ${app.name}`)
}

function deleteApp(app: Application) {
  Message.warning(`删除应用: ${app.name}`)
}

function handleCreate() {
  if (!createForm.value.name || createForm.value.metrics.length === 0) {
    Message.error('请填写必填项')
    return
  }
  applications.value.push({
    id: Date.now(),
    name: createForm.value.name,
    type: createForm.value.type as Application['type'],
    description: createForm.value.description,
    metrics: createForm.value.metrics,
    owner: 'admin',
    updatedAt: new Date().toISOString().split('T')[0] || '',
    viewCount: 0
  })
  Message.success('创建成功')
  showCreateModal.value = false
  createForm.value = { name: '', type: 'dashboard', metrics: [], description: '' }
}
</script>

<style scoped>
.application-page {
  padding: 0;
}

.overview-cards {
  margin-top: 16px;
}

.application-list {
  margin-top: 16px;
}

.app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.app-card {
  cursor: pointer;
}

.app-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.app-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #165dff;
}

.app-info {
  flex: 1;
}

.app-name {
  font-size: 16px;
  font-weight: 500;
}

.app-type {
  font-size: 12px;
  color: #86909c;
}

.app-desc {
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.app-metrics {
  margin-bottom: 12px;
}

.metrics-label {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 4px;
}

.metrics-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.app-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}

.app-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #86909c;
}

.app-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.app-stats {
  font-size: 12px;
  color: #86909c;
  display: flex;
  align-items: center;
  gap: 4px;
}

.type-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.preview-content {
  min-height: 400px;
}

.metric-preview-card {
  text-align: center;
}

.chart-preview {
  height: 300px;
}

.chart-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c9cdd4;
  gap: 8px;
}

.api-code {
  background: #f7f8fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  margin: 0;
  white-space: pre-wrap;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
