<template>
  <div class="integration-page">
    <a-page-header title="数据集成" subtitle="配置和管理数据源的抽取与同步任务">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建集成任务
        </a-button>
      </template>
    </a-page-header>

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stat-cards">
      <a-col :span="6">
        <a-card>
          <a-statistic title="总任务数" :value="tasks.length">
            <template #prefix><icon-sync /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="运行中" :value="runningCount" :value-style="{ color: '#00b42a' }">
            <template #prefix><icon-play-circle /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="已暂停" :value="pausedCount" :value-style="{ color: '#ff7d00' }">
            <template #prefix><icon-pause-circle /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="失败" :value="failedCount" :value-style="{ color: '#f53f3f' }">
            <template #prefix><icon-close-circle /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 任务列表 -->
    <a-card class="task-list" title="集成任务">
      <template #extra>
        <a-space>
          <a-input-search v-model="searchText" placeholder="搜索任务" style="width: 200px" />
          <a-select v-model="statusFilter" placeholder="状态筛选" style="width: 120px" allow-clear>
            <a-option value="running">运行中</a-option>
            <a-option value="paused">已暂停</a-option>
            <a-option value="failed">失败</a-option>
          </a-select>
        </a-space>
      </template>

      <a-table :columns="columns" :data="filteredTasks" :pagination="{ pageSize: 10 }">
        <template #name="{ record }">
          <div class="task-name">
            <a-avatar :size="32" :style="{ backgroundColor: getSourceColor(record.sourceType) }">
              {{ record.sourceType.charAt(0).toUpperCase() }}
            </a-avatar>
            <div class="task-info">
              <div class="task-title">{{ record.name }}</div>
              <div class="task-desc">{{ record.sourceType }} -> {{ record.targetType }}</div>
            </div>
          </div>
        </template>
        <template #status="{ record }">
          <a-tag :color="getStatusColor(record.status)">
            <template #icon>
              <icon-loading v-if="record.status === 'running'" spin />
              <icon-pause v-else-if="record.status === 'paused'" />
              <icon-close v-else-if="record.status === 'failed'" />
              <icon-check v-else />
            </template>
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>
        <template #schedule="{ record }">
          <span>{{ record.schedule }}</span>
        </template>
        <template #lastRun="{ record }">
          <div class="last-run">
            <div>{{ record.lastRunTime }}</div>
            <div class="run-duration">耗时: {{ record.lastRunDuration }}</div>
          </div>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-tooltip :content="record.status === 'running' ? '暂停' : '启动'">
              <a-button type="text" size="small" @click="toggleTask(record)">
                <icon-pause v-if="record.status === 'running'" />
                <icon-play-arrow v-else />
              </a-button>
            </a-tooltip>
            <a-tooltip content="立即执行">
              <a-button type="text" size="small" @click="runNow(record)">
                <icon-thunderbolt />
              </a-button>
            </a-tooltip>
            <a-tooltip content="查看日志">
              <a-button type="text" size="small" @click="viewLogs(record)">
                <icon-file />
              </a-button>
            </a-tooltip>
            <a-dropdown>
              <a-button type="text" size="small"><icon-more /></a-button>
              <template #content>
                <a-doption @click="editTask(record)">编辑</a-doption>
                <a-doption @click="copyTask(record)">复制</a-doption>
                <a-doption class="danger" @click="deleteTask(record)">删除</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新建任务弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建集成任务"
      width="640px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="任务名称" required>
          <a-input v-model="createForm.name" placeholder="请输入任务名称" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="源数据类型" required>
              <a-select v-model="createForm.sourceType" placeholder="请选择">
                <a-option value="mysql">MySQL</a-option>
                <a-option value="postgresql">PostgreSQL</a-option>
                <a-option value="oracle">Oracle</a-option>
                <a-option value="sqlserver">SQL Server</a-option>
                <a-option value="mongodb">MongoDB</a-option>
                <a-option value="kafka">Kafka</a-option>
                <a-option value="api">REST API</a-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标数据类型" required>
              <a-select v-model="createForm.targetType" placeholder="请选择">
                <a-option value="clickhouse">ClickHouse</a-option>
                <a-option value="postgresql">PostgreSQL</a-option>
                <a-option value="mysql">MySQL</a-option>
                <a-option value="hive">Hive</a-option>
                <a-option value="doris">Doris</a-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="调度策略" required>
          <a-radio-group v-model="createForm.scheduleType">
            <a-radio value="cron">Cron表达式</a-radio>
            <a-radio value="interval">固定间隔</a-radio>
            <a-radio value="manual">手动触发</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="createForm.scheduleType === 'cron'" label="Cron表达式">
          <a-input v-model="createForm.cronExpr" placeholder="0 0 * * *" />
        </a-form-item>
        <a-form-item v-if="createForm.scheduleType === 'interval'" label="执行间隔">
          <a-input-number v-model="createForm.interval" :min="1" style="width: 100%">
            <template #suffix>分钟</template>
          </a-input-number>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入任务描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Task {
  id: number
  name: string
  sourceType: string
  targetType: string
  status: 'running' | 'paused' | 'failed' | 'success'
  schedule: string
  lastRunTime: string
  lastRunDuration: string
}

const searchText = ref('')
const statusFilter = ref('')
const showCreateModal = ref(false)

const createForm = ref({
  name: '',
  sourceType: '',
  targetType: '',
  scheduleType: 'cron',
  cronExpr: '0 0 * * *',
  interval: 60,
  description: ''
})

const tasks = ref<Task[]>([
  {
    id: 1,
    name: '订单数据同步',
    sourceType: 'mysql',
    targetType: 'clickhouse',
    status: 'running',
    schedule: '每小时',
    lastRunTime: '2024-01-15 10:00',
    lastRunDuration: '2分30秒'
  },
  {
    id: 2,
    name: '用户行为日志采集',
    sourceType: 'kafka',
    targetType: 'clickhouse',
    status: 'running',
    schedule: '实时',
    lastRunTime: '2024-01-15 10:30',
    lastRunDuration: '-'
  },
  {
    id: 3,
    name: '商品主数据同步',
    sourceType: 'postgresql',
    targetType: 'mysql',
    status: 'paused',
    schedule: '每天凌晨',
    lastRunTime: '2024-01-14 00:00',
    lastRunDuration: '15分钟'
  },
  {
    id: 4,
    name: '财务数据导入',
    sourceType: 'api',
    targetType: 'postgresql',
    status: 'failed',
    schedule: '每周一',
    lastRunTime: '2024-01-08 08:00',
    lastRunDuration: '失败'
  }
])

const columns = [
  { title: '任务名称', slotName: 'name', width: 280 },
  { title: '状态', slotName: 'status', width: 100 },
  { title: '调度', slotName: 'schedule', width: 100 },
  { title: '上次执行', slotName: 'lastRun', width: 160 },
  { title: '操作', slotName: 'actions', width: 180, align: 'center' }
]

const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
const pausedCount = computed(() => tasks.value.filter(t => t.status === 'paused').length)
const failedCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)

const filteredTasks = computed(() => {
  let result = tasks.value
  if (searchText.value) {
    result = result.filter(t => t.name.toLowerCase().includes(searchText.value.toLowerCase()))
  }
  if (statusFilter.value) {
    result = result.filter(t => t.status === statusFilter.value)
  }
  return result
})

function getSourceColor(type: string) {
  const colors: Record<string, string> = {
    mysql: '#4479A1',
    postgresql: '#336791',
    oracle: '#F80000',
    kafka: '#231F20',
    api: '#165DFF',
    clickhouse: '#FFCC00'
  }
  return colors[type] || '#86909c'
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    running: 'green',
    paused: 'orange',
    failed: 'red',
    success: 'blue'
  }
  return colors[status] || 'gray'
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    running: '运行中',
    paused: '已暂停',
    failed: '失败',
    success: '成功'
  }
  return texts[status] || status
}

function toggleTask(task: Task) {
  if (task.status === 'running') {
    task.status = 'paused'
    Message.success('任务已暂停')
  } else {
    task.status = 'running'
    Message.success('任务已启动')
  }
}

function runNow(task: Task) {
  Message.info(`立即执行: ${task.name}`)
}

function viewLogs(task: Task) {
  Message.info(`查看日志: ${task.name}`)
}

function editTask(task: Task) {
  Message.info(`编辑任务: ${task.name}`)
}

function copyTask(task: Task) {
  Message.info(`复制任务: ${task.name}`)
}

function deleteTask(task: Task) {
  Message.warning(`删除任务: ${task.name}`)
}

function handleCreate() {
  if (!createForm.value.name || !createForm.value.sourceType || !createForm.value.targetType) {
    Message.error('请填写必填项')
    return
  }
  tasks.value.push({
    id: Date.now(),
    name: createForm.value.name,
    sourceType: createForm.value.sourceType,
    targetType: createForm.value.targetType,
    status: 'paused',
    schedule: createForm.value.scheduleType === 'manual' ? '手动' : createForm.value.cronExpr,
    lastRunTime: '-',
    lastRunDuration: '-'
  })
  Message.success('创建成功')
  showCreateModal.value = false
}
</script>

<style scoped>
.integration-page {
  padding: 0;
}

.stat-cards {
  margin-top: 16px;
}

.task-list {
  margin-top: 16px;
}

.task-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-info {
  display: flex;
  flex-direction: column;
}

.task-title {
  font-weight: 500;
}

.task-desc {
  font-size: 12px;
  color: #86909c;
}

.last-run {
  font-size: 13px;
}

.run-duration {
  font-size: 12px;
  color: #86909c;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
