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


        <a-button v-if="isEdit" @click="handleSetDefault" :loading="settingDefault">
          <template #icon><icon-star /></template>
          设为默认
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
      <transition name="slide-left">
        <div 
          class="table-panel" 
          v-show="showTablePanel && viewType === 'joined'"
          :style="tablePanelStyle"
        >
          <div class="panel-header">
            <span>物理表</span>
            <a-space>
              <a-select v-model="selectedDatasource" placeholder="选择数据源" size="small" style="width: 120px">
                <a-option 
                  v-for="ds in datasources" 
                  :key="ds.id" 
                  :value="ds.id"
                  :title="ds.name"
                >
                  {{ ds.name }}
                </a-option>
              </a-select>
              <a-button size="mini" type="text" @click.stop="showTablePanel = !showTablePanel" class="toggle-icon">
                <template #icon>
                  <icon-menu-fold v-if="showTablePanel" />
                  <icon-menu-unfold v-else />
                </template>
              </a-button>
            </a-space>
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
              <span class="table-name" :title="table.name">{{ table.name }}</span>
            </div>
          </div>
          <!-- 左侧拖拽调整手柄 -->
          <div 
            class="resize-handle resize-handle-right"
            @mousedown.stop="(e: MouseEvent) => startResize('left', e)"
          ></div>
        </div>
      </transition>

      <!-- 中间：画布区域 -->
      <div 
        class="canvas-panel" 
        :class="{
          'no-left-panel': !showTablePanel,
          'no-right-panel': !showPropertyPanel
        }"
        v-show="viewType === 'joined'" 
        @click="handleCanvasClick"
      >
        <!-- 左侧面板触发按钮 -->
        <div v-show="!showTablePanel && viewType === 'joined'" class="panel-trigger left" @click.stop="showTablePanel = true">
          <icon-menu-unfold />
        </div>
        <!-- 右侧面板触发按钮 -->
        <div v-show="!showPropertyPanel && viewType === 'joined'" class="panel-trigger right" @click.stop="showPropertyPanel = true">
          <icon-menu-unfold />
        </div>
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
          :auto-pan-on-node-drag="false"
          :auto-pan-on-connect="false"
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
          <MiniMap class="custom-minimap" pannable zoomable node-size="10" node-stroke-width="0" node-border-radius="2" />
          
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
      <transition name="slide-right">
        <div 
          class="property-panel" 
          v-show="showPropertyPanel && viewType === 'joined'"
          :style="propertyPanelStyle"
        >
          <div class="panel-header">
            <span>属性配置</span>
            <a-button size="mini" type="text" @click.stop="showPropertyPanel = !showPropertyPanel" class="toggle-icon">
              <template #icon>
                <icon-menu-fold v-if="showPropertyPanel" />
                <icon-menu-unfold v-else />
              </template>
            </a-button>
          </div>
          <a-tabs v-model:active-key="activeTab">
            <a-tab-pane key="basic" title="基本信息">
              <a-form :model="formData" layout="vertical" size="small">
                <a-form-item label="视图名称" required>
                  <a-input v-model="formData.name" placeholder="请输入视图名称" />
                </a-form-item>
                <a-form-item label="显示名称">
                  <a-input v-model="formData.display_name" placeholder="请输入显示名称" />
                </a-form-item>
                <a-form-item label="分类">
                  <a-select v-model="formData.category_id" placeholder="选择分类" allow-clear style="width: 100%">
                    <a-option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">
                      {{ cat.category_name }}
                    </a-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="分类名称（可选）">
                  <a-input v-model="formData.category_name" placeholder="请输入新分类名称" allow-clear />
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
              <div class="column-config-panel">
                <a-table
                  :columns="columnConfigColumns"
                  :data="columnConfigs"
                  :pagination="false"
                  :bordered="true"
                  size="small"
                >
                  <template #selected="{ rowIndex }">
                    <a-checkbox v-model="columnConfigs[rowIndex].selected" />
                  </template>
                  <template #name="{ rowIndex }">
                    <span style="font-family: monospace">{{ columnConfigs[rowIndex].name }}</span>
                  </template>
                  <template #display_name="{ rowIndex }">
                    <a-input v-model="columnConfigs[rowIndex].display_name" placeholder="展示名称" size="small" allow-clear />
                  </template>
                  <template #source_comment="{ rowIndex }">
                    <span :title="columnConfigs[rowIndex].source_comment" style="color: var(--color-text-3); font-size: 12px">
                      {{ columnConfigs[rowIndex].source_comment || '-' }}
                    </span>
                  </template>
                  <template #description="{ rowIndex }">
                    <a-input v-model="columnConfigs[rowIndex].description" placeholder="自定义说明" size="small" allow-clear />
                  </template>
                  <template #filterable="{ rowIndex }">
                    <a-switch v-model="columnConfigs[rowIndex].filterable" size="small" />
                  </template>
                  <template #value_config_type="{ rowIndex }">
                    <a-select
                      v-model="columnConfigs[rowIndex].value_config_type"
                      placeholder="值域"
                      size="small"
                      style="width: 100px"
                      @change="handleValueConfigTypeChange(rowIndex)"
                    >
                      <a-option value="">不配置</a-option>
                      <a-option value="enum">枚举</a-option>
                      <a-option value="dict">字典</a-option>
                    </a-select>
                  </template>
                  <template #value_config="{ rowIndex }">
                    <template v-if="columnConfigs[rowIndex].value_config_type === 'enum'">
                      <a-select
                        v-model="columnConfigs[rowIndex].enum_values"
                        multiple
                        placeholder="枚举值"
                        size="small"
                        style="width: 160px"
                        allow-create
                      />
                    </template>
                    <template v-else-if="columnConfigs[rowIndex].value_config_type === 'dict'">
                      <a-select
                        v-model="columnConfigs[rowIndex].dict_id"
                        placeholder="选择字典"
                        size="small"
                        style="width: 160px"
                        allow-search
                      >
                        <a-option v-for="d in dictionaries" :key="d.id" :value="d.id">
                          {{ d.display_name || d.name }}
                        </a-option>
                      </a-select>
                    </template>
                    <span v-else style="color: var(--color-text-4)">-</span>
                  </template>
                </a-table>
              </div>
            </a-tab-pane>
          </a-tabs>
          <!-- 右侧拖拽调整手柄 -->
          <div 
            v-if="showPropertyPanel && viewType === 'joined'"
            class="resize-handle resize-handle-left"
            @mousedown.stop="(e: MouseEvent) => startResize('right', e)"
          ></div>
        </div>
      </transition>
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
      <a-form :model="{}" layout="vertical">
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
    <div class="preview-panel" ref="previewPanelRef">
      <div class="preview-header" @click="showPreviewPanel = !showPreviewPanel">
        <span>SQL预览 & 数据预览</span>
        <a-button size="mini" type="text" class="toggle-icon">
          <template #icon>
            <icon-caret-down v-if="!showPreviewPanel" />
            <icon-caret-up v-else />
          </template>
        </a-button>
      </div>
      <div class="preview-content" v-show="showPreviewPanel">
        <a-collapse :default-active-key="['sql']">
          <a-collapse-item key="sql" header="SQL预览">
            <pre class="sql-preview">{{ generatedSql }}</pre>
          </a-collapse-item>
          <a-collapse-item key="data" header="数据预览">
            <a-space style="margin-bottom: 12px">
              <a-button size="small" type="primary" @click="handlePreview" :loading="previewing">
                执行预览
              </a-button>
              <a-button v-if="previewData.length > 0" size="small" @click="clearPreviewData">
                清空数据
              </a-button>
              <a-tag v-if="previewData.length > 0" color="blue">
                共 {{ previewPagination.total }} 条记录
              </a-tag>
            </a-space>
            <div v-if="previewData.length > 0" class="table-container">
              <a-table
                :columns="previewColumns"
                :data="previewData"
                :pagination="previewPagination"
                size="small"
                row-key="_key"
                :bordered="true"
                :stripe="true"
                :column-resizable="true"
                @page-change="handleTablePageChange"
                @page-size-change="handleTablePageSizeChange"
                @column-resize="handleTableColumnResize"
              >
                <template #empty>
                  <div style="padding: 20px; color: #999;">
                    暂无数据
                  </div>
                </template>
              </a-table>
            </div>
            <a-empty v-else>
              <template #description>
                点击"执行预览"查看数据
              </template>
            </a-empty>
          </a-collapse-item>
        </a-collapse>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, markRaw, provide, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection } from '@vue-flow/core'
import { Message, Modal } from '@arco-design/web-vue'
import {
  IconDelete as IconDelete,
  IconApps,
  IconMenuFold,
  IconMenuUnfold,
  IconCaretDown,
  IconCaretUp,
  IconSearch,
  IconStorage,
  IconStar
} from '@arco-design/web-vue/es/icon'
import TableNode from '@/components/semantic/TableNode.vue'
import ColumnSelectDialog from '@/components/semantic/ColumnSelectDialog.vue'
import JoinConfigPanel from '@/components/semantic/JoinConfigPanel.vue'
import type { JoinConfig } from '@/components/semantic/JoinConfigPanel.vue'
import { getDataSources, getDatasets } from '@/api/semantic'
import { getView, createView, updateView, previewView, generateViewSQL, getCategoryStats, getCategories, setDefaultView } from '@/api/views'
import { getDictionaries } from '@/api/dictionaries'
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
const vueFlowInstance = useVueFlow()
const { project, fitView } = vueFlowInstance

// 状态
const saving = ref(false)
const previewing = ref(false)
const settingDefault = ref(false)
const showTablePanel = ref(true)
const showPropertyPanel = ref(true)
const showPreviewPanel = ref(true)
const previewPanelRef = ref<HTMLElement | null>(null)
const datasources = ref<DataSource[]>([])
const selectedDatasource = ref('')
const categories = ref<Array<{ category_id: string | null; category_name: string; view_count?: number }>>([])
const tables = ref<Dataset[]>([])
const tableSearchKeyword = ref('')
const viewType = ref<'joined' | 'sql'>('joined')
const customSql = ref('')
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const selectedEdge = ref<Edge | null>(null)
const viewName = ref('')
const activeTab = ref('basic')

// 面板宽度调整
const tablePanelWidth = ref(250)
const propertyPanelWidth = ref(400)
const isResizing = ref(false)
const resizeType = ref<'left' | 'right' | null>(null)

// 面板样式计算
const tablePanelStyle = computed(() => ({
  width: `${tablePanelWidth.value}px`
}))

const propertyPanelStyle = computed(() => ({
  width: `${propertyPanelWidth.value}px`
}))

// 监听画布变换状态
let transformTimer: ReturnType<typeof setTimeout> | null = null
watch(() => vueFlowInstance.getViewport(), (viewport) => {
  if (transformTimer) clearTimeout(transformTimer)
}, { deep: true })

// 监听节点位置变化
watch(() => nodes.value.map(n => ({ id: n.id, position: n.position })), () => {
  // 节点位置变化时的处理
}, { deep: true })

// 字段选择弹窗
const showColumnSelect = ref(false)
const pendingTableColumns = ref<any[]>([])
const pendingSelectedColumns = ref<string[]>([])
const pendingTableData = ref<any>(null)

const formData = ref({
  name: '',
  display_name: '',
  category_id: null as string | null,
  category_name: '',
  description: ''
})

// 预览数据
const previewColumns = ref<any[]>([])
const previewData = ref<any[]>([])
const previewPagination = ref({
  total: 0,
  current: 1,
  pageSize: 10,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100]
})

// 列宽配置
const MAX_COLUMN_WIDTH = 400  // 最大列宽
const MIN_COLUMN_WIDTH = 80   // 最小列宽
const columnWidths = ref<Record<string, number>>({})  // 存储自定义列宽

// 视图字段
const viewColumns = ref<Array<{ name: string; type: string; selected: boolean; source_table?: string }>>([])

// 字典列表
const dictionaries = ref<any[]>([])

// 字段配置表格列定义
const columnConfigColumns = [
  { title: '选用', slotName: 'selected', width: 50 },
  { title: '字段名', slotName: 'name', width: 100 },
  { title: '类型', dataIndex: 'type', width: 70 },
  { title: '物理说明', slotName: 'source_comment', width: 120 },
  { title: '展示名', slotName: 'display_name', width: 100 },
  { title: '自定义说明', slotName: 'description', width: 130 },
  { title: '可过滤', slotName: 'filterable', width: 60 },
  { title: '值域类型', slotName: 'value_config_type', width: 90 },
  { title: '值域配置', slotName: 'value_config', width: 160 }
]

// 字段配置数据（扩展版）
interface ColumnConfig {
  name: string
  type: string
  selected: boolean
  source_table?: string
  source_comment?: string  // 物理表字段注释
  display_name?: string
  description?: string  // 自定义说明
  filterable: boolean
  value_config_type: '' | 'enum' | 'dict'
  enum_values?: string[]
  dict_id?: string
}

const columnConfigs = ref<ColumnConfig[]>([])

// 监听 viewColumns 变化，更新 columnConfigs
watch(viewColumns, (newCols) => {
  console.log('[watch viewColumns] triggered, newCols:', JSON.stringify(newCols))
  // 保留已有的配置
  const existingConfigs = new Map(columnConfigs.value.map(c => [c.name, c]))
  console.log('[watch viewColumns] existingConfigs size:', existingConfigs.size)
  
  columnConfigs.value = newCols.map(col => {
    const existing = existingConfigs.get(col.name)
    
    // 从 viewColumns 中的字段数据解析值域配置
    let valueConfigType = ''
    let enumValues: string[] = []
    let dictId = ''
    
    // 解析 value_config
    const vc = (col as any).value_config
    console.log('[watch viewColumns] col:', col.name, 'value_config:', vc)
    if (vc) {
      const vcType = vc.type
      if (vcType === 'enum') {
        valueConfigType = 'enum'
        enumValues = vc.enum_values || []
      } else if (vcType === 'dict') {
        valueConfigType = 'dict'
        dictId = vc.dict_id || ''
      }
    }
    
    console.log('[watch viewColumns] parsed:', col.name, 'valueConfigType:', valueConfigType, 'dictId:', dictId, 'description:', col.description)
    
    // 决定使用哪个值：优先使用用户编辑过的配置，否则从后端数据恢复
    const useExistingDisplayName = existing?.display_name !== undefined && existing?.display_name !== ''
    const useExistingDesc = existing?.description !== undefined && existing?.description !== ''

    const result = {
      name: col.name,
      type: col.type,
      selected: col.selected,
      source_table: col.source_table,
      source_comment: (col as any).source_comment || (col as any).comment || '',
      // 展示名称：优先使用用户已编辑的值
      display_name: useExistingDisplayName ? existing!.display_name : ((col as any).display_name || ''),
      // 自定义说明：优先使用用户已编辑的值
      description: useExistingDesc ? existing!.description : ((col as any).description || ''),
      filterable: existing?.filterable !== undefined ? existing.filterable : ((col as any).filterable ?? true),
      // 值域配置：优先使用用户已编辑的值，否则使用解析出的值
      value_config_type: (existing?.value_config_type && existing.value_config_type !== '') 
        ? existing.value_config_type : valueConfigType,
      enum_values: (existing?.enum_values?.length) ? existing.enum_values : enumValues,
      dict_id: (existing?.dict_id && existing.dict_id !== '') ? existing.dict_id : dictId
    }
    console.log('[watch viewColumns] result:', col.name, result)
    return result
  })
}, { immediate: true })

// 处理值域类型变化
function handleValueConfigTypeChange(rowIndex: number) {
  const config = columnConfigs.value[rowIndex]
  if (config.value_config_type === 'enum') {
    config.enum_values = []
  } else if (config.value_config_type === 'dict') {
    config.dict_id = ''
  }
}

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
      // 在ON子句中添加表别名
      const onClause = conditions.map((c: any) => `${sourceNode.data.alias}.${c.left_column} ${c.operator || '='} ${targetNode.data.alias}.${c.right_column}`).join(' AND ') || '1=1'
      
      // 添加filters到ON子句（而不是WHERE）
      const filters = edge.data?.filters || []
      const filterClauses = filters.map((f: any) => {
        if (['IS NULL', 'IS NOT NULL'].includes(f.operator)) {
          return `${f.column} ${f.operator}`
        } else {
          return `${f.column} ${f.operator} '${f.value}'`
        }
      })
      
      const allOnConditions = [onClause, ...filterClauses].filter(Boolean).join(' AND ')
      
      fromClause += `\n${joinType} JOIN ${targetNode.data.label} AS ${targetNode.data.alias} ON ${allOnConditions}`
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

// 加载分类
async function loadCategories() {
  try {
    // 获取定义的分类列表
    const categoryList = await getCategories()

    // 转换为 a-select 需要的格式
    categories.value = categoryList.map(cat => ({
      category_id: cat.id,
      category_name: cat.name,
      view_count: undefined
    }))

    // 可选：添加统计信息（如果需要显示视图数量）
    const stats = await getCategoryStats(selectedDatasource.value)
    const statsMap = new Map(
      stats.categories
        .filter(c => c.category_id)
        .map(c => [c.category_id, c.view_count])
    )

    // 合并统计信息
    categories.value.forEach(cat => {
      if (cat.category_id && statsMap.has(cat.category_id)) {
        cat.view_count = statsMap.get(cat.category_id)
      }
    })
  } catch (e) {
    console.error('Failed to load categories:', e)
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
  loadCategories()
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
          type: 'default',
          label: `${j.join_type || 'INNER'} JOIN`,
          data: {
            joinType: j.join_type || 'INNER',
            conditions: j.conditions || [],
            filters: j.filters || []
          },
          animated: true,
          style: {
            stroke: '#165dff',
            strokeWidth: 3
          },
          markerEnd: {
            type: 'arrowclosed',
            color: '#165dff'
          }
        })
      }
    }

    // 恢复字段列表
    if (view.columns) {
      // 直接将后端列数据转换为前端期望的格式
      const convertedColumns: ColumnConfig[] = view.columns.map((c: any) => {
        // 解析 value_config
        let valueConfigType: '' | 'enum' | 'dict' = ''
        let enumValues: string[] = []
        let dictId = ''

        const vc = c.value_config
        if (vc) {
          const vcType = vc.type
          if (vcType === 'enum') {
            valueConfigType = 'enum'
            enumValues = vc.enum_values || []
          } else if (vcType === 'dict') {
            valueConfigType = 'dict'
            dictId = vc.dict_id || ''
          }
        }

        return {
          name: c.name,
          type: c.type,
          selected: true,
          source_table: c.source_table,
          source_comment: (c.source_comment || '') as string,
          display_name: (c.display_name || '') as string,
          description: (c.description || '') as string,
          filterable: (c.filterable ?? true) as boolean,
          value_config_type: valueConfigType,
          enum_values: enumValues,
          dict_id: dictId
        }
      })

      columnConfigs.value = convertedColumns

      // 设置 viewColumns（仅用于触发后续的 watch）
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

  // 获取 Vue Flow 容器的位置
  const vueFlowElement = document.querySelector('.vue-flow') as HTMLElement
  if (!vueFlowElement) return

  const vueFlowRect = vueFlowElement.getBoundingClientRect()

  // 计算相对于 Vue Flow 容器的坐标
  const relativeX = event.clientX - vueFlowRect.left
  const relativeY = event.clientY - vueFlowRect.top

  // 使用 project 函数将相对坐标转换为画布逻辑坐标
  const projectedPosition = project({ x: relativeX, y: relativeY })
  
  // 节点尺寸（宽度固定240px，高度根据字段数量动态计算）
  const nodeWidth = 240
  const headerHeight = 36 // 表头高度
  const columnItemHeight = 36 // 每个字段的高度
  const maxColumnsHeight = 400 // table-columns-wrapper 的 max-height
  const footerHeight = 0 // 底部高度（如果有未选择字段提示）
  
  // 计算实际显示的字段区域高度
  const columnCount = table.columns?.length || 0
  const totalColumnsHeight = columnCount * columnItemHeight
  const actualColumnsHeight = Math.min(totalColumnsHeight, maxColumnsHeight)
  const estimatedNodeHeight = headerHeight + actualColumnsHeight + footerHeight
  
  // 调整位置，使节点中心对齐鼠标位置
  const position = {
    x: projectedPosition.x - nodeWidth / 2,
    y: projectedPosition.y - estimatedNodeHeight / 2
  }

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
  const newNode = {
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
  }

  nodes.value.push(newNode)

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
      value: col.name  // 只返回列名，不返回带别名的格式
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
}

// 边变化处理
function onEdgesChange(params: any[]) {
  // 处理边的删除事件，更新连接点计数
  params.forEach(param => {
    if (param.type === 'remove' && param.item) {
      deleteSingleEdge(param.item.id)
    }
  })
}

// 边点击
function onEdgeClick({ edge }: { edge: Edge }) {
  selectedEdge.value = edge
  activeTab.value = 'joins'
}

// 节点点击
function handleNodeClick({ node }: { node: Node }) {
  // 节点点击处理
}

// 画布空白处点击
function handlePaneClick(event: MouseEvent) {
  // 取消选中边
  selectedEdge.value = null
}

// 画布容器点击
function handleCanvasClick(event: MouseEvent) {
  // 画布容器点击处理
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
    
    // 显示JOIN类型选择对话框
    showJoinTypeDialog.value = true
  }
}

// 确认JOIN类型并建立连接
// 确认JOIN类型并建立连接
function handleJoinTypeConfirm() {
  if (!pendingConnection.value) return
  
  const { sourceNode, sourceColumn, targetNode, targetColumn } = pendingConnection.value
  
  // 验证节点是否存在
  const sourceNodeObj = nodes.value.find(n => n.id === sourceNode)
  const targetNodeObj = nodes.value.find(n => n.id === targetNode)
  
  if (!sourceNodeObj || !targetNodeObj) {
    Message.error('节点不存在，无法创建连接')
    return
  }
  
  // 根据节点的X坐标判断左右关系，确保连线从左到右
  const leftNode = sourceNodeObj.position.x < targetNodeObj.position.x ? sourceNodeObj : targetNodeObj
  const rightNode = sourceNodeObj.position.x < targetNodeObj.position.x ? targetNodeObj : sourceNodeObj
  const leftColumn = sourceNodeObj.position.x < targetNodeObj.position.x ? sourceColumn : targetColumn
  const rightColumn = sourceNodeObj.position.x < targetNodeObj.position.x ? targetColumn : sourceColumn
  
  // 检查是否已存在连接
  let existingEdge = edges.value.find(
    e => (e.source === leftNode.id && e.target === rightNode.id) ||
         (e.source === rightNode.id && e.target === leftNode.id)
  )
  
  if (existingEdge) {
    // 添加条件到现有连接
    if (!existingEdge.data) existingEdge.data = { joinType: selectedJoinType.value, conditions: [], filters: [] }
    if (!existingEdge.data.conditions) existingEdge.data.conditions = []
    existingEdge.data.conditions.push({
      left_column: leftColumn,
      right_column: rightColumn,
      operator: '='
    })
    Message.success('已添加连接条件')
  } else {
    // 左节点使用右侧连接点（source），右节点使用左侧连接点（target）
    const leftSide = 'right'
    const rightSide = 'left'
    
    // 更新节点数据中的连接点计数
    const leftHandlesKey = 'rightHandles'
    const rightHandlesKey = 'leftHandles'
    
    // 获取当前计数
    const leftCurrentCount = leftNode.data[leftHandlesKey] || 0
    const rightCurrentCount = rightNode.data[rightHandlesKey] || 0
    
    // 新增连接点索引
    const leftHandleIndex = leftCurrentCount
    const rightHandleIndex = rightCurrentCount
    
    // 使用Vue的响应式更新方式
    leftNode.data = {
      ...leftNode.data,
      [leftHandlesKey]: leftCurrentCount + 1
    }
    rightNode.data = {
      ...rightNode.data,
      [rightHandlesKey]: rightCurrentCount + 1
    }
    
    // 生成连接点ID
    const sourceHandle = `${leftNode.id}-${leftSide}-${leftHandleIndex}`
    const targetHandle = `${rightNode.id}-${rightSide}-${rightHandleIndex}`

    // 创建新连接（从左节点到右节点）
    const newEdge: Edge = {
      id: `e${leftNode.id}-${rightNode.id}`,
      source: leftNode.id,
      target: rightNode.id,
      sourceHandle: sourceHandle,
      targetHandle: targetHandle,
      type: 'default',
      label: `${selectedJoinType.value} JOIN`,
      data: {
        joinType: selectedJoinType.value,
        conditions: [{
          left_column: leftColumn,
          right_column: rightColumn,
          operator: '='
        }],
        filters: []
      },
      animated: true,
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
      // 收集所有连接到该节点的边
      const edgesToDelete = edges.value.filter(e => e.source === nodeId || e.target === nodeId)
      
      // 解析连接点ID，获取节点ID、侧和索引
      const parseHandle = (handleId: string) => {
        // handleId格式: ${nodeId}-${side}-${index}
        const parts = handleId.split('-')
        if (parts.length < 3) return null
        const index = parseInt(parts[parts.length - 1])
        const side = parts[parts.length - 2]
        const nodeId = parts.slice(0, parts.length - 2).join('-')
        return { nodeId, side, index }
      }
      
      // 减少相邻节点的连接点计数
      edgesToDelete.forEach(edge => {
        const sourceHandleInfo = parseHandle(edge.sourceHandle || '')
        const targetHandleInfo = parseHandle(edge.targetHandle || '')
        
        // 减少源节点计数（如果源节点不是被删除的节点）
        if (sourceHandleInfo && sourceHandleInfo.nodeId !== nodeId) {
          const { nodeId: adjNodeId, side } = sourceHandleInfo
          const adjNode = nodes.value.find(n => n.id === adjNodeId)
          if (adjNode) {
            const handleKey = side === 'left' ? 'leftHandles' : 'rightHandles'
            const currentCount = adjNode.data[handleKey] || 0
            if (currentCount > 0) {
              adjNode.data = {
                ...adjNode.data,
                [handleKey]: currentCount - 1
              }
            }
          }
        }
        
        // 减少目标节点计数（如果目标节点不是被删除的节点）
        if (targetHandleInfo && targetHandleInfo.nodeId !== nodeId) {
          const { nodeId: adjNodeId, side } = targetHandleInfo
          const adjNode = nodes.value.find(n => n.id === adjNodeId)
          if (adjNode) {
            const handleKey = side === 'left' ? 'leftHandles' : 'rightHandles'
            const currentCount = adjNode.data[handleKey] || 0
            if (currentCount > 0) {
              adjNode.data = {
                ...adjNode.data,
                [handleKey]: currentCount - 1
              }
            }
          }
        }
      })
      
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

// 删除单条边并更新连接点计数
function deleteSingleEdge(edgeId: string) {
  // 找到要删除的边
  const edgeToDelete = edges.value.find(e => e.id === edgeId)
  if (!edgeToDelete) {
    Message.error('未找到要删除的连接')
    return false
  }

  // 解析连接点ID，获取节点ID、侧和索引
  const parseHandle = (handleId: string) => {
    // handleId格式: ${nodeId}-${side}-${index}
    const parts = handleId.split('-')
    if (parts.length < 3) return null
    const index = parseInt(parts[parts.length - 1])
    const side = parts[parts.length - 2]
    const nodeId = parts.slice(0, parts.length - 2).join('-')
    return { nodeId, side, index }
  }

  const sourceHandleInfo = parseHandle(edgeToDelete.sourceHandle || '')
  const targetHandleInfo = parseHandle(edgeToDelete.targetHandle || '')

  // 减少源节点和目标节点的连接点计数
  if (sourceHandleInfo) {
    const { nodeId, side } = sourceHandleInfo
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      const handleKey = side === 'left' ? 'leftHandles' : 'rightHandles'
      const currentCount = node.data[handleKey] || 0
      if (currentCount > 0) {
        node.data = {
          ...node.data,
          [handleKey]: currentCount - 1
        }
      }
    }
  }

  if (targetHandleInfo) {
    const { nodeId, side } = targetHandleInfo
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      const handleKey = side === 'left' ? 'leftHandles' : 'rightHandles'
      const currentCount = node.data[handleKey] || 0
      if (currentCount > 0) {
        node.data = {
          ...node.data,
          [handleKey]: currentCount - 1
        }
      }
    }
  }

  // 重新索引同一节点同一侧的其他边
  const reindexHandles = (handleInfo: { nodeId: string; side: string; index: number } | null) => {
    if (!handleInfo) return
    
    const { nodeId, side, index: deletedIndex } = handleInfo
    // 找到所有使用该节点该侧的边
    edges.value.forEach(edge => {
      // 检查sourceHandle
      if (edge.sourceHandle) {
        const info = parseHandle(edge.sourceHandle)
        if (info && info.nodeId === nodeId && info.side === side && info.index > deletedIndex) {
          // 更新索引：减1
          const newIndex = info.index - 1
          edge.sourceHandle = `${nodeId}-${side}-${newIndex}`
        }
      }
      // 检查targetHandle
      if (edge.targetHandle) {
        const info = parseHandle(edge.targetHandle)
        if (info && info.nodeId === nodeId && info.side === side && info.index > deletedIndex) {
          // 更新索引：减1
          const newIndex = info.index - 1
          edge.targetHandle = `${nodeId}-${side}-${newIndex}`
        }
      }
    })
  }

  // 重新索引源节点和目标节点的连接点
  if (sourceHandleInfo) {
    reindexHandles(sourceHandleInfo)
  }
  if (targetHandleInfo) {
    reindexHandles(targetHandleInfo)
  }

  // 删除边
  edges.value = edges.value.filter(e => e.id !== edgeId)
  if (selectedEdge.value?.id === edgeId) {
    selectedEdge.value = null
    activeTab.value = 'basic'
  }
  return true
}

// 删除边
function handleDeleteEdge(edgeId: string) {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个连接吗？',
    okText: '确定',
    cancelText: '取消',
    onOk: () => {
      if (deleteSingleEdge(edgeId)) {
        Message.success('删除成功')
      }
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
          source_comment: col.comment || '',  // 物理表字段说明
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
    // 获取分类名称
    let categoryName = formData.value.category_name
    if (formData.value.category_id && !categoryName) {
      const selectedCategory = categories.value.find(c => c.category_id === formData.value.category_id)
      categoryName = selectedCategory?.category_name || ''
    }

    const data: any = {
      name: formData.value.name,
      display_name: formData.value.display_name,
      description: formData.value.description,
      datasource_id: selectedDatasource.value,
      view_type: viewType.value,
      category_id: formData.value.category_id,
      category_name: categoryName,
      columns: viewColumns.value.filter(c => c.selected).map(c => {
        const config = columnConfigs.value.find(cc => cc.name === c.name)
        const colData: any = {
          name: c.name,
          type: c.type,
          source_table: c.source_table,
          source_comment: c.source_comment  // 物理表字段说明
        }
        // 添加字段配置
        if (config) {
          if (config.display_name) colData.display_name = config.display_name
          if (config.description) colData.description = config.description
          colData.filterable = config.filterable
          if (config.value_config_type === 'enum' && config.enum_values?.length) {
            colData.value_config = { type: 'enum', enum_values: config.enum_values }
          } else if (config.value_config_type === 'dict' && config.dict_id) {
            colData.value_config = { type: 'dict', dict_id: config.dict_id }
          }
        }
        return colData
      })
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

// 设为默认视图
async function handleSetDefault() {
  if (!isEdit.value || !viewId.value) {
    Message.warning('请先保存视图')
    return
  }
  
  settingDefault.value = true
  try {
    await setDefaultView(viewId.value)
    Message.success('已设置为默认视图')
  } catch (e: any) {
    Message.error(e.message || '设置默认视图失败')
  } finally {
    settingDefault.value = false
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
    // 使用后端分页查询
    const result = await previewView(viewId.value, {
      page: previewPagination.value.current,
      page_size: previewPagination.value.pageSize
    })
    
    // 更新分页信息
    previewPagination.value.total = result.total
    
    // 处理列配置
    previewColumns.value = result.columns.map((c, index) => ({
      title: c,
      dataIndex: c,
      key: c,
      width: columnWidths.value[c] || getColumnWidth(c, result.data),
      ellipsis: true,
      tooltip: true
    }))
    
    // 存储当前页数据
    previewData.value = result.data.map((row, idx) => {
      const obj: Record<string, any> = { _key: `${previewPagination.value.current}_${idx}_${Date.now()}` }
      result.columns.forEach((col, i) => {
        obj[col] = formatCellValue(row[i])
      })
      return obj
    })
    
    if (result.data.length === 0) {
      Message.info('查询成功，但没有返回数据')
    } else {
      Message.success(`查询成功，共 ${result.total} 条记录`)
    }
  } catch (e: any) {
    Message.error(e.message || '预览失败')
    // 清空之前的数据
    clearPreviewData()
  } finally {
    previewing.value = false
  }
}

// 格式化单元格值
function formatCellValue(value: any): string {
  if (value === null || value === undefined) {
    return ''
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

// 获取列宽
function getColumnWidth(columnName: string, data: any[][]): number {
  const maxLength = Math.max(
    columnName.length,
    ...data.slice(0, 50).map(row => {
      const value = row[data[0].indexOf(columnName)]
      return String(value || '').length
    })
  )
  // 自适应列宽，但不超过最大宽度
  const autoWidth = Math.max(maxLength * 8 + 20, MIN_COLUMN_WIDTH)
  return Math.min(autoWidth, MAX_COLUMN_WIDTH)
}

// 处理列宽调整
function handleColumnResize(columnName: string, width: number) {
  // 确保列宽在合理范围内
  const constrainedWidth = Math.max(MIN_COLUMN_WIDTH, Math.min(width, MAX_COLUMN_WIDTH))
  columnWidths.value[columnName] = constrainedWidth
  // 更新列配置
  const column = previewColumns.value.find(col => col.dataIndex === columnName)
  if (column) {
    column.width = constrainedWidth
  }
}

// 处理表格列宽调整事件
function handleTableColumnResize(dataIndex: string, width: number) {
  handleColumnResize(dataIndex, width)
}

// 清空预览数据
function clearPreviewData() {
  previewData.value = []
  previewColumns.value = []
  previewPagination.value.total = 0
  previewPagination.value.current = 1
}

// 处理表格页码变化
function handleTablePageChange(page: number) {
  previewPagination.value.current = page
  handlePreview()  // 重新请求后端数据
}

// 处理表格每页条数变化
function handleTablePageSizeChange(pageSize: number) {
  previewPagination.value.pageSize = pageSize
  previewPagination.value.current = 1
  handlePreview()  // 重新请求后端数据
}

// 返回列表
function goBack() {
  router.push('/semantic/views')
}

// 面板宽度调整相关函数
let startX = 0
let startWidth = 0

function startResize(type: 'left' | 'right', event: MouseEvent) {
  isResizing.value = true
  resizeType.value = type
  startX = event.clientX
  
  if (type === 'left') {
    startWidth = tablePanelWidth.value
  } else {
    startWidth = propertyPanelWidth.value
  }
  
  // 添加全局样式防止文本选中
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
}

function handleResize(event: MouseEvent) {
  if (!isResizing.value || !resizeType.value) return
  
  const deltaX = event.clientX - startX
  
  if (resizeType.value === 'left') {
    // 左侧面板：根据鼠标移动距离调整宽度
    const newWidth = startWidth + deltaX
    if (newWidth >= 180 && newWidth <= 400) {
      tablePanelWidth.value = newWidth
    }
  } else if (resizeType.value === 'right') {
    // 右侧面板：根据鼠标移动距离调整宽度（反向）
    const newWidth = startWidth - deltaX
    if (newWidth >= 350 && newWidth <= 600) {
      propertyPanelWidth.value = newWidth
    }
  }
}

function stopResize() {
  isResizing.value = false
  resizeType.value = null
  startX = 0
  startWidth = 0
  
  // 恢复全局样式
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
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

  // 从 SELECT 子句中提取每个表的字段
  // parsed.columns 格式: ["t0.rec_id", "t0.task_num", "t1.type_name", ...]
  const tableColumns: Map<string, Set<string>> = new Map()
  for (const col of parsed.columns) {
    if (col === '*') {
      // SELECT * 的情况，所有表的所有字段都选中
      continue
    }
    // 解析列名：可能是 "alias.column" 或 "column" 格式
    const parts = col.split('.')
    if (parts.length === 2) {
      const alias = parts[0]
      const columnName = parts[1]
      if (!tableColumns.has(alias)) {
        tableColumns.set(alias, new Set())
      }
      tableColumns.get(alias)!.add(columnName)
    } else if (parts.length === 1) {
      // 没有表别名的列，暂时跳过（需要后续推断）
      console.log(`列 ${col} 没有表别名，跳过`)
    }
  }

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

    // 获取该表在 SELECT 子句中的字段
    const selectedCols = tableColumns.get(table.alias)
    let selectedColumns: string[]
    if (selectedCols && selectedCols.size > 0) {
      // 只选择 SELECT 子句中指定的字段
      selectedColumns = Array.from(selectedCols)
    } else {
      // 如果 SELECT 子句是 * 或没有该表的字段，选择全部字段
      selectedColumns = dataset.columns?.map((c: any) => c.name) || []
    }

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
        selectedColumns,
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
        type: 'default',
        label: `${join.joinType} JOIN`,
        data: {
          joinType: join.joinType,
          conditions: join.conditions,
          filters: join.filters || []
        },
        animated: true,
        style: {
          stroke: '#165dff',
          strokeWidth: 3
        },
        markerEnd: {
          type: 'arrowclosed',
          color: '#165dff'
        }
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
  // 加载字典列表
  try {
    dictionaries.value = await getDictionaries()
  } catch (e) {
    console.error('Failed to load dictionaries:', e)
  }
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
})

onUnmounted(() => {
  // 清理事件监听器
  if (isResizing.value) {
    document.removeEventListener('mousemove', handleResize)
    document.removeEventListener('mouseup', stopResize)
  }
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
  width: 250px;
  background: #fff;
  border-right: 1px solid #e5e6eb;
  display: flex;
  flex-direction: column;
  position: relative;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e5e6eb;
  font-weight: 500;
}

.panel-header :deep(.arco-select-view-value) {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-header :deep(.arco-select-option) {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-header .toggle-icon {
  color: #86909c;
  transition: color 0.2s;
}

.panel-header .toggle-icon:hover {
  color: #165dff;
}

.table-search {
  padding: 8px 12px;
  border-bottom: 1px solid #e5e6eb;
}

.table-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
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

.table-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-panel {
  flex: 1;
  position: relative;
  min-height: 400px;
  overflow: hidden;
  background: #f5f7fa;
  transition: all 0.3s ease;
}

/* 当左侧面板隐藏时，画布占据左侧空间 */
.canvas-panel.no-left-panel {
  margin-left: 0;
}

/* 当右侧面板隐藏时，画布占据右侧空间 */
.canvas-panel.no-right-panel {
  margin-right: 0;
}

/* 当两侧面板都隐藏时，画布全宽 */
.canvas-panel.no-left-panel.no-right-panel {
  width: 100%;
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
  /* 关键修复：防止 transformationpane 高度累加 */
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
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
  /* 固定在右下角 */
  position: absolute !important;
  z-index: 1000;
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
  /* 关键修复：确保节点使用绝对定位，不影响容器高度 */
  position: absolute !important;
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
  background: #fff;
  border-left: 1px solid #e5e6eb;
  padding: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  flex-shrink: 0;
}

.property-panel :deep(.arco-tabs) {
  width: 100%;
}

.property-panel :deep(.arco-tabs-content) {
  width: 100%;
  padding: 0;
}

.property-panel :deep(.arco-tabs-pane) {
  width: 100%;
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
  position: relative;
  z-index: 100;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  font-weight: 500;
  cursor: pointer;
  background: #f7f8fa;
  border-bottom: 1px solid #e5e6eb;
  transition: background 0.2s;
}

.preview-header:hover {
  background: #e8f3ff;
}

.preview-header .toggle-icon {
  color: #86909c;
}

.preview-content {
  max-height: 400px;
  overflow-y: auto;
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

/* 面板触发按钮 */
.panel-trigger {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 60px;
  background: #165dff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  border-radius: 0 4px 4px 0;
  transition: all 0.2s;
  opacity: 0.8;
}

.panel-trigger:hover {
  opacity: 1;
  width: 28px;
}

.panel-trigger.left {
  left: 0;
  border-radius: 0 4px 4px 0;
}

.panel-trigger.right {
  right: 0;
  border-radius: 4px 0 0 4px;
}

.panel-trigger svg {
  width: 16px;
  height: 16px;
}

/* 数据预览表格样式 */
.table-container {
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  overflow: visible;
}

.preview-content :deep(.arco-table) {
  border-radius: 6px;
}

/* 列宽调整样式 */
.preview-content :deep(.arco-table-th) {
  background: #f7f8fa !important;
  font-weight: 600;
  color: #1d2129;
  position: relative;
}

/* 列宽拖拽手柄 */
.preview-content :deep(.arco-table-resize-trigger) {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  background: transparent;
  transition: background 0.2s;
  z-index: 10;
}

.preview-content :deep(.arco-table-resize-trigger:hover) {
  background: #165dff;
}

/* 单元格样式 - 确保对齐 */
.preview-content :deep(.arco-table-td) {
  padding: 8px 12px;
  white-space: nowrap;
}

/* 表格容器无滚动条 */
.preview-content :deep(.arco-table-container) {
  overflow: visible;
}

.preview-content :deep(.arco-table-body) {
  overflow: visible;
}

.preview-content :deep(.arco-table-tr:hover .arco-table-td:not(.arco-table-col-fixed-left):not(.arco-table-col-fixed-right)) {
  background: #f7f8fa;
}

/* 空状态样式 */
.preview-content .arco-empty {
  padding: 40px 0;
}

/* 强制Handle垂直居中 - 覆盖Vue Flow的默认样式 */
/* 考虑到表头的存在，调整到视觉中心（表头底部 + 字段区域一半） */
/* 表头高度约38px，所以从50%向下偏移约17px到达视觉中心 */
.canvas-panel :deep(.vue-flow__handle) {
  top: calc(50% + 17px) !important;
  transform: none !important;
}

/* 使用data属性选择器确保样式生效 */
.canvas-panel :deep([data-handlepos="left"]) {
  left: -6px !important;
  top: calc(50% + 17px) !important;
  transform: none !important;
}

.canvas-panel :deep([data-handlepos="right"]) {
  right: -6px !important;
  top: calc(50% + 17px) !important;
  transform: none !important;
}

.canvas-panel :deep(.vue-flow__handle-left) {
  left: -6px !important;
}

.canvas-panel :deep(.vue-flow__handle-right) {
  right: -6px !important;
}

/* 拖拽调整手柄 - 明显可见 */
.resize-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  background: transparent;
  transition: all 0.2s;
  z-index: 1000;
}

.resize-handle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 40px;
  background: #d9d9d9;
  border-radius: 1px;
  transition: all 0.2s;
}

.resize-handle:hover::after,
.resize-handle:active::after {
  background: #165dff;
  height: 60px;
}

.resize-handle:hover {
  background: rgba(22, 93, 255, 0.08);
}

.resize-handle:active {
  background: rgba(22, 93, 255, 0.15);
}

.resize-handle-right {
  right: -3px;
}

.resize-handle-left {
  left: -3px;
}



/* 拖拽时的遮罩层 */
.designer-body.resizing {
  user-select: none;
}

/* 左侧面板展开收起过渡动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  width: 0 !important;
  opacity: 0;
  transform: translateX(-100%);
}

/* 右侧面板展开收起过渡动画 */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  width: 0 !important;
  opacity: 0;
  transform: translateX(100%);
}

</style>
