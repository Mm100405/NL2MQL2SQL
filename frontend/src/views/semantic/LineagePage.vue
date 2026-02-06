<template>
  <div class="lineage-page">
    <a-card title="数据血缘">
      <template #extra>
        <a-space>
          <a-select v-model="filterType" placeholder="筛选类型" style="width: 120px" allow-clear>
            <a-option value="datasource">数据源</a-option>
            <a-option value="dataset">物理表</a-option>
            <a-option value="view">视图</a-option>
            <a-option value="metric">指标</a-option>
            <a-option value="dimension">维度</a-option>
          </a-select>
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索节点..."
            style="width: 200px"
            @search="highlightNode"
          />
          <a-button @click="resetView">
            <template #icon><icon-refresh /></template>
            重置视图
          </a-button>
          <a-button type="primary" @click="fetchLineage">
            <template #icon><icon-sync /></template>
            刷新数据
          </a-button>
        </a-space>
      </template>

      <div class="lineage-container">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-viewport="{ zoom: 0.8 }"
          :min-zoom="0.2"
          :max-zoom="2"
          fit-view-on-init
          class="lineage-flow"
        >
          <template #node-datasource="{ data }">
            <div class="lineage-node datasource-node" @click="onNodeClick(data)">
              <div class="node-icon"><icon-storage /></div>
              <div class="node-content">
                <div class="node-type">数据源</div>
                <div class="node-name">{{ data.label }}</div>
              </div>
            </div>
          </template>
          
          <template #node-dataset="{ data }">
            <div class="lineage-node dataset-node" @click="onNodeClick(data)">
              <div class="node-icon"><icon-layers /></div>
              <div class="node-content">
                <div class="node-type">物理表</div>
                <div class="node-name">{{ data.label }}</div>
                <div class="node-sub" v-if="data.physicalName">{{ data.physicalName }}</div>
              </div>
            </div>
          </template>
          
          <template #node-view="{ data }">
            <div class="lineage-node view-node" @click="onNodeClick(data)">
              <div class="node-icon"><icon-apps /></div>
              <div class="node-content">
                <div class="node-type">视图</div>
                <div class="node-name">{{ data.label }}</div>
                <div class="node-sub" v-if="data.viewType">{{ viewTypeLabel(data.viewType) }}</div>
              </div>
            </div>
          </template>
          
          <template #node-metric="{ data }">
            <div class="lineage-node metric-node" @click="onNodeClick(data)">
              <div class="node-icon"><icon-bar-chart /></div>
              <div class="node-content">
                <div class="node-type">指标</div>
                <div class="node-name">{{ data.label }}</div>
                <div class="node-sub" v-if="data.metricType">{{ metricTypeLabel(data.metricType) }}</div>
              </div>
            </div>
          </template>
          
          <template #node-dimension="{ data }">
            <div class="lineage-node dimension-node" @click="onNodeClick(data)">
              <div class="node-icon"><icon-filter /></div>
              <div class="node-content">
                <div class="node-type">维度</div>
                <div class="node-name">{{ data.label }}</div>
                <div class="node-sub" v-if="data.dimensionType">{{ dimensionTypeLabel(data.dimensionType) }}</div>
              </div>
            </div>
          </template>

          <Background />
          <Controls />
          <MiniMap pannable zoomable />
        </VueFlow>
      </div>

      <!-- 节点详情面板 -->
      <a-drawer
        v-model:visible="drawerVisible"
        :title="selectedNode?.label || '节点详情'"
        :width="400"
        placement="right"
      >
        <a-descriptions v-if="selectedNode" :column="1" bordered>
          <a-descriptions-item label="类型">
            <a-tag :color="getNodeColor(selectedNode.nodeType)">
              {{ getNodeTypeLabel(selectedNode.nodeType) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="名称">{{ selectedNode.label }}</a-descriptions-item>
          <a-descriptions-item label="ID">{{ selectedNode.id }}</a-descriptions-item>
          <a-descriptions-item v-if="selectedNode.physicalName" label="物理名称">
            {{ selectedNode.physicalName }}
          </a-descriptions-item>
          <a-descriptions-item v-if="selectedNode.viewType" label="视图类型">
            {{ viewTypeLabel(selectedNode.viewType) }}
          </a-descriptions-item>
          <a-descriptions-item v-if="selectedNode.metricType" label="指标类型">
            {{ metricTypeLabel(selectedNode.metricType) }}
          </a-descriptions-item>
          <a-descriptions-item v-if="selectedNode.dimensionType" label="维度类型">
            {{ dimensionTypeLabel(selectedNode.dimensionType) }}
          </a-descriptions-item>
        </a-descriptions>
        
        <a-divider>上游节点</a-divider>
        <a-list :data="upstreamNodes" size="small">
          <template #item="{ item }">
            <a-list-item>
              <a-tag :color="getNodeColor(item.type)">{{ item.name }}</a-tag>
            </a-list-item>
          </template>
          <template #empty>
            <a-empty description="无上游节点" />
          </template>
        </a-list>
        
        <a-divider>下游节点</a-divider>
        <a-list :data="downstreamNodes" size="small">
          <template #item="{ item }">
            <a-list-item>
              <a-tag :color="getNodeColor(item.type)">{{ item.name }}</a-tag>
            </a-list-item>
          </template>
          <template #empty>
            <a-empty description="无下游节点" />
          </template>
        </a-list>
      </a-drawer>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge } from '@vue-flow/core'
import { getFullLineageGraph } from '@/api/semantic'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const { fitView, setCenter } = useVueFlow()

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const filterType = ref<string>('')
const searchKeyword = ref('')
const drawerVisible = ref(false)
const selectedNode = ref<any>(null)
const rawData = ref<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })

// 上下游节点
const upstreamNodes = computed(() => {
  if (!selectedNode.value) return []
  const nodeId = selectedNode.value.id
  const upstream = rawData.value.edges
    .filter(e => e.target === nodeId)
    .map(e => {
      const node = rawData.value.nodes.find(n => n.id === e.source)
      return node ? { id: node.id, name: node.name, type: node.type } : null
    })
    .filter(Boolean)
  return upstream
})

const downstreamNodes = computed(() => {
  if (!selectedNode.value) return []
  const nodeId = selectedNode.value.id
  const downstream = rawData.value.edges
    .filter(e => e.source === nodeId)
    .map(e => {
      const node = rawData.value.nodes.find(n => n.id === e.target)
      return node ? { id: node.id, name: node.name, type: node.type } : null
    })
    .filter(Boolean)
  return downstream
})

onMounted(() => {
  fetchLineage()
})

async function fetchLineage() {
  try {
    const data = await getFullLineageGraph()
    rawData.value = data
    processGraphData(data)
  } catch (error) {
    console.error('Failed to fetch lineage:', error)
    Message.error('获取血缘数据失败')
  }
}

function processGraphData(data: { nodes: any[]; edges: any[] }) {
  // 按层级组织节点位置
  const levelMap: Record<string, number> = {
    datasource: 0,
    dataset: 1,
    view: 2,
    metric: 3,
    dimension: 3
  }
  
  // 统计每层节点数量
  const levelCounts: { [key: number]: number } = {}
  const levelCurrentIndex: { [key: number]: number } = {}
  
  data.nodes.forEach(n => {
    const level = levelMap[n.type] || 0
    levelCounts[level] = (levelCounts[level] || 0) + 1
  })
  
  // 初始化当前索引
  Object.keys(levelCounts).forEach(l => {
    levelCurrentIndex[Number(l)] = 0
  })
  
  // 转换节点
  const flowNodes: Node[] = data.nodes
    .filter(n => !filterType.value || n.type === filterType.value)
    .map(n => {
      const level = levelMap[n.type] ?? 0
      const count = levelCounts[level] ?? 1
      if (levelCurrentIndex[level] === undefined) {
        levelCurrentIndex[level] = 0
      }
      const index = levelCurrentIndex[level]
      levelCurrentIndex[level] += 1
      
      // 计算位置：横向按层级，纵向平均分布
      const xSpacing = 300
      const ySpacing = 120
      const xOffset = level * xSpacing
      const yOffset = index * ySpacing - ((count - 1) * ySpacing / 2)
      
      return {
        id: n.id,
        type: n.type,
        position: { x: xOffset, y: yOffset },
        data: {
          id: n.id,
          label: n.name,
          nodeType: n.type,
          physicalName: n.physical_name,
          viewType: n.view_type,
          metricType: n.metric_type,
          dimensionType: n.dimension_type
        }
      }
    })
  
  // 转换边
  const nodeIds = new Set(flowNodes.map(n => n.id))
  const flowEdges: Edge[] = data.edges
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      animated: e.type === 'derives' || e.type === 'uses',
      style: { stroke: getEdgeColor(e.type) },
      label: getEdgeLabel(e.type),
      labelStyle: { fontSize: 10, fill: '#666' }
    }))
  
  nodes.value = flowNodes
  edges.value = flowEdges
}

function getEdgeColor(type: string): string {
  const colors: Record<string, string> = {
    contains: '#91d5ff',
    source: '#87e8de',
    derives: '#ffd591',
    defines: '#d3adf7',
    uses: '#ffadd2'
  }
  return colors[type] || '#aaa'
}

function getEdgeLabel(type: string): string {
  const labels: Record<string, string> = {
    contains: '包含',
    source: '来源',
    derives: '派生',
    defines: '定义',
    uses: '引用'
  }
  return labels[type] || ''
}

function getNodeColor(type: string): string {
  const colors: Record<string, string> = {
    datasource: 'arcoblue',
    dataset: 'green',
    view: 'cyan',
    metric: 'orange',
    dimension: 'purple'
  }
  return colors[type] || 'gray'
}

function getNodeTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    datasource: '数据源',
    dataset: '物理表',
    view: '视图',
    metric: '指标',
    dimension: '维度'
  }
  return labels[type] || type
}

function viewTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    single_table: '单表',
    joined: '多表聚合',
    sql: '自定义SQL'
  }
  return labels[type] || type
}

function metricTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    basic: '基础指标',
    derived: '派生指标',
    composite: '复合指标'
  }
  return labels[type] || type
}

function dimensionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    categorical: '分类维度',
    time: '时间维度',
    hierarchical: '层级维度'
  }
  return labels[type] || type
}

function onNodeClick(data: any) {
  selectedNode.value = data
  drawerVisible.value = true
}

function highlightNode() {
  if (!searchKeyword.value) return
  
  const keyword = searchKeyword.value.toLowerCase()
  const found = nodes.value.find(n => 
    n.data?.label?.toLowerCase().includes(keyword)
  )
  
  if (found) {
    setCenter(found.position.x, found.position.y, { zoom: 1.2, duration: 500 })
    // 高亮节点
    nodes.value = nodes.value.map(n => ({
      ...n,
      class: n.id === found.id ? 'highlighted' : ''
    }))
    Message.success(`找到节点：${found.data?.label}`)
  } else {
    Message.warning('未找到匹配的节点')
  }
}

function resetView() {
  filterType.value = ''
  searchKeyword.value = ''
  processGraphData(rawData.value)
  setTimeout(() => fitView({ duration: 500 }), 100)
}
</script>

<style scoped>
.lineage-page {
  height: 100%;
}

.lineage-container {
  height: 600px;
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
}

.lineage-flow {
  width: 100%;
  height: 100%;
  background: #fafafa;
}

.lineage-node {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  min-width: 140px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.lineage-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.node-icon {
  font-size: 24px;
  margin-right: 10px;
}

.node-content {
  flex: 1;
}

.node-type {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 2px;
}

.node-name {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
}

.node-sub {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 2px;
}

.datasource-node {
  background: linear-gradient(135deg, #1890ff, #096dd9);
}

.datasource-node .node-icon {
  color: rgba(255, 255, 255, 0.9);
}

.dataset-node {
  background: linear-gradient(135deg, #52c41a, #389e0d);
}

.dataset-node .node-icon {
  color: rgba(255, 255, 255, 0.9);
}

.view-node {
  background: linear-gradient(135deg, #13c2c2, #08979c);
}

.view-node .node-icon {
  color: rgba(255, 255, 255, 0.9);
}

.metric-node {
  background: linear-gradient(135deg, #fa8c16, #d46b08);
}

.metric-node .node-icon {
  color: rgba(255, 255, 255, 0.9);
}

.dimension-node {
  background: linear-gradient(135deg, #722ed1, #531dab);
}

.dimension-node .node-icon {
  color: rgba(255, 255, 255, 0.9);
}

:deep(.highlighted) {
  outline: 3px solid #f00;
  outline-offset: 2px;
}

:deep(.vue-flow__minimap) {
  background: #fff;
  border: 1px solid var(--color-border-2);
}
</style>
