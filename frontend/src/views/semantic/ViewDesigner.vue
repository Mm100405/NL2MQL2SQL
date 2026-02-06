<template>
  <div class="view-designer">
    <!-- 顶部工具栏 -->
    <div class="designer-header">
      <a-space>
        <a-button @click="goBack">
          <template #icon><icon-left /></template>
          返回列表
        </a-button>
        <a-divider direction="vertical" />
        <span class="view-name">{{ viewName || '新建视图' }}</span>
      </a-space>
      <a-space>
        <a-radio-group v-model="viewType" type="button" size="small" @change="handleViewTypeChange">
          <a-radio value="joined">可视化设计</a-radio>
          <a-radio value="sql">SQL编辑</a-radio>
        </a-radio-group>
        <a-button v-if="viewType === 'sql'" size="small" @click="parseSQLToCanvas">
          <template #icon><icon-swap /></template>
          转为可视化
        </a-button>
        <a-button v-if="viewType === 'joined'" size="small" @click="syncSQLFromCanvas">
          <template #icon><icon-sync /></template>
          同步SQL
        </a-button>
        <a-button type="primary" @click="handleSave" :loading="saving">
          <template #icon><icon-save /></template>
          保存
        </a-button>
      </a-space>
    </div>

    <!-- 主体区域 -->
    <div class="designer-body">
      <!-- 左侧：物理表列表 -->
      <div class="table-panel">
        <div class="panel-header">
          <span>物理表</span>
          <a-select v-model="selectedDatasource" placeholder="选择数据源" size="small" style="width: 120px">
            <a-option v-for="ds in datasources" :key="ds.id" :value="ds.id">{{ ds.name }}</a-option>
          </a-select>
        </div>
        <div class="table-search">
          <a-input 
            v-model="tableSearchKeyword" 
            placeholder="搜索表名..." 
            size="small"
            allow-clear
          >
            <template #prefix>
              <icon-search />
            </template>
          </a-input>
        </div>
        <div class="table-list">
          <div
            v-for="table in filteredTables"
            :key="table.id"
            class="table-item"
            draggable="true"
            @dragstart="onTableDragStart($event, table)"
          >
            <icon-storage />
            <span>{{ table.name }}</span>
          </div>
        </div>
      </div>

      <!-- 中间：画布区域 -->
      <div class="canvas-panel" v-show="viewType === 'joined'" @click="handleCanvasClick">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-viewport="{ zoom: 1, x: 0, y: 0 }"
          :min-zoom="0.1"
          :max-zoom="4"
          :nodes-draggable="true"
          :nodes-connectable="false"
          :elements-selectable="true"
          :connect-on-click="false"
          :pan-on-drag="true"
          :pan-on-scroll="true"
          :zoom-on-scroll="true"
          :fit-view-on-init="false"
          zoom-on-pinch
          zoom-on-double-click
          @drop="onCanvasDrop"
          @dragover.prevent
          @edge-click="onEdgeClick"
          @node-click="handleNodeClick"
          @pane-click="handlePaneClick"
          @nodes-change="onNodesChange"
          @edges-change="onEdgesChange"
        >
          <template #node-tableNode="nodeProps">
            <TableNode
              v-bind="nodeProps"
              @update-columns="handleUpdateNodeColumns"
              @column-click="handleColumnClick"
              @delete-node="handleDeleteNode"
            />
          </template>
          <Background pattern-color="#aaa" :gap="16" style="pointer-events: none !important;" />
          <Controls class="custom-controls" />
          <MiniMap class="custom-minimap" />
          
          <!-- 自定义整理布局按钮 -->
          <div class="layout-button">
            <a-tooltip content="整理布局" position="bottom">
              <button class="vue-flow__controls-button layout-btn-large" @click="handleAutoLayout">
                <icon-apps style="width: 27px; height: 27px;" />
              </button>
            </a-tooltip>
          </div>
        </VueFlow>
      </div>

      <!-- SQL编辑模式 -->
      <div class="sql-panel" v-show="viewType === 'sql'">
        <a-textarea
          v-model="customSql"
          placeholder="请输入自定义SQL查询语句..."
          :auto-size="{ minRows: 20 }"
        />
      </div>

      <!-- 右侧：属性面板 -->
      <div class="property-panel">
        <a-tabs v-model:active-key="activeTab">
          <a-tab-pane key="basic" title="基本信息">
            <a-form :model="formData" layout="vertical" size="small">
              <a-form-item label="视图名称" required>
                <a-input v-model="formData.name" placeholder="请输入视图名称" />
              </a-form-item>
              <a-form-item label="显示名称">
                <a-input v-model="formData.display_name" placeholder="请输入显示名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-textarea v-model="formData.description" placeholder="请输入描述" :auto-size="{ minRows: 3 }" />
              </a-form-item>
            </a-form>
          </a-tab-pane>
          <a-tab-pane key="joins" title="关联配置">
            <div v-if="selectedEdge" class="join-panel">
              <div class="join-header">
                <a-space>
                  <span>连接: {{ selectedEdge.source }} → {{ selectedEdge.target }}</span>
                  <a-tag :color="selectedEdge.data?.joinType === 'INNER' ? 'blue' : 
                           selectedEdge.data?.joinType === 'LEFT' ? 'arcoblue' : 
                           selectedEdge.data?.joinType === 'RIGHT' ? 'green' : 
                           selectedEdge.data?.joinType === 'FULL' ? 'orange' : 'gray'">
                    {{ selectedEdge.data?.joinType }} JOIN
                  </a-tag>
                </a-space>
                <a-button type="text" size="mini" status="danger" @click="handleDeleteEdge(selectedEdge.id)">
                  <template #icon><icon-delete /></template>
                  删除连接
                </a-button>
              </div>
              <JoinConfigPanel
                v-if="selectedEdgeConfig"
                :config="selectedEdgeConfig"
                :left-table-alias="selectedEdge.source"
                :right-table-alias="selectedEdge.target"
                :left-columns="getNodeColumns(selectedEdge.source)"
                :right-columns="getNodeColumns(selectedEdge.target)"
                @update="updateEdgeConfig"
              />
            </div>
            <a-empty v-else description="点击连线查看配置" />
          </a-tab-pane>
          <a-tab-pane key="columns" title="字段列表">
            <div class="column-list">
              <div v-for="col in viewColumns" :key="col.name" class="column-row">
                <a-checkbox v-model="col.selected">{{ col.name }}</a-checkbox>
                <span class="col-type">{{ col.type }}</span>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <!-- 字段选择弹窗 -->
    <ColumnSelectDialog
      v-model:visible="showColumnSelect"
      :columns="pendingTableColumns"
      :default-selected="pendingSelectedColumns"
      @confirm="handleColumnSelectConfirm"
    />

    <!-- JOIN类型选择弹窗 -->
    <a-modal
      v-model:visible="showJoinTypeDialog"
      title="选择连接类型"
      width="400px"
      @ok="handleJoinTypeConfirm"
      @cancel="handleJoinTypeCancel"
    >
      <a-form layout="vertical">
        <a-form-item label="连接方式">
          <a-radio-group v-model="selectedJoinType" direction="vertical">
            <a-radio value="INNER">INNER JOIN - 内连接（返回两表匹配的记录）</a-radio>
            <a-radio value="LEFT">LEFT JOIN - 左连接（返回左表全部+右表匹配）</a-radio>
            <a-radio value="RIGHT">RIGHT JOIN - 右连接（返回右表全部+左表匹配）</a-radio>
            <a-radio value="FULL">FULL JOIN - 全连接（返回两表全部记录）</a-radio>
            <a-radio value="CROSS">CROSS JOIN - 交叉连接（笛卡尔积）</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 底部：SQL预览 -->
    <div class="preview-panel">
      <a-collapse :default-active-key="['sql']">
        <a-collapse-item key="sql" header="SQL预览">
          <pre class="sql-preview">{{ generatedSql }}</pre>
        </a-collapse-item>
        <a-collapse-item key="data" header="数据预览">
          <a-button size="small" type="primary" @click="handlePreview" :loading="previewing" style="margin-bottom: 12px">
            执行预览
          </a-button>
          <a-table v-if="previewData.length" :columns="previewColumns" :data="previewData" :pagination="false" size="small" />
        </a-collapse-item>
      </a-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, markRaw, provide, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection } from '@vue-flow/core'
import { Message, Modal } from '@arco-design/web-vue'
import {
  IconDelete as IconDelete,
  IconApps
} from '@arco-design/web-vue/es/icon'
import TableNode from '@/components/semantic/TableNode.vue'
import ColumnSelectDialog from '@/components/semantic/ColumnSelectDialog.vue'
import JoinConfigPanel from '@/components/semantic/JoinConfigPanel.vue'
import type { JoinConfig } from '@/components/semantic/JoinConfigPanel.vue'
import { getDataSources, getDatasets } from '@/api/semantic'
import { getView, createView, updateView, previewView, generateViewSQL } from '@/api/views'
import type { Dataset, DataSource } from '@/api/types'
import { parseSQL } from '@/utils/sqlParser'

const route = useRoute()
const router = useRouter()
const viewId = computed(() => route.params.id as string)
const isEdit = computed(() => !!viewId.value && viewId.value !== 'new')

// 节点类型
const nodeTypes = {
  tableNode: markRaw(TableNode)
}

// 获取 Vue Flow 实例 - 在顶层调用
const { project, addEdge, onConnect: onConnectVueFlow, fitView } = useVueFlow()

// 状态
const saving = ref(false)
const previewing = ref(false)
const datasources = ref<DataSource[]>([])
const selectedDatasource = ref('')
const tables = ref<Dataset[]>([])
const tableSearchKeyword = ref('')
const viewType = ref<'joined' | 'sql'>('joined')
const customSql = ref('')
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const selectedEdge = ref<Edge | null>(null)
const viewName = ref('')
const activeTab = ref('basic')

// 字段选择弹窗
const showColumnSelect = ref(false)
const pendingTableColumns = ref<any[]>([])
const pendingSelectedColumns = ref<string[]>([])
const pendingTableData = ref<any>(null)

const formData = ref({
  name: '',
  display_name: '',
  description: ''
})

// 预览数据
const previewColumns = ref<any[]>([])
const previewData = ref<any[]>([])

// 视图字段
const viewColumns = ref<Array<{ name: string; type: string; selected: boolean; source_table?: string }>>([])

// 字段连接状态
const connectingColumn = ref<{ nodeId: string; columnName: string } | null>(null)
const showJoinTypeDialog = ref(false)
const pendingConnection = ref<{ sourceNode: string; sourceColumn: string; targetNode: string; targetColumn: string } | null>(null)
const selectedJoinType = ref<'INNER' | 'LEFT' | 'RIGHT' | 'FULL' | 'CROSS'>('INNER')

// 提供连接状态给子组件
provide('connectingColumn', connectingColumn)

// 过滤后的表列表
const filteredTables = computed(() => {
  if (!tableSearchKeyword.value.trim()) return tables.value
  const keyword = tableSearchKeyword.value.toLowerCase()
  return tables.value.filter(t => t.name.toLowerCase().includes(keyword))
})

// 监听nodes变化,支持字段选择更新
watch(() => nodes.value.map(n => n.data.selectedColumns), () => {
  updateViewColumns()
}, { deep: true })

// 选中边的配置
const selectedEdgeConfig = computed(() => {
  if (!selectedEdge.value?.data) return null
  return {
    joinType: selectedEdge.value.data.joinType || 'INNER',
    conditions: selectedEdge.value.data.conditions || [],
    filters: selectedEdge.value.data.filters || []
  }
})

// 生成的SQL
const generatedSql = computed(() => {
  if (viewType.value === 'sql') {
    return customSql.value || '-- 请输入自定义SQL'
  }
  
  if (nodes.value.length === 0) {
    return '-- 请拖拽表到画布'
  }
  
  // 构建SELECT子句
  const selectedCols = viewColumns.value.filter(c => c.selected)
  const selectClause = selectedCols.length > 0
    ? selectedCols.map(c => c.source_table ? `${c.source_table}.${c.name}` : c.name).join(', ')
    : '*'
  
  // 构建FROM子句
  if (nodes.value.length === 1) {
    const firstNode = nodes.value[0]
    return `SELECT ${selectClause}\nFROM ${firstNode.data.label} AS ${firstNode.data.alias}`
  }
  
  // 多表JOIN
  let fromClause = ''
  const firstNode = nodes.value[0]
  fromClause = `${firstNode.data.label} AS ${firstNode.data.alias}`
  
  // 收集所有WHERE条件
  const whereConditions: string[] = []
  
  for (const edge of edges.value) {
    const sourceNode = nodes.value.find(n => n.id === edge.source)
    const targetNode = nodes.value.find(n => n.id === edge.target)
    if (targetNode && sourceNode) {
      const joinType = edge.data?.joinType || 'INNER'
      const conditions = edge.data?.conditions || []
      const onClause = conditions.map((c: any) => `${c.left_column} ${c.operator || '='} ${c.right_column}`).join(' AND ') || '1=1'
      fromClause += `\n${joinType} JOIN ${targetNode.data.label} AS ${targetNode.data.alias} ON ${onClause}`
      
      // 收集筛选条件
      if (edge.data?.filters && edge.data.filters.length > 0) {
        for (const filter of edge.data.filters) {
          if (['IS NULL', 'IS NOT NULL'].includes(filter.operator)) {
            whereConditions.push(`${filter.column} ${filter.operator}`)
          } else {
            whereConditions.push(`${filter.column} ${filter.operator} '${filter.value}'`)
          }
        }
      }
    }
  }
  
  let sql = `SELECT ${selectClause}\nFROM ${fromClause}`
  
  // 添加WHERE子句
  if (whereConditions.length > 0) {
    sql += `\nWHERE ${whereConditions.join(' AND ')}`
  }
  
  return sql
})

// 加载数据源
async function loadDatasources() {
  try {
    datasources.value = await getDataSources()
    if (datasources.value.length > 0 && !selectedDatasource.value) {
      selectedDatasource.value = datasources.value[0].id
    }
  } catch (e) {
    console.error('Failed to load datasources:', e)
  }
}

// 加载表列表
async function loadTables() {
  if (!selectedDatasource.value) return
  try {
    // 直接通过参数过滤，避免加载所有数据
    tables.value = await getDatasets({ datasource_id: selectedDatasource.value })
  } catch (e) {
    console.error('Failed to load tables:', e)
  }
}

// 监听数据源变化
watch(selectedDatasource, () => {
  loadTables()
})

// 加载视图详情
async function loadView() {
  if (!isEdit.value) return
  try {
    const view = await getView(viewId.value)
    formData.value.name = view.name
    formData.value.display_name = view.display_name || ''
    formData.value.description = view.description || ''
    viewName.value = view.name
    selectedDatasource.value = view.datasource_id

    // 关键修复：设置数据源后，立即加载该数据源的表
    await loadTables()

    if (view.view_type === 'sql') {
      viewType.value = 'sql'
      customSql.value = view.custom_sql || ''
    } else if (view.view_type === 'joined' && view.join_config) {
      viewType.value = 'joined'
      // 恢复节点
      const joinConfig = view.join_config
      const nodePositions: Record<string, { x: number; y: number }> = {}
      for (const t of joinConfig.tables || []) {
        const dataset = tables.value.find(d => d.id === t.id)
        if (dataset) {
          const position = t.position || { x: 100, y: 100 }
          nodePositions[t.alias] = position
          nodes.value.push({
            id: t.alias,
            type: 'tableNode',
            position,
            data: {
              label: dataset.name,
              alias: t.alias,
              datasetId: dataset.id,
              columns: dataset.columns || [],
              selectedColumns: t.selectedColumns || dataset.columns?.map((c: any) => c.name) || [],
              leftHandles: 0,
              rightHandles: 0
            }
          })
        }
      }
      // 恢复边 (强制从左到右：源节点右侧连目标节点左侧)
      for (const j of joinConfig.joins || []) {
        // 强制连接方向：源节点使用右侧(source)，目标节点使用左侧(target)
        const sourceSide = 'right'
        const targetSide = 'left'
        
        // 更新节点数据中的连接点计数（使用响应式更新）
        const sourceNode = nodes.value.find(n => n.id === j.left_table)
        const targetNode = nodes.value.find(n => n.id === j.right_table)
        
        let sourceHandleIndex = 0
        let targetHandleIndex = 0
        
        if (sourceNode) {
          const sourceCurrentCount = sourceNode.data.rightHandles || 0
          sourceHandleIndex = sourceCurrentCount
          sourceNode.data = {
            ...sourceNode.data,
            rightHandles: sourceCurrentCount + 1
          }
        }
        
        if (targetNode) {
          const targetCurrentCount = targetNode.data.leftHandles || 0
          targetHandleIndex = targetCurrentCount
          targetNode.data = {
            ...targetNode.data,
            leftHandles: targetCurrentCount + 1
          }
        }
        
        // 生成连接点ID
        const sourceHandle = `${j.left_table}-${sourceSide}-${sourceHandleIndex}`
        const targetHandle = `${j.right_table}-${targetSide}-${targetHandleIndex}`
        
        edges.value.push({
          id: `${j.left_table}-${j.right_table}`,
          source: j.left_table,
          target: j.right_table,
          sourceHandle,
          targetHandle,
          data: {
            joinType: j.join_type,
            conditions: j.conditions,
            filters: j.filters || []
          },
          animated: true
        })
      }
    }

    // 恢复字段列表
    if (view.columns) {
      viewColumns.value = view.columns.map((c: any) => ({
        ...c,
        selected: true
      }))
    }
  } catch (e) {
    Message.error('加载视图失败')
  }
}

// 表拖拽开始
function onTableDragStart(event: DragEvent, table: Dataset) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('table-id', table.id)
    event.dataTransfer.effectAllowed = 'copy'
  }
}

// 画布放置
function onCanvasDrop(event: DragEvent) {
  const tableId = event.dataTransfer?.getData('table-id')
  if (!tableId) return

  const table = tables.value.find(t => t.id === tableId)
  if (!table) return

  // 检查是否已添加
  const exists = nodes.value.some(n => n.data.datasetId === tableId)
  if (exists) {
    Message.warning('该表已添加到画布')
    return
  }

  // 获取画布坐标
  const position = project({
    x: event.clientX,
    y: event.clientY
  })

  // 显示字段选择弹窗
  pendingTableColumns.value = table.columns || []
  pendingSelectedColumns.value = table.columns?.map(c => c.name) || []
  pendingTableData.value = {
    table,
    position
  }
  showColumnSelect.value = true
}

// 字段选择确认
function handleColumnSelectConfirm(selectedColumns: string[]) {
  if (!pendingTableData.value) return
  
  const { table, position } = pendingTableData.value
  const alias = `t${nodes.value.length}`

  // 添加节点
  nodes.value.push({
    id: alias,
    type: 'tableNode',
    position,
            data: {
              label: table.name,
              alias,
              datasetId: table.id,
              columns: table.columns || [],
              selectedColumns,
              leftHandles: 0,
              rightHandles: 0
            }
  })

  // 更新字段列表会自动通过watch触发
  
  // 清理临时数据
  pendingTableData.value = null
}

// 获取节点的字段选项
function getNodeColumns(nodeId: string) {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return []
  
  const selectedCols = node.data.selectedColumns || node.data.columns?.map((c: any) => c.name) || []
  return node.data.columns
    .filter((col: any) => selectedCols.includes(col.name))
    .map((col: any) => ({
      label: `${node.data.alias}.${col.name}`,
      value: `${node.data.alias}.${col.name}`
    }))
}

// 更新边配置
function updateEdgeConfig(config: JoinConfig) {
  if (selectedEdge.value) {
    selectedEdge.value.data = {
      ...selectedEdge.value.data,
      ...config
    }
  }
}

// 连接处理


// 节点变化处理
function onNodesChange(params: any[]) {
  // Vue Flow 会自动处理节点的拖动等变化
  console.log('Nodes changed:', params)
  
  // 检查是否有节点被删除
  const removeEvents = params.filter((p: any) => p.type === 'remove')
  if (removeEvents.length > 0) {
    console.log('Nodes removed:', removeEvents)
    updateViewColumns()
  }
}

// 边变化处理
function onEdgesChange(params: any[]) {
  // Vue Flow 会自动处理边的删除等变化
  console.log('Edges changed:', params)
}

// 边点击
function onEdgeClick({ edge }: { edge: Edge }) {
  console.log('Edge clicked:', edge)
  selectedEdge.value = edge
  activeTab.value = 'joins'
}

// 节点点击
function handleNodeClick({ node }: { node: Node }) {
  console.log('Node clicked:', node)
}

// 画布空白处点击
function handlePaneClick(event: MouseEvent) {
  console.log('Pane clicked:', event)
  // 取消选中边
  selectedEdge.value = null
}

// 画布容器点击 (用于调试)
function handleCanvasClick(event: MouseEvent) {
  console.log('Canvas container clicked:', event.target)
}

// 处理节点字段更新
function handleUpdateNodeColumns(payload: { alias: string; selectedColumns: string[] }) {
  const node = nodes.value.find(n => n.id === payload.alias)
  if (node) {
    node.data.selectedColumns = payload.selectedColumns
    updateViewColumns()
  }
}

// 处理字段点击（用于建立连线）
function handleColumnClick(payload: { nodeId: string; columnName: string; columnData: any }) {
  if (!connectingColumn.value) {
    // 第一次点击：记录源字段
    connectingColumn.value = {
      nodeId: payload.nodeId,
      columnName: payload.columnName
    }
    console.log('选中源字段:', payload)
  } else {
    // 第二次点击：检查是否是同一节点
    if (connectingColumn.value.nodeId === payload.nodeId) {
      Message.warning('请选择不同表的字段进行连接')
      connectingColumn.value = null
      return
    }
    
    // 记录待建立的连接
    pendingConnection.value = {
      sourceNode: connectingColumn.value.nodeId,
      sourceColumn: connectingColumn.value.columnName,
      targetNode: payload.nodeId,
      targetColumn: payload.columnName
    }
    
    console.log('准备建立连接:', pendingConnection.value)
    
    // 显示JOIN类型选择对话框
    showJoinTypeDialog.value = true
  }
}

// 确认JOIN类型并建立连接
function handleJoinTypeConfirm() {
  if (!pendingConnection.value) return
  
  const { sourceNode, sourceColumn, targetNode, targetColumn } = pendingConnection.value
  
  console.log('=== 开始创建连接 ===')
  console.log('连接信息:', pendingConnection.value)
  console.log('当前nodes:', nodes.value)
  console.log('当前edges:', edges.value)
  
  // 验证节点是否存在
  const sourceNodeObj = nodes.value.find(n => n.id === sourceNode)
  const targetNodeObj = nodes.value.find(n => n.id === targetNode)
  
  if (!sourceNodeObj || !targetNodeObj) {
    console.error('节点不存在!', { sourceNodeObj, targetNodeObj })
    Message.error('节点不存在，无法创建连接')
    return
  }
  

  
  // 检查是否已存在连接
  let existingEdge = edges.value.find(
    e => (e.source === sourceNode && e.target === targetNode) ||
         (e.source === targetNode && e.target === sourceNode)
  )
  
  if (existingEdge) {
    // 添加条件到现有连接
    if (!existingEdge.data) existingEdge.data = { joinType: selectedJoinType.value, conditions: [], filters: [] }
    if (!existingEdge.data.conditions) existingEdge.data.conditions = []
    existingEdge.data.conditions.push({
      left_column: `${sourceNode}.${sourceColumn}`,
      right_column: `${targetNode}.${targetColumn}`,
      operator: '='
    })
    console.log('更新现有连接:', existingEdge)
    Message.success('已添加连接条件')
  } else {
    // 强制连接方向从左到右：源节点始终使用右侧(source)，目标节点始终使用左侧(target)
    // 这符合 SQL JOIN 的语义（左表 JOIN 右表）
    const sourceSide = 'right'; // 源节点使用右侧连接点（source 类型）
    const targetSide = 'left';  // 目标节点使用左侧连接点（target 类型）
    
    // 更新节点数据中的连接点计数（使用响应式更新）
    const sourceHandlesKey = sourceSide === 'left' ? 'leftHandles' : 'rightHandles';
    const targetHandlesKey = targetSide === 'left' ? 'leftHandles' : 'rightHandles';
    
    // 获取当前计数
    const sourceCurrentCount = sourceNodeObj.data[sourceHandlesKey] || 0;
    const targetCurrentCount = targetNodeObj.data[targetHandlesKey] || 0;
    
    // 新增连接点索引
    const sourceHandleIndex = sourceCurrentCount;
    const targetHandleIndex = targetCurrentCount;
    
    // 使用Vue的响应式更新方式：重新赋值整个data对象
    sourceNodeObj.data = {
      ...sourceNodeObj.data,
      [sourceHandlesKey]: sourceCurrentCount + 1
    };
    targetNodeObj.data = {
      ...targetNodeObj.data,
      [targetHandlesKey]: targetCurrentCount + 1
    };
    
    // 生成连接点ID
    const sourceHandle = `${sourceNode}-${sourceSide}-${sourceHandleIndex}`;
    const targetHandle = `${targetNode}-${targetSide}-${targetHandleIndex}`;

    // 创建新连接
    const newEdge: Edge = {
      id: `e${sourceNode}-${targetNode}`,
      source: sourceNode,
      target: targetNode,
      sourceHandle: sourceHandle,
      targetHandle: targetHandle,
      type: 'default',
      label: `${selectedJoinType.value} JOIN`,
      data: {
        joinType: selectedJoinType.value,
        conditions: [{
          left_column: `${sourceNode}.${sourceColumn}`,
          right_column: `${targetNode}.${targetColumn}`,
          operator: '='
        }],
        filters: []
      },
      animated: false,
      style: {
        stroke: '#165dff',
        strokeWidth: 3
      },
      markerEnd: {
        type: 'arrowclosed',
        color: '#165dff'
      }
    }

    edges.value.push(newEdge)
    Message.success(`已建立 ${selectedJoinType.value} JOIN 连接`)
  }
  
  // 清理状态
  connectingColumn.value = null
  pendingConnection.value = null
  showJoinTypeDialog.value = false
  
  console.log('=== 连接创建完成 ===')
}

// 取消JOIN类型选择
function handleJoinTypeCancel() {
  connectingColumn.value = null
  pendingConnection.value = null
  showJoinTypeDialog.value = false
}

// 删除节点
function handleDeleteNode(nodeId: string) {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return

  // 确认删除
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除表 "${node.data.label}" 吗？这将同时删除所有相关的连接。`,
    okText: '确定',
    cancelText: '取消',
    onOk: () => {
      // 删除节点
      nodes.value = nodes.value.filter(n => n.id !== nodeId)
      // 删除相关的边
      edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
      // 如果选中的边被删除了，清空选中
      if (selectedEdge.value && (selectedEdge.value.source === nodeId || selectedEdge.value.target === nodeId)) {
        selectedEdge.value = null
      }
      // 更新视图字段
      updateViewColumns()
      Message.success('删除成功')
    }
  })
}

// 删除边
function handleDeleteEdge(edgeId: string) {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个连接吗？',
    okText: '确定',
    cancelText: '取消',
    onOk: () => {
      edges.value = edges.value.filter(e => e.id !== edgeId)
      if (selectedEdge.value?.id === edgeId) {
        selectedEdge.value = null
        activeTab.value = 'basic'
      }
      Message.success('删除成功')
    }
  })
}

// 自动布局
function handleAutoLayout() {
  if (nodes.value.length === 0) {
    Message.warning('画布上没有节点')
    return
  }

  // 使用分层布局算法
  const levels: Node[][] = []
  const visited = new Set<string>()
  const inDegree = new Map<string, number>()

  // 计算入度
  for (const node of nodes.value) {
    inDegree.set(node.id, 0)
  }
  for (const edge of edges.value) {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
  }

  // 拓扑排序
  const queue = nodes.value.filter(n => inDegree.get(n.id) === 0).map(n => n.id)

  while (queue.length > 0) {
    const currentLevel = [...queue]
    levels.push(currentLevel.map(id => nodes.value.find(n => n.id === id)!))
    queue.length = 0

    for (const nodeId of currentLevel) {
      visited.add(nodeId)
      for (const edge of edges.value) {
        if (edge.source === nodeId && !visited.has(edge.target)) {
          inDegree.set(edge.target, inDegree.get(edge.target)! - 1)
          if (inDegree.get(edge.target) === 0) {
            queue.push(edge.target)
          }
        }
      }
    }
  }

  // 处理循环依赖的节点，放到最后
  const remainingNodes = nodes.value.filter(n => !visited.has(n.id))
  if (remainingNodes.length > 0) {
    levels.push(remainingNodes)
  }

  // 计算节点位置
  const nodeWidth = 260
  const nodeHeight = 200
  const horizontalGap = 40
  const verticalGap = 120
  const startY = 50

  levels.forEach((level, levelIndex) => {
    const levelWidth = level.length * nodeWidth + (level.length - 1) * horizontalGap
    const startX = (1000 - levelWidth) / 2 // 假设画布宽度为1000

    level.forEach((node, nodeIndex) => {
      node.position = {
        x: startX + nodeIndex * (nodeWidth + horizontalGap),
        y: startY + levelIndex * (nodeHeight + verticalGap)
      }
    })
  })

  Message.success('布局已整理')
  fitView({ duration: 800, padding: 0.2 })
}

// 移除条件
function removeCondition(index: number) {
  if (selectedEdge.value?.data?.conditions) {
    selectedEdge.value.data.conditions.splice(index, 1)
  }
}

// 更新视图字段
function updateViewColumns() {
  const cols: typeof viewColumns.value = []
  for (const node of nodes.value) {
    const selectedCols = node.data.selectedColumns || node.data.columns?.map((c: any) => c.name) || []
    for (const col of node.data.columns || []) {
      if (selectedCols.includes(col.name)) {
        cols.push({
          name: col.name,
          type: col.type,
          source_table: node.data.alias,
          selected: true
        })
      }
    }
  }
  viewColumns.value = cols
}

// 保存视图
async function handleSave() {
  if (!formData.value.name) {
    Message.error('请输入视图名称')
    return
  }
  if (!selectedDatasource.value) {
    Message.error('请选择数据源')
    return
  }
  
  saving.value = true
  try {
    const data: any = {
      name: formData.value.name,
      display_name: formData.value.display_name,
      description: formData.value.description,
      datasource_id: selectedDatasource.value,
      view_type: viewType.value,
      columns: viewColumns.value.filter(c => c.selected).map(c => ({
        name: c.name,
        type: c.type,
        source_table: c.source_table
      }))
    }
    
    if (viewType.value === 'sql') {
      data.custom_sql = customSql.value
    } else if (viewType.value === 'joined') {
      data.join_config = {
        tables: nodes.value.map(n => ({
          id: n.data.datasetId,
          alias: n.data.alias,
          position: n.position,
          selectedColumns: n.data.selectedColumns
        })),
        joins: edges.value.map(e => ({
          left_table: e.source,
          right_table: e.target,
          join_type: e.data?.joinType || 'INNER',
          conditions: e.data?.conditions || [],
          filters: e.data?.filters || []
        }))
      }
      data.canvas_config = { nodes: nodes.value, edges: edges.value }
    }
    
    if (isEdit.value) {
      await updateView(viewId.value, data)
      Message.success('更新成功')
    } else {
      const created = await createView(data)
      Message.success('创建成功')
      router.replace(`/semantic/views/${created.id}`)
    }
  } catch (e: any) {
    Message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// 预览数据
async function handlePreview() {
  if (!isEdit.value) {
    Message.warning('请先保存视图')
    return
  }
  
  previewing.value = true
  try {
    const result = await previewView(viewId.value, 100)
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

// 返回列表
function goBack() {
  router.push('/semantic/views')
}

// 视图类型切换
function handleViewTypeChange(value: string) {
  if (value === 'sql' && nodes.value.length > 0) {
    // 从画布切换到SQL,自动同步SQL
    customSql.value = generatedSql.value
  }
}

// 从SQL解析到画布
async function parseSQLToCanvas() {
  if (!customSql.value) {
    Message.warning('请输入SQL语句')
    return
  }

  console.log('开始解析SQL:', customSql.value)
  
  const parsed = parseSQL(customSql.value)
  console.log('解析结果:', parsed)
  
  if (!parsed) {
    Message.error('SQL解析失败,请检查语法')
    return
  }

  // 确保数据源已选择并且表已加载
  if (!selectedDatasource.value) {
    Message.error('请先选择数据源')
    return
  }

  if (tables.value.length === 0) {
    Message.warning('正在加载表数据...')
    await loadTables()
  }

  console.log('当前可用的表:', tables.value.map(t => t.name))

  // 清空现有画布
  nodes.value = []
  edges.value = []

  // 根据表名查找Dataset
  const addedNodes: Map<string, Node> = new Map()
  const nodePositions: Record<string, { x: number; y: number }> = {}
  let foundCount = 0
  
  for (let i = 0; i < parsed.tables.length; i++) {
    const table = parsed.tables[i]
    
    console.log(`查找表: ${table.name}`)
    
    // 查找匹配的Dataset (支持大小写不敏感和带schema的表名)
    const dataset = tables.value.find(t => {
      const tName = t.name.toLowerCase()
      const searchName = table.name.toLowerCase()
      // 支持 schema.table 格式
      return tName === searchName || 
             tName.endsWith(`.${searchName}`) ||
             searchName.endsWith(`.${tName}`)
    })
    
    if (!dataset) {
      console.warn(`未找到表: ${table.name}`)
      Message.warning(`未找到表: ${table.name}，请检查表名或数据源`)
      continue
    }

    console.log(`找到匹配的表: ${dataset.name}`)
    foundCount++

    // 创建节点
    const position = table.position || { x: 100 + i * 300, y: 100 }
    nodePositions[table.alias] = position
    const node: Node = {
      id: table.alias,
      type: 'tableNode',
      position,
      data: {
        label: dataset.name,
        alias: table.alias,
        datasetId: dataset.id,
        columns: dataset.columns || [],
        selectedColumns: dataset.columns?.map((c: any) => c.name) || [],
        leftHandles: 0,
        rightHandles: 0
      }
    }
    
    nodes.value.push(node)
    addedNodes.set(table.alias, node)
  }

  console.log(`成功添加 ${foundCount}/${parsed.tables.length} 个表节点`)

  // 创建连接 (强制从左到右：源节点右侧连目标节点左侧)
  let joinCount = 0
  for (const join of parsed.joins) {
    if (addedNodes.has(join.leftTable) && addedNodes.has(join.rightTable)) {
      // 强制连接方向：源节点使用右侧(source)，目标节点使用左侧(target)
      const sourceSide = 'right'
      const targetSide = 'left'
      
      // 更新节点数据中的连接点计数（使用响应式更新）
      const sourceNode = addedNodes.get(join.leftTable)
      const targetNode = addedNodes.get(join.rightTable)
      
      let sourceHandleIndex = 0
      let targetHandleIndex = 0
      
      if (sourceNode) {
        const sourceCurrentCount = sourceNode.data.rightHandles || 0
        sourceHandleIndex = sourceCurrentCount
        sourceNode.data = {
          ...sourceNode.data,
          rightHandles: sourceCurrentCount + 1
        }
      }
      
      if (targetNode) {
        const targetCurrentCount = targetNode.data.leftHandles || 0
        targetHandleIndex = targetCurrentCount
        targetNode.data = {
          ...targetNode.data,
          leftHandles: targetCurrentCount + 1
        }
      }
      
      // 生成连接点ID
      const sourceHandle = `${join.leftTable}-${sourceSide}-${sourceHandleIndex}`
      const targetHandle = `${join.rightTable}-${targetSide}-${targetHandleIndex}`
      
      edges.value.push({
        id: `${join.leftTable}-${join.rightTable}`,
        source: join.leftTable,
        target: join.rightTable,
        sourceHandle,
        targetHandle,
        data: {
          joinType: join.joinType,
          conditions: join.conditions,
          filters: parsed.whereConditions || []
        },
        animated: true
      })
      joinCount++
    }
  }

  console.log(`成功添加 ${joinCount} 个连接`)
  console.log('最终nodes:', nodes.value)
  console.log('最终edges:', edges.value)

  if (foundCount === 0) {
    Message.error('没有找到匹配的表，请检查SQL中的表名是否与数据源中的表名一致')
    return
  }

  // 更新字段列表
  updateViewColumns()

  // 切换到可视化模式
  viewType.value = 'joined'
  Message.success(`SQL解析成功：添加了 ${foundCount} 个表，${joinCount} 个连接`)
}

// 从画布同步SQL
function syncSQLFromCanvas() {
  customSql.value = generatedSql.value
  Message.success('SQL已同步')
}

onMounted(async () => {
  await loadDatasources()
  if (isEdit.value) {
    // 编辑模式：先加载视图，视图会设置数据源并加载表
    await loadView()
  } else {
    // 新建模式：加载第一个数据源的表
    if (datasources.value.length > 0 && !selectedDatasource.value) {
      selectedDatasource.value = datasources.value[0].id
    }
    await loadTables()
  }
  console.log('VueFlow nodes:', nodes.value)
  console.log('VueFlow edges:', edges.value)
  console.log('VueFlow nodeTypes:', nodeTypes)
})
</script>

<style scoped>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';
@import '@vue-flow/minimap/dist/style.css';

.view-designer {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.designer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e6eb;
}

.view-name {
  font-weight: 600;
  color: #1d2129;
}

.designer-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.table-panel {
  width: 220px;
  background: #fff;
  border-right: 1px solid #e5e6eb;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e5e6eb;
  font-weight: 500;
}

.table-search {
  padding: 8px 12px;
  border-bottom: 1px solid #e5e6eb;
}

.table-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 4px;
  background: #f7f8fa;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
}

.table-item:hover {
  background: #e8f3ff;
  color: #165dff;
}

.canvas-panel {
  flex: 1;
  position: relative;
  min-height: 400px;
  overflow: hidden;
  background: #f5f7fa;
}

.debug-info {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(255, 255, 255, 0.95);
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  max-width: 300px;
}

/* 确保 Vue Flow 画布样式正确 */
.canvas-panel :deep(.vue-flow) {
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  position: absolute;
  top: 0;
  left: 0;
}

/* 确保Background不拦截点击事件 */
.canvas-panel :deep(.vue-flow__background) {
  pointer-events: none !important;
}

.canvas-panel :deep(.vue-flow__background rect) {
  pointer-events: none !important;
}

/* 确保画布交互层可以接收事件 */
.canvas-panel :deep(.vue-flow__pane) {
  cursor: grab !important;
  pointer-events: all !important;
}

.canvas-panel :deep(.vue-flow__pane.dragging) {
  cursor: grabbing !important;
}

.canvas-panel :deep(.vue-flow__transformationpane) {
  width: 100% !important;
  height: 100% !important;
}

.canvas-panel :deep(.vue-flow__viewport) {
  width: 100% !important;
  height: 100% !important;
}

.canvas-panel :deep(.vue-flow__node) {
  cursor: grab !important;
}

.canvas-panel :deep(.vue-flow__node:active) {
  cursor: grabbing !important;
}

/* 自定义 Controls 样式 */
.canvas-panel :deep(.vue-flow__controls) {
  bottom: 20px;
  left: 20px;
  display: flex;
  flex-direction: row;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid #e5e6eb;
}

/* 整理布局按钮样式 */
.layout-button {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 100;
}

.layout-btn-large {
  width: 48px !important;
  height: 48px !important;
  min-width: 48px !important;
  min-height: 48px !important;
  border: none;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d2129;
  border: 1px solid #e5e6eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.layout-btn-large:hover {
  background: #165dff;
  color: #fff;
  border-color: #165dff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.2);
}

.canvas-panel :deep(.vue-flow__controls-button) {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  border: none;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d2129;
  border: 1px solid #e5e6eb;
}

.canvas-panel :deep(.vue-flow__controls-button:hover) {
  background: #165dff;
  color: #fff;
  border-color: #165dff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.2);
}

.canvas-panel :deep(.vue-flow__controls-button svg) {
  width: 18px;
  height: 18px;
}

/* MiniMap 样式 */
.canvas-panel :deep(.vue-flow__minimap) {
  bottom: 20px;
  right: 20px;
  width: 200px;
  height: 150px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid #e5e6eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.canvas-panel :deep(.vue-flow__minimap-mask) {
  fill: rgba(22, 93, 255, 0.1);
}

.canvas-panel :deep(.vue-flow__minimap-node) {
  fill: #165dff;
}

/* 连接线样式 */
.canvas-panel :deep(.vue-flow__edges) {
  z-index: 10 !important;
  pointer-events: all !important;
}

.canvas-panel :deep(.vue-flow__edge) {
  pointer-events: all !important;
  z-index: 10 !important;
}

.canvas-panel :deep(.vue-flow__edge-path) {
  stroke: #165dff !important;
  stroke-width: 3 !important;
  fill: none !important;
  pointer-events: stroke !important;
}

.canvas-panel :deep(.vue-flow__edge.selected .vue-flow__edge-path),
.canvas-panel :deep(.vue-flow__edge-path.selected) {
  stroke: #ff4500 !important;
  stroke-width: 4 !important;
  filter: drop-shadow(0 0 4px rgba(255, 69, 0, 0.6));
}

.canvas-panel :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
  stroke: #4080ff !important;
  stroke-width: 4 !important;
  cursor: pointer;
}

.canvas-panel :deep(.vue-flow__edge .vue-flow__edge-textwrapper) {
  pointer-events: all;
}

/* 箭头标记 */
.canvas-panel :deep(.vue-flow__edge marker) {
  fill: #165dff !important;
}

.canvas-panel :deep(.vue-flow__edge path[marker-end]) {
  stroke: #165dff !important;
}

/* 边的文本标签 */
.canvas-panel :deep(.vue-flow__edge-textbg) {
  fill: white;
}

.canvas-panel :deep(.vue-flow__edge-text) {
  fill: #1d2129;
  font-size: 12px;
}

/* 确保 edges 容器可见 */
.canvas-panel :deep(.vue-flow__edges) {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  pointer-events: none !important;
}

.canvas-panel :deep(.vue-flow__edges > *) {
  pointer-events: all !important;
}

/* 节点样式 */
.canvas-panel :deep(.vue-flow__node) {
  width: fit-content !important;
  height: fit-content !important;
}

.canvas-panel :deep(.vue-flow__node.selected) {
  box-shadow: none !important;
}

.canvas-panel :deep(.vue-flow__node .vue-flow__node-default) {
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
  width: fit-content !important;
  height: fit-content !important;
}

.sql-panel {
  flex: 1;
  padding: 16px;
  background: #fff;
}

.sql-panel :deep(.arco-textarea) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.property-panel {
  width: 280px;
  background: #fff;
  border-left: 1px solid #e5e6eb;
  padding: 12px;
  overflow-y: auto;
}

.join-config {
  padding: 8px 0;
}

.join-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e5e6eb;
  margin-bottom: 12px;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f7f8fa;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 12px;
}

.column-list {
  max-height: 400px;
  overflow-y: auto;
}

.column-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f2f3f5;
}

.col-type {
  font-size: 11px;
  color: #86909c;
}

.preview-panel {
  background: #fff;
  border-top: 1px solid #e5e6eb;
}

.sql-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>
