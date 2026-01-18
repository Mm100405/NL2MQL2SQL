<template>
  <div class="acceleration-page">
    <a-page-header title="数据加速" subtitle="配置数据预计算和物化视图加速查询">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建加速任务
        </a-button>
      </template>
    </a-page-header>

    <!-- 加速概览 -->
    <a-row :gutter="16" class="overview-cards">
      <a-col :span="6">
        <a-card>
          <div class="stat-card">
            <div class="stat-icon" style="background: #e8f3ff">
              <icon-thunderbolt :size="24" style="color: #165dff" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ accelerations.length }}</div>
              <div class="stat-label">加速任务</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-card">
            <div class="stat-icon" style="background: #e8ffea">
              <icon-check-circle :size="24" style="color: #00b42a" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ enabledCount }}</div>
              <div class="stat-label">已启用</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-card">
            <div class="stat-icon" style="background: #fff7e8">
              <icon-clock-circle :size="24" style="color: #ff7d00" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ avgSpeedup }}x</div>
              <div class="stat-label">平均加速比</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-card">
            <div class="stat-icon" style="background: #f5e8ff">
              <icon-storage :size="24" style="color: #722ed1" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalStorage }}</div>
              <div class="stat-label">存储占用</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 加速任务列表 -->
    <a-card class="acceleration-list" title="加速任务列表">
      <template #extra>
        <a-input-search v-model="searchText" placeholder="搜索" style="width: 200px" />
      </template>

      <a-table :columns="columns" :data="filteredAccelerations" :pagination="{ pageSize: 10 }">
        <template #name="{ record }">
          <div class="task-name">
            <icon-thunderbolt :style="{ color: record.enabled ? '#165dff' : '#c9cdd4' }" />
            <div>
              <div class="name-text">{{ record.name }}</div>
              <div class="name-desc">{{ record.description }}</div>
            </div>
          </div>
        </template>
        <template #type="{ record }">
          <a-tag :color="getTypeColor(record.type)">{{ record.type }}</a-tag>
        </template>
        <template #enabled="{ record }">
          <a-switch v-model="record.enabled" size="small" @change="handleToggle(record)" />
        </template>
        <template #speedup="{ record }">
          <div class="speedup-info">
            <span class="speedup-value">{{ record.speedup }}x</span>
            <a-progress
              :percent="Math.min(record.speedup * 10, 100)"
              :show-text="false"
              size="small"
              style="width: 60px"
            />
          </div>
        </template>
        <template #schedule="{ record }">
          <div class="schedule-info">
            <div>{{ record.schedule }}</div>
            <div class="next-run">下次: {{ record.nextRun }}</div>
          </div>
        </template>
        <template #storage="{ record }">
          <span>{{ record.storage }}</span>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-tooltip content="立即刷新">
              <a-button type="text" size="small" @click="refreshNow(record)">
                <icon-sync />
              </a-button>
            </a-tooltip>
            <a-tooltip content="查看详情">
              <a-button type="text" size="small" @click="viewDetail(record)">
                <icon-eye />
              </a-button>
            </a-tooltip>
            <a-dropdown>
              <a-button type="text" size="small"><icon-more /></a-button>
              <template #content>
                <a-doption @click="editAcceleration(record)">编辑</a-doption>
                <a-doption @click="viewQuery(record)">查看SQL</a-doption>
                <a-doption class="danger" @click="deleteAcceleration(record)">删除</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新建加速任务弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建数据加速任务"
      width="720px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="任务名称" required>
          <a-input v-model="createForm.name" placeholder="请输入任务名称" />
        </a-form-item>
        <a-form-item label="加速类型" required>
          <a-radio-group v-model="createForm.type">
            <a-radio value="materialized_view">
              <div class="type-option">
                <div class="type-title">物化视图</div>
                <div class="type-desc">预计算并存储查询结果</div>
              </div>
            </a-radio>
            <a-radio value="cube">
              <div class="type-option">
                <div class="type-title">OLAP Cube</div>
                <div class="type-desc">多维数据预聚合</div>
              </div>
            </a-radio>
            <a-radio value="cache">
              <div class="type-option">
                <div class="type-title">查询缓存</div>
                <div class="type-desc">缓存热点查询结果</div>
              </div>
            </a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="源数据" required>
          <a-select v-model="createForm.sourceTable" placeholder="请选择源表">
            <a-option value="dwd_order_wide">dwd_order_wide</a-option>
            <a-option value="dwd_user_behavior">dwd_user_behavior</a-option>
            <a-option value="dim_product">dim_product</a-option>
            <a-option value="dim_user">dim_user</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="加速SQL" required>
          <a-textarea
            v-model="createForm.query"
            placeholder="SELECT ... FROM ... GROUP BY ..."
            :auto-size="{ minRows: 4, maxRows: 8 }"
          />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="刷新策略">
              <a-select v-model="createForm.refreshPolicy">
                <a-option value="manual">手动刷新</a-option>
                <a-option value="schedule">定时刷新</a-option>
                <a-option value="realtime">实时刷新</a-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item v-if="createForm.refreshPolicy === 'schedule'" label="刷新周期">
              <a-select v-model="createForm.schedule">
                <a-option value="hourly">每小时</a-option>
                <a-option value="daily">每天</a-option>
                <a-option value="weekly">每周</a-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- SQL查看弹窗 -->
    <a-modal v-model:visible="showSqlModal" title="加速SQL" :footer="false" width="640px">
      <pre class="sql-code">{{ currentSql }}</pre>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Acceleration {
  id: number
  name: string
  description: string
  type: string
  sourceTable: string
  query: string
  enabled: boolean
  speedup: number
  schedule: string
  nextRun: string
  storage: string
  lastRefresh: string
}

const searchText = ref('')
const showCreateModal = ref(false)
const showSqlModal = ref(false)
const currentSql = ref('')

const createForm = ref({
  name: '',
  type: 'materialized_view',
  sourceTable: '',
  query: '',
  refreshPolicy: 'schedule',
  schedule: 'daily',
  description: ''
})

const accelerations = ref<Acceleration[]>([
  {
    id: 1,
    name: '销售日报汇总',
    description: '按天汇总销售数据',
    type: '物化视图',
    sourceTable: 'dwd_order_wide',
    query: 'SELECT date, SUM(amount) as total_amount, COUNT(*) as order_count FROM dwd_order_wide GROUP BY date',
    enabled: true,
    speedup: 8.5,
    schedule: '每小时',
    nextRun: '11:00',
    storage: '2.3GB',
    lastRefresh: '2024-01-15 10:00'
  },
  {
    id: 2,
    name: '用户行为Cube',
    description: '用户行为多维聚合',
    type: 'OLAP Cube',
    sourceTable: 'dwd_user_behavior',
    query: 'CREATE CUBE user_behavior_cube ON dwd_user_behavior DIMENSIONS (user_id, event_type, platform, date) MEASURES (COUNT(*), SUM(duration))',
    enabled: true,
    speedup: 15.2,
    schedule: '每天',
    nextRun: '00:00',
    storage: '5.1GB',
    lastRefresh: '2024-01-15 00:00'
  },
  {
    id: 3,
    name: '热门商品排行',
    description: '实时热销商品排行',
    type: '查询缓存',
    sourceTable: 'dwd_order_wide',
    query: 'SELECT product_id, product_name, SUM(quantity) as sold_count FROM dwd_order_wide WHERE date >= TODAY() GROUP BY product_id, product_name ORDER BY sold_count DESC LIMIT 100',
    enabled: true,
    speedup: 25.0,
    schedule: '实时',
    nextRun: '-',
    storage: '128MB',
    lastRefresh: '2024-01-15 10:28'
  },
  {
    id: 4,
    name: '区域销售分析',
    description: '按区域统计销售',
    type: '物化视图',
    sourceTable: 'dwd_order_wide',
    query: 'SELECT region, city, SUM(amount) as total_amount FROM dwd_order_wide GROUP BY region, city',
    enabled: false,
    speedup: 6.8,
    schedule: '每天',
    nextRun: '-',
    storage: '890MB',
    lastRefresh: '2024-01-10 00:00'
  }
])

const columns = [
  { title: '任务名称', slotName: 'name', width: 240 },
  { title: '类型', slotName: 'type', width: 100 },
  { title: '启用', slotName: 'enabled', width: 80 },
  { title: '加速比', slotName: 'speedup', width: 140 },
  { title: '刷新策略', slotName: 'schedule', width: 120 },
  { title: '存储', slotName: 'storage', width: 80 },
  { title: '操作', slotName: 'actions', width: 140 }
]

const enabledCount = computed(() => accelerations.value.filter(a => a.enabled).length)
const avgSpeedup = computed(() => {
  const enabled = accelerations.value.filter(a => a.enabled)
  if (enabled.length === 0) return 0
  return (enabled.reduce((sum, a) => sum + a.speedup, 0) / enabled.length).toFixed(1)
})
const totalStorage = computed(() => {
  return '8.4GB'
})

const filteredAccelerations = computed(() => {
  if (!searchText.value) return accelerations.value
  return accelerations.value.filter(a =>
    a.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
    a.description.toLowerCase().includes(searchText.value.toLowerCase())
  )
})

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    '物化视图': 'arcoblue',
    'OLAP Cube': 'purple',
    '查询缓存': 'green'
  }
  return colors[type] || 'gray'
}

function handleToggle(record: Acceleration) {
  Message.success(record.enabled ? '加速已启用' : '加速已禁用')
}

function refreshNow(record: Acceleration) {
  Message.info(`正在刷新: ${record.name}`)
}

function viewDetail(record: Acceleration) {
  Message.info(`查看详情: ${record.name}`)
}

function editAcceleration(record: Acceleration) {
  Message.info(`编辑: ${record.name}`)
}

function viewQuery(record: Acceleration) {
  currentSql.value = record.query
  showSqlModal.value = true
}

function deleteAcceleration(record: Acceleration) {
  Message.warning(`删除: ${record.name}`)
}

function handleCreate() {
  if (!createForm.value.name || !createForm.value.sourceTable || !createForm.value.query) {
    Message.error('请填写必填项')
    return
  }
  const typeMap: Record<string, string> = {
    'materialized_view': '物化视图',
    'cube': 'OLAP Cube',
    'cache': '查询缓存'
  }
  accelerations.value.push({
    id: Date.now(),
    name: createForm.value.name,
    description: createForm.value.description,
    type: typeMap[createForm.value.type] || '物化视图',
    sourceTable: createForm.value.sourceTable,
    query: createForm.value.query,
    enabled: false,
    speedup: 0,
    schedule: createForm.value.refreshPolicy === 'manual' ? '手动' : 
              createForm.value.refreshPolicy === 'realtime' ? '实时' : 
              createForm.value.schedule === 'hourly' ? '每小时' :
              createForm.value.schedule === 'weekly' ? '每周' : '每天',
    nextRun: '-',
    storage: '-',
    lastRefresh: '-'
  })
  Message.success('创建成功')
  showCreateModal.value = false
}
</script>

<style scoped>
.acceleration-page {
  padding: 0;
}

.overview-cards {
  margin-top: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1d2129;
}

.stat-label {
  font-size: 13px;
  color: #86909c;
}

.acceleration-list {
  margin-top: 16px;
}

.task-name {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.name-text {
  font-weight: 500;
}

.name-desc {
  font-size: 12px;
  color: #86909c;
}

.speedup-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.speedup-value {
  font-weight: 500;
  color: #165dff;
}

.schedule-info {
  font-size: 13px;
}

.next-run {
  font-size: 12px;
  color: #86909c;
}

.type-option {
  padding: 4px 0;
}

.type-title {
  font-weight: 500;
}

.type-desc {
  font-size: 12px;
  color: #86909c;
}

.sql-code {
  background: #f7f8fa;
  padding: 16px;
  border-radius: 4px;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
