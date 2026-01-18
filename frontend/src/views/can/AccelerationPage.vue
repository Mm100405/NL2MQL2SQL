<template>
  <div class="acceleration-page">
    <a-page-header title="指标加速" subtitle="配置指标预计算加速查询性能">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建加速配置
        </a-button>
      </template>
    </a-page-header>

    <!-- 加速统计 -->
    <a-row :gutter="16" class="stat-cards">
      <a-col :span="6">
        <a-card>
          <div class="stat-item">
            <div class="stat-icon" style="background: #e8f3ff">
              <icon-thunderbolt :size="24" style="color: #165dff" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ accelerations.length }}</div>
              <div class="stat-label">加速配置</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-item">
            <div class="stat-icon" style="background: #e8ffea">
              <icon-check-circle :size="24" style="color: #00b42a" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ enabledCount }}</div>
              <div class="stat-label">已启用</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-item">
            <div class="stat-icon" style="background: #fff7e8">
              <icon-fire :size="24" style="color: #ff7d00" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ avgHitRate }}%</div>
              <div class="stat-label">平均命中率</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <div class="stat-item">
            <div class="stat-icon" style="background: #f5e8ff">
              <icon-clock-circle :size="24" style="color: #722ed1" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ avgLatencyReduction }}%</div>
              <div class="stat-label">延迟降低</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 加速配置列表 -->
    <a-card class="acceleration-list" title="加速配置">
      <template #extra>
        <a-input-search v-model="searchText" placeholder="搜索" style="width: 200px" />
      </template>

      <a-table :columns="columns" :data="filteredAccelerations" :pagination="{ pageSize: 10 }">
        <template #metric="{ record }">
          <div class="metric-info">
            <div class="metric-name">{{ record.metricName }}</div>
            <div class="metric-code">{{ record.metricCode }}</div>
          </div>
        </template>
        <template #dimensions="{ record }">
          <div class="dimension-list">
            <a-tag v-for="dim in record.dimensions.slice(0, 2)" :key="dim" size="small">{{ dim }}</a-tag>
            <a-tag v-if="record.dimensions.length > 2" size="small">+{{ record.dimensions.length - 2 }}</a-tag>
          </div>
        </template>
        <template #granularity="{ record }">
          <a-tag :color="getGranularityColor(record.granularity)">{{ record.granularity }}</a-tag>
        </template>
        <template #enabled="{ record }">
          <a-switch v-model="record.enabled" size="small" @change="handleToggle(record)" />
        </template>
        <template #hitRate="{ record }">
          <div class="hit-rate">
            <span>{{ record.hitRate }}%</span>
            <a-progress
              :percent="record.hitRate"
              :show-text="false"
              size="small"
              :status="record.hitRate >= 80 ? 'success' : record.hitRate >= 50 ? 'warning' : 'danger'"
              style="width: 60px"
            />
          </div>
        </template>
        <template #latency="{ record }">
          <div class="latency-compare">
            <span class="old-latency">{{ record.originalLatency }}ms</span>
            <icon-arrow-right />
            <span class="new-latency">{{ record.acceleratedLatency }}ms</span>
          </div>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-tooltip content="刷新缓存">
              <a-button type="text" size="small" @click="refreshCache(record)">
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
                <a-doption @click="viewStats(record)">统计</a-doption>
                <a-doption class="danger" @click="deleteAcceleration(record)">删除</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新建加速配置弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建指标加速配置"
      width="640px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="选择指标" required>
          <a-select v-model="createForm.metricCode" placeholder="请选择要加速的指标">
            <a-option value="gmv">销售额 (gmv)</a-option>
            <a-option value="order_count">订单量 (order_count)</a-option>
            <a-option value="avg_order_value">客单价 (avg_order_value)</a-option>
            <a-option value="new_users">新增用户数 (new_users)</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="预聚合维度" required>
          <a-checkbox-group v-model="createForm.dimensions">
            <a-checkbox value="date">日期</a-checkbox>
            <a-checkbox value="channel">渠道</a-checkbox>
            <a-checkbox value="region">地区</a-checkbox>
            <a-checkbox value="category">类目</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
        <a-form-item label="时间粒度" required>
          <a-radio-group v-model="createForm.granularity">
            <a-radio value="分钟">分钟</a-radio>
            <a-radio value="小时">小时</a-radio>
            <a-radio value="天">天</a-radio>
            <a-radio value="周">周</a-radio>
            <a-radio value="月">月</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="刷新策略">
          <a-select v-model="createForm.refreshPolicy">
            <a-option value="realtime">实时</a-option>
            <a-option value="interval">定时间隔</a-option>
            <a-option value="schedule">定时调度</a-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="createForm.refreshPolicy === 'interval'" label="刷新间隔">
          <a-input-number v-model="createForm.refreshInterval" :min="1" style="width: 100%">
            <template #suffix>分钟</template>
          </a-input-number>
        </a-form-item>
        <a-form-item label="数据保留天数">
          <a-input-number v-model="createForm.retentionDays" :min="1" :max="365" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:visible="showDetailDrawer"
      :title="currentAcceleration?.metricName || '加速详情'"
      width="560px"
    >
      <template v-if="currentAcceleration">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="指标名称">{{ currentAcceleration.metricName }}</a-descriptions-item>
          <a-descriptions-item label="指标编码">{{ currentAcceleration.metricCode }}</a-descriptions-item>
          <a-descriptions-item label="预聚合维度">
            <a-space>
              <a-tag v-for="dim in currentAcceleration.dimensions" :key="dim">{{ dim }}</a-tag>
            </a-space>
          </a-descriptions-item>
          <a-descriptions-item label="时间粒度">{{ currentAcceleration.granularity }}</a-descriptions-item>
          <a-descriptions-item label="刷新策略">{{ currentAcceleration.refreshPolicy }}</a-descriptions-item>
          <a-descriptions-item label="上次刷新">{{ currentAcceleration.lastRefresh }}</a-descriptions-item>
          <a-descriptions-item label="缓存大小">{{ currentAcceleration.cacheSize }}</a-descriptions-item>
        </a-descriptions>

        <a-divider>性能统计</a-divider>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-statistic title="命中率" :value="currentAcceleration.hitRate" suffix="%" />
          </a-col>
          <a-col :span="8">
            <a-statistic title="原始延迟" :value="currentAcceleration.originalLatency" suffix="ms" />
          </a-col>
          <a-col :span="8">
            <a-statistic title="加速后延迟" :value="currentAcceleration.acceleratedLatency" suffix="ms" />
          </a-col>
        </a-row>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Acceleration {
  id: number
  metricName: string
  metricCode: string
  dimensions: string[]
  granularity: string
  refreshPolicy: string
  enabled: boolean
  hitRate: number
  originalLatency: number
  acceleratedLatency: number
  lastRefresh: string
  cacheSize: string
}

const searchText = ref('')
const showCreateModal = ref(false)
const showDetailDrawer = ref(false)
const currentAcceleration = ref<Acceleration | null>(null)

const createForm = ref({
  metricCode: '',
  dimensions: [] as string[],
  granularity: '天',
  refreshPolicy: 'interval',
  refreshInterval: 60,
  retentionDays: 90
})

const accelerations = ref<Acceleration[]>([
  {
    id: 1,
    metricName: '销售额',
    metricCode: 'gmv',
    dimensions: ['日期', '渠道', '地区'],
    granularity: '天',
    refreshPolicy: '每小时',
    enabled: true,
    hitRate: 92,
    originalLatency: 2500,
    acceleratedLatency: 120,
    lastRefresh: '2024-01-15 10:00',
    cacheSize: '1.2GB'
  },
  {
    id: 2,
    metricName: '订单量',
    metricCode: 'order_count',
    dimensions: ['日期', '渠道'],
    granularity: '小时',
    refreshPolicy: '实时',
    enabled: true,
    hitRate: 88,
    originalLatency: 1800,
    acceleratedLatency: 80,
    lastRefresh: '2024-01-15 10:28',
    cacheSize: '890MB'
  },
  {
    id: 3,
    metricName: '客单价',
    metricCode: 'avg_order_value',
    dimensions: ['日期'],
    granularity: '天',
    refreshPolicy: '每天',
    enabled: true,
    hitRate: 95,
    originalLatency: 3200,
    acceleratedLatency: 150,
    lastRefresh: '2024-01-15 00:00',
    cacheSize: '456MB'
  },
  {
    id: 4,
    metricName: '新增用户数',
    metricCode: 'new_users',
    dimensions: ['日期', '渠道', '来源'],
    granularity: '天',
    refreshPolicy: '每6小时',
    enabled: false,
    hitRate: 45,
    originalLatency: 2100,
    acceleratedLatency: 200,
    lastRefresh: '2024-01-14 18:00',
    cacheSize: '320MB'
  }
])

const columns = [
  { title: '指标', slotName: 'metric', width: 180 },
  { title: '预聚合维度', slotName: 'dimensions', width: 200 },
  { title: '粒度', slotName: 'granularity', width: 80 },
  { title: '启用', slotName: 'enabled', width: 70 },
  { title: '命中率', slotName: 'hitRate', width: 140 },
  { title: '延迟对比', slotName: 'latency', width: 160 },
  { title: '操作', slotName: 'actions', width: 120 }
]

const enabledCount = computed(() => accelerations.value.filter(a => a.enabled).length)
const avgHitRate = computed(() => {
  const enabled = accelerations.value.filter(a => a.enabled)
  if (enabled.length === 0) return 0
  return Math.round(enabled.reduce((sum, a) => sum + a.hitRate, 0) / enabled.length)
})
const avgLatencyReduction = computed(() => {
  const enabled = accelerations.value.filter(a => a.enabled)
  if (enabled.length === 0) return 0
  const reductions = enabled.map(a => ((a.originalLatency - a.acceleratedLatency) / a.originalLatency) * 100)
  return Math.round(reductions.reduce((sum, r) => sum + r, 0) / reductions.length)
})

const filteredAccelerations = computed(() => {
  if (!searchText.value) return accelerations.value
  return accelerations.value.filter(a =>
    a.metricName.includes(searchText.value) ||
    a.metricCode.includes(searchText.value)
  )
})

function getGranularityColor(granularity: string) {
  const colors: Record<string, string> = {
    '分钟': 'red',
    '小时': 'orange',
    '天': 'blue',
    '周': 'green',
    '月': 'purple'
  }
  return colors[granularity] || 'gray'
}

function handleToggle(record: Acceleration) {
  Message.success(record.enabled ? '加速已启用' : '加速已禁用')
}

function refreshCache(record: Acceleration) {
  Message.info(`正在刷新缓存: ${record.metricName}`)
}

function viewDetail(record: Acceleration) {
  currentAcceleration.value = record
  showDetailDrawer.value = true
}

function editAcceleration(record: Acceleration) {
  Message.info(`编辑加速配置: ${record.metricName}`)
}

function viewStats(record: Acceleration) {
  Message.info(`查看统计: ${record.metricName}`)
}

function deleteAcceleration(record: Acceleration) {
  Message.warning(`删除加速配置: ${record.metricName}`)
}

function handleCreate() {
  if (!createForm.value.metricCode || createForm.value.dimensions.length === 0) {
    Message.error('请填写必填项')
    return
  }
  const metricNames: Record<string, string> = {
    gmv: '销售额',
    order_count: '订单量',
    avg_order_value: '客单价',
    new_users: '新增用户数'
  }
  accelerations.value.push({
    id: Date.now(),
    metricName: metricNames[createForm.value.metricCode] || createForm.value.metricCode,
    metricCode: createForm.value.metricCode,
    dimensions: createForm.value.dimensions,
    granularity: createForm.value.granularity,
    refreshPolicy: createForm.value.refreshPolicy === 'realtime' ? '实时' :
                   createForm.value.refreshPolicy === 'interval' ? `每${createForm.value.refreshInterval}分钟` : '定时',
    enabled: false,
    hitRate: 0,
    originalLatency: 2000,
    acceleratedLatency: 0,
    lastRefresh: '-',
    cacheSize: '-'
  })
  Message.success('创建成功')
  showCreateModal.value = false
}
</script>

<style scoped>
.acceleration-page {
  padding: 0;
}

.stat-cards {
  margin-top: 16px;
}

.stat-item {
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

.stat-content {
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

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-name {
  font-weight: 500;
}

.metric-code {
  font-size: 12px;
  color: #86909c;
  font-family: monospace;
}

.dimension-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.hit-rate {
  display: flex;
  align-items: center;
  gap: 8px;
}

.latency-compare {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.old-latency {
  color: #86909c;
  text-decoration: line-through;
}

.new-latency {
  color: #00b42a;
  font-weight: 500;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
