<template>
  <div class="operator-lineage-page">
    <a-page-header title="算子级血缘" subtitle="追踪数据处理流程中每个算子的数据血缘关系">
      <template #extra>
        <a-space>
          <a-input-search v-model="searchText" placeholder="搜索表/字段/算子" style="width: 240px" @search="handleSearch" />
          <a-button @click="refreshLineage">
            <template #icon><icon-sync /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showAnalyzeModal = true">
            <template #icon><icon-plus /></template>
            分析SQL
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <div class="lineage-content">
      <!-- 左侧面板 -->
      <div class="left-panel">
        <!-- 数据对象树 -->
        <a-card class="object-tree" title="数据对象">
          <template #extra>
            <a-radio-group v-model="objectType" size="small" type="button">
              <a-radio value="table">表</a-radio>
              <a-radio value="field">字段</a-radio>
            </a-radio-group>
          </template>
          <a-tree
            :data="objectTree"
            :default-expand-all="false"
            :selected-keys="selectedObject"
            @select="handleObjectSelect"
          >
            <template #title="node">
              <div class="tree-node-title">
                <component :is="getNodeIcon(node.type)" :size="14" />
                <span>{{ node.title }}</span>
              </div>
            </template>
          </a-tree>
        </a-card>

        <!-- 算子类型筛选 -->
        <a-card class="operator-filter" title="算子类型">
          <a-checkbox-group v-model="selectedOperators" direction="vertical">
            <a-checkbox v-for="op in operatorTypes" :key="op.value" :value="op.value">
              <div class="operator-item">
                <span class="operator-icon" :style="{ color: op.color }">{{ op.icon }}</span>
                <span>{{ op.label }}</span>
              </div>
            </a-checkbox>
          </a-checkbox-group>
        </a-card>
      </div>

      <!-- 中间血缘图 -->
      <a-card class="lineage-graph">
        <template #title>
          <a-space>
            <span>血缘图谱</span>
            <a-tag v-if="currentTarget" color="arcoblue">{{ currentTarget }}</a-tag>
          </a-space>
        </template>
        <template #extra>
          <a-space>
            <a-radio-group v-model="viewDirection" size="small" type="button">
              <a-radio value="upstream">上游</a-radio>
              <a-radio value="both">双向</a-radio>
              <a-radio value="downstream">下游</a-radio>
            </a-radio-group>
            <a-slider v-model="zoomLevel" :min="50" :max="150" :step="10" style="width: 100px" />
            <a-button type="text" size="small" @click="fitView"><icon-fullscreen /></a-button>
          </a-space>
        </template>

        <div class="graph-container" ref="graphContainer">
          <!-- 血缘图可视化区域 -->
          <div class="lineage-diagram" :style="{ transform: `scale(${zoomLevel / 100})` }">
            <!-- 源表节点 -->
            <div class="lineage-column source-column">
              <div class="column-title">源数据</div>
              <div
                v-for="node in sourceNodes"
                :key="node.id"
                class="lineage-node source-node"
                :class="{ active: isNodeActive(node.id) }"
                @click="selectNode(node)"
              >
                <div class="node-header">
                  <icon-storage />
                  <span>{{ node.name }}</span>
                </div>
                <div class="node-fields">
                  <div v-for="field in node.fields" :key="field" class="field-item">
                    {{ field }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 算子节点 -->
            <div class="lineage-column operator-column">
              <div class="column-title">处理算子</div>
              <div
                v-for="op in operatorNodes"
                :key="op.id"
                class="lineage-node operator-node"
                :class="{ active: isNodeActive(op.id) }"
                :style="{ borderColor: getOperatorColor(op.type || '') }"
                @click="selectNode(op)"
              >
                <div class="node-header" :style="{ background: getOperatorColor(op.type || '') + '20' }">
                  <span class="operator-type">{{ op.type }}</span>
                </div>
                <div class="node-content">
                  <div class="operator-detail">{{ op.detail }}</div>
                  <div class="operator-meta">
                    <span><icon-clock-circle /> {{ op.executionTime }}</span>
                    <span><icon-file /> {{ op.rowCount }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 目标表节点 -->
            <div class="lineage-column target-column">
              <div class="column-title">目标数据</div>
              <div
                v-for="node in targetNodes"
                :key="node.id"
                class="lineage-node target-node"
                :class="{ active: isNodeActive(node.id) }"
                @click="selectNode(node)"
              >
                <div class="node-header">
                  <icon-storage />
                  <span>{{ node.name }}</span>
                </div>
                <div class="node-fields">
                  <div v-for="field in node.fields" :key="field" class="field-item">
                    {{ field }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 连接线 (SVG) -->
            <svg class="connection-lines" ref="svgRef">
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#c9cdd4" />
                </marker>
              </defs>
              <path
                v-for="(line, index) in connectionLines"
                :key="index"
                :d="line.path"
                :stroke="line.color"
                stroke-width="2"
                fill="none"
                marker-end="url(#arrowhead)"
                class="connection-line"
                :class="{ highlighted: line.highlighted }"
              />
            </svg>
          </div>
        </div>
      </a-card>

      <!-- 右侧详情面板 -->
      <div class="right-panel">
        <a-card class="detail-panel" title="节点详情">
          <template v-if="selectedNode">
            <a-descriptions :column="1" size="small" bordered>
              <a-descriptions-item label="名称">{{ selectedNode.name }}</a-descriptions-item>
              <a-descriptions-item label="类型">
                <a-tag :color="getNodeTypeColor(selectedNode.nodeType)">{{ selectedNode.nodeType }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item v-if="selectedNode.type" label="算子类型">{{ selectedNode.type }}</a-descriptions-item>
              <a-descriptions-item v-if="selectedNode.detail" label="详情">
                <pre class="detail-code">{{ selectedNode.detail }}</pre>
              </a-descriptions-item>
              <a-descriptions-item v-if="selectedNode.fields" label="字段">
                <div class="field-tags">
                  <a-tag v-for="f in selectedNode.fields" :key="f" size="small">{{ f }}</a-tag>
                </div>
              </a-descriptions-item>
            </a-descriptions>

            <a-divider>关联信息</a-divider>
            <div class="relation-info">
              <div class="relation-section">
                <div class="relation-title">上游依赖</div>
                <div class="relation-list">
                  <a-tag v-for="up in selectedNode.upstream || []" :key="up" size="small" color="blue">{{ up }}</a-tag>
                  <span v-if="!selectedNode.upstream?.length" class="empty-text">无上游</span>
                </div>
              </div>
              <div class="relation-section">
                <div class="relation-title">下游影响</div>
                <div class="relation-list">
                  <a-tag v-for="down in selectedNode.downstream || []" :key="down" size="small" color="green">{{ down }}</a-tag>
                  <span v-if="!selectedNode.downstream?.length" class="empty-text">无下游</span>
                </div>
              </div>
            </div>
          </template>
          <a-empty v-else description="选择节点查看详情" />
        </a-card>

        <!-- 影响分析 -->
        <a-card class="impact-analysis" title="影响分析">
          <template #extra>
            <a-button type="text" size="small" @click="runImpactAnalysis">
              <icon-experiment />
            </a-button>
          </template>
          <a-statistic title="影响范围" :value="impactStats.affectedTables" class="stat-item">
            <template #suffix>个表</template>
          </a-statistic>
          <a-statistic title="影响字段" :value="impactStats.affectedFields" class="stat-item">
            <template #suffix>个字段</template>
          </a-statistic>
          <a-statistic title="下游任务" :value="impactStats.affectedJobs" class="stat-item">
            <template #suffix>个任务</template>
          </a-statistic>
        </a-card>
      </div>
    </div>

    <!-- SQL分析弹窗 -->
    <a-modal
      v-model:visible="showAnalyzeModal"
      title="SQL血缘分析"
      width="720px"
      @ok="handleAnalyze"
    >
      <a-form :model="analyzeForm" layout="vertical">
        <a-form-item label="SQL语句" required>
          <a-textarea
            v-model="analyzeForm.sql"
            placeholder="输入SQL语句进行血缘分析..."
            :auto-size="{ minRows: 8, maxRows: 16 }"
          />
        </a-form-item>
        <a-form-item label="分析深度">
          <a-radio-group v-model="analyzeForm.depth">
            <a-radio value="table">表级血缘</a-radio>
            <a-radio value="column">字段级血缘</a-radio>
            <a-radio value="operator">算子级血缘</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface LineageNode {
  id: string
  name: string
  nodeType: 'source' | 'operator' | 'target'
  type?: string
  detail?: string
  fields?: string[]
  executionTime?: string
  rowCount?: string
  upstream?: string[]
  downstream?: string[]
}

const searchText = ref('')
const objectType = ref('table')
const selectedObject = ref<string[]>([])
const selectedOperators = ref(['SELECT', 'JOIN', 'FILTER', 'GROUP', 'AGGREGATE'])
const viewDirection = ref('both')
const zoomLevel = ref(100)
const currentTarget = ref('dwd_order_wide')
const selectedNode = ref<LineageNode | null>(null)
const showAnalyzeModal = ref(false)

const analyzeForm = ref({
  sql: '',
  depth: 'operator'
})

const operatorTypes = [
  { value: 'SELECT', label: 'SELECT', icon: 'S', color: '#165dff' },
  { value: 'JOIN', label: 'JOIN', icon: 'J', color: '#722ed1' },
  { value: 'FILTER', label: 'FILTER/WHERE', icon: 'F', color: '#ff7d00' },
  { value: 'GROUP', label: 'GROUP BY', icon: 'G', color: '#00b42a' },
  { value: 'AGGREGATE', label: 'AGGREGATE', icon: 'A', color: '#f53f3f' },
  { value: 'UNION', label: 'UNION', icon: 'U', color: '#0fc6c2' }
]

const objectTree = ref([
  {
    key: 'ods',
    title: 'ODS层',
    type: 'folder',
    children: [
      { key: 'ods_orders', title: 'ods_orders', type: 'table' },
      { key: 'ods_order_items', title: 'ods_order_items', type: 'table' },
      { key: 'ods_users', title: 'ods_users', type: 'table' }
    ]
  },
  {
    key: 'dwd',
    title: 'DWD层',
    type: 'folder',
    children: [
      { key: 'dwd_order_wide', title: 'dwd_order_wide', type: 'table' },
      { key: 'dwd_user_behavior', title: 'dwd_user_behavior', type: 'table' }
    ]
  },
  {
    key: 'dws',
    title: 'DWS层',
    type: 'folder',
    children: [
      { key: 'dws_sales_daily', title: 'dws_sales_daily', type: 'table' }
    ]
  }
])

const sourceNodes = ref<LineageNode[]>([
  {
    id: 'ods_orders',
    name: 'ods_orders',
    nodeType: 'source',
    fields: ['order_id', 'user_id', 'amount', 'status', 'create_time'],
    upstream: [],
    downstream: ['JOIN_1', 'FILTER_1']
  },
  {
    id: 'ods_order_items',
    name: 'ods_order_items',
    nodeType: 'source',
    fields: ['item_id', 'order_id', 'product_id', 'quantity', 'price'],
    upstream: [],
    downstream: ['JOIN_1']
  }
])

const operatorNodes = ref<LineageNode[]>([
  {
    id: 'JOIN_1',
    name: 'JOIN',
    nodeType: 'operator',
    type: 'JOIN',
    detail: 'ods_orders.order_id = ods_order_items.order_id',
    executionTime: '1.2s',
    rowCount: '15.6M',
    upstream: ['ods_orders', 'ods_order_items'],
    downstream: ['FILTER_1']
  },
  {
    id: 'FILTER_1',
    name: 'FILTER',
    nodeType: 'operator',
    type: 'FILTER',
    detail: "status = 'completed' AND create_time >= '2024-01-01'",
    executionTime: '0.8s',
    rowCount: '12.3M',
    upstream: ['JOIN_1'],
    downstream: ['GROUP_1']
  },
  {
    id: 'GROUP_1',
    name: 'GROUP BY',
    nodeType: 'operator',
    type: 'GROUP',
    detail: 'GROUP BY user_id, DATE(create_time)',
    executionTime: '2.5s',
    rowCount: '890K',
    upstream: ['FILTER_1'],
    downstream: ['AGG_1']
  },
  {
    id: 'AGG_1',
    name: 'AGGREGATE',
    nodeType: 'operator',
    type: 'AGGREGATE',
    detail: 'SUM(amount) as total_amount, COUNT(*) as order_count',
    executionTime: '0.5s',
    rowCount: '890K',
    upstream: ['GROUP_1'],
    downstream: ['dwd_order_wide']
  }
])

const targetNodes = ref<LineageNode[]>([
  {
    id: 'dwd_order_wide',
    name: 'dwd_order_wide',
    nodeType: 'target',
    fields: ['user_id', 'order_date', 'total_amount', 'order_count'],
    upstream: ['AGG_1'],
    downstream: []
  }
])

const connectionLines = computed(() => {
  return [
    { path: 'M 200,60 C 280,60 280,80 360,80', color: '#165dff', highlighted: false },
    { path: 'M 200,180 C 280,180 280,80 360,80', color: '#165dff', highlighted: false },
    { path: 'M 560,80 C 640,80 640,180 720,180', color: '#722ed1', highlighted: false },
    { path: 'M 560,180 C 640,180 640,280 720,280', color: '#ff7d00', highlighted: false },
    { path: 'M 560,280 C 640,280 640,380 720,380', color: '#00b42a', highlighted: false },
    { path: 'M 560,380 C 640,380 640,60 920,60', color: '#f53f3f', highlighted: false }
  ]
})

const impactStats = ref({
  affectedTables: 5,
  affectedFields: 23,
  affectedJobs: 8
})

const activeNodes = ref<string[]>([])

function getNodeIcon(type: string) {
  const icons: Record<string, string> = {
    folder: 'icon-folder',
    table: 'icon-storage',
    field: 'icon-code'
  }
  return icons[type] || 'icon-file'
}

function getOperatorColor(type: string) {
  const op = operatorTypes.find(o => o.value === type)
  return op?.color || '#86909c'
}

function getNodeTypeColor(nodeType: string) {
  const colors: Record<string, string> = {
    source: 'blue',
    operator: 'purple',
    target: 'green'
  }
  return colors[nodeType] || 'gray'
}

function isNodeActive(id: string) {
  return activeNodes.value.includes(id)
}

function handleObjectSelect(keys: string[]) {
  selectedObject.value = keys
  if (keys.length > 0) {
    currentTarget.value = keys[0] || ''
    Message.info(`选中: ${keys[0]}`)
  }
}

function selectNode(node: LineageNode) {
  selectedNode.value = node
  activeNodes.value = [node.id, ...(node.upstream || []), ...(node.downstream || [])]
}

function handleSearch() {
  Message.info(`搜索: ${searchText.value}`)
}

function refreshLineage() {
  Message.info('正在刷新血缘数据...')
}

function fitView() {
  zoomLevel.value = 100
}

function runImpactAnalysis() {
  Message.info('正在分析影响范围...')
}

function handleAnalyze() {
  if (!analyzeForm.value.sql) {
    Message.error('请输入SQL语句')
    return
  }
  Message.success('SQL血缘分析完成')
  showAnalyzeModal.value = false
}
</script>

<style scoped>
.operator-lineage-page {
  padding: 0;
}

.lineage-content {
  display: flex;
  gap: 16px;
  margin-top: 16px;
  height: calc(100vh - 200px);
}

.left-panel {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.object-tree {
  flex: 1;
  overflow: auto;
}

.tree-node-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.operator-filter {
  flex-shrink: 0;
}

.operator-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.operator-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: currentColor;
  color: white !important;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.lineage-graph {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.graph-container {
  flex: 1;
  overflow: auto;
  position: relative;
  background: #fafafa;
  border-radius: 4px;
}

.lineage-diagram {
  display: flex;
  gap: 120px;
  padding: 24px;
  min-width: 100%;
  min-height: 100%;
  position: relative;
  transform-origin: top left;
}

.lineage-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 200px;
}

.column-title {
  font-size: 12px;
  font-weight: 500;
  color: #86909c;
  text-transform: uppercase;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e6eb;
}

.lineage-node {
  background: white;
  border: 2px solid #e5e6eb;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.lineage-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.lineage-node.active {
  border-color: #165dff;
  box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.1);
}

.node-header {
  padding: 8px 12px;
  background: #f7f8fa;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.operator-node .node-header {
  justify-content: center;
}

.operator-type {
  font-size: 13px;
  font-weight: 600;
}

.node-fields {
  padding: 8px 12px;
}

.field-item {
  font-size: 12px;
  color: #4e5969;
  padding: 2px 0;
  font-family: monospace;
}

.node-content {
  padding: 8px 12px;
}

.operator-detail {
  font-size: 12px;
  color: #4e5969;
  font-family: monospace;
  word-break: break-all;
}

.operator-meta {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 11px;
  color: #86909c;
}

.operator-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.connection-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.connection-line {
  transition: stroke 0.2s, stroke-width 0.2s;
}

.connection-line.highlighted {
  stroke-width: 3;
}

.right-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-panel {
  flex: 1;
  overflow: auto;
}

.detail-code {
  background: #f7f8fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.relation-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.relation-section {
  padding: 8px;
  background: #f7f8fa;
  border-radius: 4px;
}

.relation-title {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}

.relation-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty-text {
  font-size: 12px;
  color: #c9cdd4;
}

.impact-analysis {
  flex-shrink: 0;
}

.stat-item {
  margin-bottom: 12px;
}
</style>
