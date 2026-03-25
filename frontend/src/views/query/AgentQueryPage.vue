<template>
  <div class="query-page">
    <ModelNotConfigured v-if="!settingsStore.isModelAvailable" />

    <template v-else>
      <!-- 顶部标题栏 + 视图选择 -->
      <div class="query-header">
        <span class="query-title">{{ currentQueryTitle }}</span>
        <div class="view-selector">
          <a-radio-group v-model="activeViewId" type="button" size="small">
            <a-radio v-for="tab in viewTabs" :key="tab.key" :value="tab.viewId">
              {{ tab.viewName }}
              <icon-close v-if="tab.closable" class="tab-close-icon" @click.stop="handleCloseViewTab(tab.viewId)" />
            </a-radio>
          </a-radio-group>
          <a-dropdown trigger="click" @select="handleViewDropdown">
            <a-button type="text" size="small" class="add-view-trigger">
              <template #icon><icon-plus /></template>
            </a-button>
            <template #content>
              <a-doption value="add"><icon-plus /> 新建视图</a-doption>
              <a-doption value="manage"><icon-apps /> 管理视图</a-doption>
            </template>
          </a-dropdown>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="chat-container" ref="chatContainer">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.type">
          <div v-if="msg.type === 'user'" class="user-bubble">
            {{ msg.content }}
          </div>
          
          <div v-else class="agent-message">
            <!-- 分析过程 -->
            <QuerySteps
              v-if="msg.queryResult || msg.loading"
              :steps="msg.queryResult?.steps || loadingSteps"
            />

            <!-- 查询结果卡片 -->
            <a-card v-if="msg.queryResult?.result" class="result-card">
              <template #title>
                <div class="result-card-header">
                  <div class="result-info">
                    <span class="metrics-name">{{ getMetricsFromCols(msg.queryResult).join(', ') }}</span>
                  </div>
                  <div class="result-actions">
                    <a-space>
                      <a-button type="text" size="small" @click="handleQuote(msg.queryResult.mql, msg.queryResult.view_id)">
                        <template #icon><icon-share-alt /></template>
                        引用
                      </a-button>
                      <a-button type="text" size="small" @click="handleShowSql(msg.queryResult)">
                        <template #icon><icon-code /></template>
                        查看SQL
                      </a-button>
                      <a-button type="text" size="small" @click="showGlobalAddDimension(msg.queryResult)">
                        <template #icon><icon-plus-circle /></template>
                        维度细分
                      </a-button>
                      <a-button type="text" size="small" @click="showAdjustment(msg.queryResult)">
                        <template #icon><icon-settings /></template>
                        调整查询
                      </a-button>
                      <a-button type="text" size="small">
                        <template #icon><icon-download /></template>
                      </a-button>
                      <a-button 
                        :type="msg.queryResult.viewType === 'chart' ? 'primary' : 'outline'" 
                        size="small"
                        @click="msg.queryResult.viewType = 'chart'"
                        :style="msg.queryResult.viewType === 'chart' ? {} : { color: '#4e5969' }"
                      >
                        <template #icon><icon-mosaic /></template>
                        图表
                      </a-button>
                      <a-button 
                        :type="msg.queryResult.viewType !== 'chart' ? 'primary' : 'outline'" 
                        size="small"
                        @click="msg.queryResult.viewType = 'table'"
                        :style="msg.queryResult.viewType !== 'chart' ? {} : { color: '#4e5969' }"
                      >
                        <template #icon><icon-drive-file /></template>
                        表格
                      </a-button>
                    </a-space>
                  </div>
                </div>
              </template>

              <div class="result-body-container">
                <!-- 查询元信息面板 -->
                <div class="query-meta-panel">
                  <!-- 时间范围 -->
                  <div v-if="getParsedTimeRange(msg.queryResult.mql, msg.queryResult.query_id) || formatTimeRange(msg.queryResult.mql)" class="meta-row">
                    <div class="meta-label">
                      <icon-clock-circle />
                      <span>时间范围</span>
                    </div>
                    <div class="meta-content">
                      <template v-if="getParsedTimeRange(msg.queryResult.mql, msg.queryResult.query_id)">
                        <span class="time-range-box">
                          <span class="time-field-name-in-box">
                            {{ findDimension(extractTimeConditions(msg.queryResult.mql?.filters || {})[0]?.field || '')?.display_name || '时间' }}
                          </span>
                          <span class="time-date">{{ getParsedTimeRange(msg.queryResult.mql, msg.queryResult.query_id)?.start || '-' }}</span>
                          <span class="time-separator">~</span>
                          <span class="time-date">{{ getParsedTimeRange(msg.queryResult.mql, msg.queryResult.query_id)?.end || '-' }}</span>
                        </span>
                      </template>
                      <template v-else>
                        <span>{{ formatTimeRange(msg.queryResult.mql) }}</span>
                      </template>
                    </div>
                  </div>

                  <!-- 指标 -->
                  <div v-if="getMetricsFromCols(msg.queryResult).length > 0" class="meta-row">
                    <div class="meta-label">
                      <icon-bar-chart />
                      <span>指标</span>
                    </div>
                    <div class="meta-content">
                      <a-space size="small" wrap>
                        <a-popover v-for="col in getMetricsFromCols(msg.queryResult)" :key="col" position="bottom">
                          <span class="meta-tag-chip metric-chip">{{ findMetric(col)?.display_name || col }}</span>
                          <template #content>
                            <div class="metadata-popup">
                              <div v-if="findMetric(col)">
                                <div class="p-title">{{ findMetric(col)?.display_name || col }}</div>
                                <div class="p-desc">{{ findMetric(col)?.description || '暂无描述' }}</div>
                                <div class="p-formula">计算口径：{{ findMetric(col)?.calculation_formula || '基础聚合' }}</div>
                              </div>
                              <div v-else>未知指标</div>
                            </div>
                          </template>
                        </a-popover>
                      </a-space>
                    </div>
                  </div>

                  <!-- 维度 -->
                  <div v-if="getDimensionsFromCols(msg.queryResult).length > 0" class="meta-row">
                    <div class="meta-label">
                      <icon-apps />
                      <span>维度</span>
                    </div>
                    <div class="meta-content">
                      <a-space size="small" wrap>
                        <a-popover v-for="col in getDimensionsFromCols(msg.queryResult)" :key="col" position="bottom">
                          <span class="meta-tag-chip dimension-chip">
                            {{ col && col.includes('__') ? (findDimension(col.split('__')[0] || '')?.display_name || col.split('__')[0]) + '(' + (col.split('__')[1] || '') + ')' : (findDimension(col || '')?.display_name || col) }}
                          </span>
                          <template #content>
                            <div class="metadata-popup">
                              <div v-if="col && (findDimension(col) || (col.includes('__') && findDimension(col.split('__')[0] || '')))">
                                <div class="p-title">
                                  {{ col.includes('__') ? (findDimension(col.split('__')[0] || '')?.display_name || col.split('__')[0]) + '(' + (col.split('__')[1] || '') + ')' : (findDimension(col)?.display_name || col) }}
                                </div>
                                <div class="p-desc">{{ findDimension(col.split('__')[0] || '')?.description || '暂无描述' }}</div>
                              </div>
                              <div v-else>未知维度</div>
                            </div>
                          </template>
                        </a-popover>
                      </a-space>
                    </div>
                  </div>

                  <!-- 过滤条件 -->
                  <div v-if="hasFilters(msg.queryResult.mql.filters)" class="meta-row">
                    <div class="meta-label">
                      <icon-filter />
                      <span>过滤条件</span>
                    </div>
                    <div class="meta-content filter-content">
                      <FilterTree :node="normalizeFilters(msg.queryResult.mql.filters)" :format-field="formatDimensionName" />
                    </div>
                  </div>
                </div>

                <div class="result-content-wrapper">
                  <a-table
                    v-if="msg.queryResult.viewType !== 'chart'"
                    :columns="formatColumns(msg.queryResult.result.columns)"
                    :data="formatData(msg.queryResult.result, msg.queryResult.query_id)"
                    :pagination="false"
                    :bordered="false"
                    size="small"
                    :scroll="{ x: '100%', y: 400 }"
                    row-key="key"
                    :row-class-name="(record: any) => record.key === selectedRowKey ? 'arco-table-tr-checked' : ''"
                    @row-click="(record: any) => handleRowSelection(record, msg.queryResult!)"
                    @row-contextmenu="(record: any, ev: MouseEvent) => handleRowContextMenu(record, msg.queryResult!, ev)"
                  >
                    <template #actions="{ record }">
                      <a-dropdown @select="(val: any) => handleActionSelect(val, record, msg.queryResult!)">
                        <a-button type="text" size="small"><icon-more /></a-button>
                        <template #content>
                          <a-doption value="drill">
                            <template #icon><icon-layers /></template>
                            下钻分析
                          </a-doption>
                        </template>
                      </a-dropdown>
                    </template>
                  </a-table>

                  <ChartContainer
                    v-if="msg.queryResult.viewType === 'chart'"
                    :columns="msg.queryResult.result.columns"
                    :data="msg.queryResult.result.data"
                    :chart-type="(msg.queryResult.result.chart_recommendation as any) || 'bar'"
                  />
                </div>
              
              <div class="result-footer">
                <div class="footer-left">
                  <span class="timestamp">{{ msg.queryResult.query_id }}</span>
                  <span v-if="msg.queryResult.dataFormatConfigId" class="config-id">
                    API配置ID: {{ msg.queryResult.dataFormatConfigId }}
                  </span>
                </div>
                <div class="footer-right">
                  <a-button
                    v-if="!msg.queryResult.dataFormatConfigId"
                    type="primary"
                    size="small"
                    @click="handleGenerateApi(msg.queryResult)"
                  >
                    <template #icon><icon-thunderbolt /></template>
                    生成API
                  </a-button>
                  <a-button
                    v-else
                    type="outline"
                    size="small"
                    @click="openApiDebug(msg.queryResult.dataFormatConfigId!)"
                  >
                    <template #icon><icon-code /></template>
                    API调试
                  </a-button>
                </div>
              </div>

              <!-- 洞察展示面板 -->
              <div v-if="msg.queryResult?.insights?.length > 0" class="insights-panel">
                <div class="insights-header" @click="insightsExpanded = !insightsExpanded">
                  <div class="insights-title">
                    <icon-light /> 洞察分析
                    <a-badge v-if="msg.queryResult?.insights?.length > 0" :count="msg.queryResult?.insights?.length" :max-count="99" />
                  </div>
                  <a-button type="text" size="mini">
                    <template #icon>
                      <icon-down v-if="!insightsExpanded" />
                      <icon-up v-else />
                    </template>
                  </a-button>
                </div>
                <div v-show="insightsExpanded" class="insights-content">
                  <div
                    v-for="(insight, idx) in msg.queryResult?.insights"
                    :key="idx"
                    class="insight-item"
                  >
                    <div class="insight-index">{{ idx + 1 }}</div>
                    <div class="insight-text">{{ insight }}</div>
                  </div>
                </div>
              </div>
            </div>
          </a-card>
          </div>
        </div>
      </div>

      <!-- 底部输入框 -->
      <div class="input-container">
        <!-- 引用上下文显示区域 -->
        <div v-if="quotedMql" class="quoted-mql-box">
          <div class="quoted-header">
            <span class="quoted-label"><icon-share-alt /> 正在引用上下文进行分析</span>
            <a-button type="text" size="mini" @click="quotedMql = null">
              <template #icon><icon-close /></template>
              取消引用
            </a-button>
          </div>
          <div class="quoted-content">
            <a-tag v-for="m in quotedMql.metrics" :key="m" color="arcoblue" size="small">{{ m }}</a-tag>
            <a-tag v-for="d in quotedMql.dimensions" :key="d" color="green" size="small">{{ d }}</a-tag>
            <span v-if="quotedMql.timeConstraint && quotedMql.timeConstraint !== 'true'" class="quoted-time">
              {{ formatTimeRange(quotedMql) }}
            </span>
          </div>
        </div>

        <div class="input-wrapper">
          <a-textarea
            v-model="queryInput"
            placeholder="输入问题"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            @keydown.enter.prevent="handleEnter"
            class="query-input"
          />
          <div class="input-footer">
            <span class="input-hint">Agent测试服务生成的所有内容均由人工智能模型生成，请谨慎识别数据准确性。</span>
            <a-space>
              <a-button 
                type="outline"
                size="small"
                @click="showDataFormatConfig"
                title="配置输出格式"
              >
                <template #icon><icon-settings /></template>
                格式
              </a-button>
              <a-button 
                type="primary" 
                shape="circle" 
                :loading="loading" 
                @click="handleQuery"
                class="send-btn"
              >
                <template #icon><icon-send /></template>
              </a-button>
            </a-space>
          </div>
        </div>
      </div>
    </template>

    <!-- SQL查看弹窗 -->
    <a-modal v-model:visible="sqlViewVisible" title="查看SQL" width="1000px" height="600px" :footer="false" :body-style="{ maxHeight: '600px', overflow: 'auto' }">
      <div class="sql-view-container">
        <div class="sql-toolbar">
          <a-button type="primary" size="small" @click="copySqlToClipboard">
            <template #icon><icon-copy /></template>
            复制SQL
          </a-button>
        </div>
        <a-textarea
          v-model="currentViewingSql"
          readonly
          auto-height
          class="sql-textarea"
          placeholder="暂无SQL"
        />
      </div>
    </a-modal>

    <!-- 调整查询弹窗 -->
    <a-modal v-model:visible="adjustmentVisible" title="调整查询" @ok="handleAdjust" width="600px">
      <a-form :model="adjustmentForm" layout="vertical">
        <a-form-item label="已选指标">
          <a-select v-model="adjustmentForm.metrics" multiple placeholder="请选择指标">
            <a-option v-for="m in adjustmentMetadata.metrics" :key="m.id" :value="m.name">{{ m.display_name || m.name }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分析维度">
          <a-select v-model="adjustmentForm.dimensions" multiple placeholder="请选择分析维度">
            <a-option v-for="d in adjustmentMetadata.dimensions" :key="d.id" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="过滤条件">
          <FilterEditor ref="filterEditorRef" v-model="adjustmentForm.filterGroups" :dimensions="adjustmentMetadata.dimensions" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 添加分析维度弹窗 (全局) -->
    <a-modal v-model:visible="addDimensionVisible" title="添加分析维度 (全局)" @ok="handleAddDimension" width="480px">
      <div class="drill-down-context">
        <div class="context-title">
          <icon-layers style="margin-right: 4px; color: var(--color-success-light-4)" />
          当前已有维度：
        </div>
        <div class="current-dims-display global-mode">
          <a-tag v-for="dim in activeQueryResult?.mql?.dimensions" :key="dim" color="green" size="small" style="margin-right: 6px; margin-bottom: 6px;">
            {{ formatDimensionName(dim) }}
          </a-tag>
        </div>
        <div class="context-tip">在当前查询的基础上增加新的分析维度。</div>
      </div>
      <a-divider />
      <a-form :model="addDimensionForm" layout="vertical">
        <a-form-item label="选择要增加的维度" required>
          <a-select v-model="addDimensionForm.dimensions" multiple allow-clear placeholder="支持选择多个维度" :max-tag-count="3">
            <a-option v-for="d in addDimensionAvailableDimensions" :key="d.id" :value="d.value">
              {{ d.label }}
            </a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 下钻分析弹窗 (锁定行数据) -->
    <a-modal v-model:visible="drillDownVisible" title="下钻分析 (锁定行数据)" @ok="handleDrillDown" width="480px">
      <div v-if="selectedRecord" class="drill-down-context">
        <div class="context-title">
          <icon-filter style="margin-right: 4px; color: var(--color-primary-light-4)" />
          下钻范围：
        </div>
        <div class="current-dims-display drill-mode">
          <a-tag v-for="dim in activeQueryResult?.mql?.dimensions" :key="dim" color="arcoblue" size="small" style="margin-right: 6px; margin-bottom: 6px;">
            <span class="tag-label">{{ formatDimensionName(dim) }}:</span>
            <span class="tag-value">{{ selectedRecord[dim] }}</span>
          </a-tag>
        </div>
        <div class="context-tip">系统将自动锁定上述条件，并展示更细粒度的数据。</div>
      </div>
      <a-divider />
      <a-form :model="drillDownForm" layout="vertical">
        <a-form-item label="选择下钻目标维度" required>
          <a-select v-model="drillDownForm.dimensions" multiple allow-clear placeholder="支持选择多个维度" :max-tag-count="3">
            <a-option v-for="d in drillDownAvailableDimensions" :key="d.id" :value="d.value">
              {{ d.label }}
            </a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 数据格式配置弹窗 -->
    <DataFormatConfigModal
      v-model:visible="dataFormatConfigVisible"
      :initial-config="dataFormatConfig"
      :filterable-fields="apiFilterableFields"
      @save="handleDataFormatSave"
    />

    <!-- API 调试弹窗 -->
    <ApiDebugModal
      v-model:visible="apiDebugVisible"
      :config-id="apiDebugConfigId"
    />

    <!-- 视图选择弹窗 -->
    <a-modal 
      v-model:visible="showViewSelectModal"
      title="选择视图"
      @cancel="showViewSelectModal = false"
      :footer="false"
      width="500px"
    >
      <div class="view-select-list">
        <a-list :bordered="false">
          <a-list-item 
            v-for="view in allViews" 
            :key="view.id"
            class="view-select-item"
            @click="handleViewSelect(view)"
          >
            <a-list-item-meta :title="view.display_name || view.name" :description="view.description || '暂无描述'" />
          </a-list-item>
        </a-list>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, watch, toRaw, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Dropdown, Doption } from '@arco-design/web-vue'
import { 
  IconLayers, 
  IconSettings, 
  IconMore, 
  IconDriveFile, 
  IconShareAlt, 
  IconPlusCircle,
  IconDownload,
  IconMosaic,
  IconClose,
  IconSend,
  IconDelete,
  IconPlus,
  IconFilter,
  IconThunderbolt,
  IconFile,
  IconCode,
  IconApps
} from '@arco-design/web-vue/es/icon'
import { useSettingsStore } from '@/stores/settings'
import ModelNotConfigured from '@/components/query/ModelNotConfigured.vue'
import QuerySteps from '@/components/query/QuerySteps.vue'
import ChartContainer from '@/components/common/ChartContainer.vue'
import DataFormatConfigModal from '@/components/query/DataFormatConfigModal.vue'
import ApiDebugModal from '@/components/query/ApiDebugModal.vue'
import type { FullQueryResponse, AnalysisStep } from '@/api/types'
import { analyzeIntent, generateMQL, mql2sql, executeSQL, getQueryHistoryDetail, startConversation, getConversationHistory, saveConversationHistory, parseTimeRanges } from '@/api/query'
import { getMetrics, getDimensions, getMetricsAllowedDimensions } from '@/api/semantic'
import { getSystemSetting } from '@/api/settings'
import { generateDataFormatConfig } from '@/api/data_format'
import { getViews, getDefaultView, getFilterableFields } from '@/api/views'
import type { Metric, Dimension } from '@/api/types'
import type { MQLFilterCondition, MQLFilterGroup } from '@/api/types'
import FilterTree from '@/components/FilterTree.vue'
import FilterEditor from '@/components/FilterEditor.vue'
import type { FeGroup, FeCondition, FeSubGroup } from '@/components/FilterEditor.vue'
import type { View, FilterableField } from '@/api/views'

const settingsStore = useSettingsStore()
const route = useRoute()
const router = useRouter()

const queryInput = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const currentQueryTitle = ref('问数对话')
const conversationId = ref<string | null>(null)  // 当前对话ID

// 数据格式配置弹窗
const dataFormatConfigVisible = ref(false)
const dataFormatConfig = ref<{
  targetFormat: any
  apiParameters: string[]
} | undefined>(undefined)

// API 调试弹窗
const apiDebugVisible = ref(false)
const apiDebugConfigId = ref<string>('')

interface MessageItem {
  type: 'user' | 'agent'
  content?: string
  queryResult?: FullQueryResponse
  loading?: boolean
  error?: boolean
}

const messages = ref<MessageItem[]>([])
const allMetrics = ref<Metric[]>([])
const allDimensions = ref<Dimension[]>([])
const allowedDimensions = ref<Dimension[]>([])  // 当前查询允许的维度

// 视图标签页相关
interface ViewTab {
  key: string
  viewId: string
  viewName: string
  baseTableId?: string
  closable: boolean
}

const viewTabs = ref<ViewTab[]>([])
const activeViewId = ref<string>('')
const allViews = ref<View[]>([])
const showViewSelectModal = ref(false)
const timeFormats = ref<any[]>([])
const quotedMql = ref<any>(null)
const quotedViewId = ref<string | null>(null)  // 引用时绑定的视图ID
const selectedRecord = ref<any>(null)
const activeQueryResult = ref<FullQueryResponse | null>(null)
const selectedRowKey = ref<string | null>(null) // 当前选中的行 key (全局唯一)

// 视图元数据缓存
const viewMetadataCache = ref<Record<string, { metrics: Metric[], dimensions: Dimension[] }>>({})

// 获取视图的元数据（优先使用缓存）
async function getViewMetadata(viewId: string): Promise<{ metrics: Metric[], dimensions: Dimension[] }> {
  if (viewMetadataCache.value[viewId]) {
    return viewMetadataCache.value[viewId]
  }
  
  const viewTab = viewTabs.value.find(t => t.viewId === viewId)
  const baseTableId = viewTab?.baseTableId
  
  const [metrics, dimensions] = await Promise.all([
    getMetrics(baseTableId ? { dataset_id: baseTableId } : {}),
    getDimensions(baseTableId ? { dataset_id: baseTableId } : (viewId ? { view_id: viewId } : {}))
  ])
  
  const result = { metrics, dimensions }
  viewMetadataCache.value[viewId] = result
  return result
}

const drillDownVisible = ref(false)
const addDimensionVisible = ref(false)
const drillDownForm = reactive({
  dimensions: [] as string[]
})
const addDimensionForm = reactive({
  dimensions: [] as string[]
})

const adjustmentVisible = ref(false)

// SQL 查看
const sqlViewVisible = ref(false)
const currentViewingSql = ref('')

// 洞察展示
const insightsExpanded = ref(false)

// 解析后的时间范围缓存 {queryId: {field: {start: '', end: '', data_type: ''}}}
const parsedTimeRanges = ref<Record<string, Record<string, { start: string; end: string; data_type: string }>>>({})


const filterEditorRef = ref<{ getRootOperator: () => string } | null>(null)
const adjustmentForm = ref<{
  metrics: string[],
  dimensions: string[],
  filters: FeCondition[]
  filterGroups: FeGroup[]
}>({
  metrics: [],
  dimensions: [],
  filters: [],
  filterGroups: [{ operator: 'AND' as const, items: [{ type: 'condition' as const, field: '', op: '=', value: '' }] }]
})

// 调整弹窗专用的元数据（使用结果绑定的视图）
const adjustmentMetadata = ref<{
  metrics: Metric[],
  dimensions: Dimension[]
}>({ metrics: [], dimensions: [] })

// 生成API弹窗的可过滤字段（使用结果绑定的视图的维度）
const apiFilterableFields = computed(() => {
  if (!activeQueryResult.value) return []
  const viewId = activeQueryResult.value.view_id || activeViewId.value
  if (!viewId) return []
  return filterableFieldsCache.value[viewId] || []
})

// 可过滤字段缓存
const filterableFieldsCache = ref<Record<string, FilterableField[]>>({})

// 加载视图可过滤字段
async function loadFilterableFields(viewId: string) {
  if (filterableFieldsCache.value[viewId]) {
    return
  }
  try {
    const response = await getFilterableFields(viewId)
    filterableFieldsCache.value[viewId] = response.fields || []
  } catch (e) {
    console.error('Failed to load filterable fields:', e)
    filterableFieldsCache.value[viewId] = []
  }
}

const addDimensionAvailableDimensions = computed(() => {
  if (!activeQueryResult.value) return []
  
  const presentDims = new Set<string>()
  
  activeQueryResult.value.mql?.dimensions?.forEach((d: string) => {
    if (d) {
      presentDims.add(d)
      if (d.includes('__')) {
        const base = d.split('__')[0]
        if (base) presentDims.add(base)
      }
    }
  })
  
  const results: { id: string, label: string, value: string }[] = []
  
  // 使用约束维度列表
  const dimensionList = allowedDimensions.value.length > 0 ? allowedDimensions.value : allDimensions.value
  
  dimensionList.forEach(d => {
    const isTime = d.dimension_type === 'time' || ['date', 'datetime', 'timestamp'].includes(d.data_type?.toLowerCase() || '')
    
    if (isTime && timeFormats.value.length > 0) {
      const options = d.format_config?.options || []
      timeFormats.value.forEach(fmt => {
        if (options.length === 0 || options.includes(fmt.name)) {
          const virtualName = `${d.display_name || d.name}__${fmt.label}`
          if (!presentDims.has(virtualName)) {
            results.push({
              id: `${d.id}_${fmt.suffix}`,
              label: `${d.display_name || d.name}(${fmt.label})`,
              value: virtualName
            })
          }
        }
      })
    } else {
      const dimName = d.display_name || d.name
      if (!presentDims.has(dimName) && !presentDims.has(d.name)) {
        results.push({
          id: d.id,
          label: d.display_name || d.name,
          value: dimName
        })
      }
    }
  })
  
  return results
})

const drillDownAvailableDimensions = computed(() => {
  if (!activeQueryResult.value) return []
  
  const results: { id: string, label: string, value: string }[] = []
  
  // 使用约束维度列表
  const dimensionList = allowedDimensions.value.length > 0 ? allowedDimensions.value : allDimensions.value
  
  dimensionList.forEach(d => {
    const isTime = d.dimension_type === 'time' || ['date', 'datetime', 'timestamp'].includes(d.data_type?.toLowerCase() || '')
    
    if (isTime && timeFormats.value.length > 0) {
      const options = d.format_config?.options || []
      timeFormats.value.forEach(fmt => {
        if (options.length === 0 || options.includes(fmt.name)) {
          const virtualName = `${d.display_name || d.name}__${fmt.label}`
          results.push({
            id: `${d.id}_${fmt.suffix}`,
            label: `${d.display_name || d.name}(${fmt.label})`,
            value: virtualName
          })
        }
      })
    } else {
      const dimName = d.display_name || d.name
      results.push({
        id: d.id,
        label: d.display_name || d.name,
        value: dimName
      })
    }
  })
  
  return results
})

function formatDimensionName(dim: string) {
  if (!dim) return ''
  if (dim.includes('__')) {
    const parts = dim.split('__')
    const base = parts[0]
    const suffix = parts[1]
    const d = findDimension(base || '')
    return `${d?.display_name || base}(${suffix})`
  }
  const d = findDimension(dim)
  return d?.display_name || dim
}

function formatFilterDisplay(filterStr: string) {
  if (!filterStr) return ''
  // Try to replace [field] with Display Name
  const match = filterStr.match(/\[(.*?)\]\s*(.*)/)
  if (match) {
    const field = match[1]
    const rest = match[2]
    return `${formatDimensionName(field || '')} ${rest}`
  }
  return filterStr
}

// 判断 filters 是否有内容
function hasFilters(filters: any): boolean {
  if (!filters) return false
  if (Array.isArray(filters)) return filters.length > 0
  if (typeof filters === 'object') return (filters as MQLFilterGroup).conditions?.length > 0
  return false
}

// 将结构化 filters 扁平化为叶子条件数组
function flattenFilters(filters: any): MQLFilterCondition[] {
  if (!filters) return []
  if (Array.isArray(filters)) {
    return filters.map((f: string) => {
      const parts = f.split(' ')
      return { field: parts[0]?.replace(/[\[\]]/g, '') || '', op: parts[1] || '=', value: parts[2]?.replace(/'/g, '') || '' }
    })
  }
  const result: MQLFilterCondition[] = []
  function walk(node: any) {
    if (node.field !== undefined) {
      result.push({ field: node.field, op: node.op || '=', value: node.value })
    } else if (node.conditions) {
      node.conditions.forEach(walk)
    }
  }
  walk(filters)
  return result
}

// 格式化单个叶子条件展示
function formatFilterConditionDisplay(cond: MQLFilterCondition): string {
  if (!cond || !cond.field) return ''
  return `${formatDimensionName(cond.field)} ${cond.op} ${cond.value}`
}

// 将 filters 标准化为 MQLFilterGroup，兼容旧字符串数组格式
function normalizeFilters(filters: any): MQLFilterGroup {
  if (!filters) return { operator: 'AND', conditions: [] }
  if (typeof filters === 'object' && filters.conditions) return filters as MQLFilterGroup
  if (Array.isArray(filters)) {
    return {
      operator: 'AND',
      conditions: filters.map((f: any) =>
        typeof f === 'string'
          ? { field: f.split(/[\s=<>!]+/)[0]?.replace(/[\[\]]/g, '') || '', op: '=', value: f.replace(/.*?[<>!=]+\s*/, '').replace(/'/g, '') || '' }
          : f
      )
    }
  }
  return { operator: 'AND', conditions: [] }
}

function getSelectedRowValues() {
  if (!selectedRecord.value || !activeQueryResult.value) return ''
  const dims = activeQueryResult.value.mql?.dimensions || []
  return dims.map((d: string) => selectedRecord.value[d]).join(', ')
}

async function handleAddDimension() {
  if (addDimensionForm.dimensions.length === 0) {
    Message.warning('请选择至少一个分析维度')
    return
  }
  
  if (!activeQueryResult.value || !activeQueryResult.value.mql) {
    Message.error('当前查询上下文已失效，请尝试重新提问')
    return
  }
  
  const mql = JSON.parse(JSON.stringify(activeQueryResult.value.mql))
  const drillDims = [...addDimensionForm.dimensions]
  
  if (!mql.dimensions) mql.dimensions = []
  drillDims.forEach(d => {
    if (!mql.dimensions.includes(d)) {
      mql.dimensions.push(d)
    }
  })
  
  addDimensionVisible.value = false
  loading.value = true
  
  try {
    Message.info('正在扩展分析维度...')
    const sqlRes = await mql2sql(mql)
    const queryRes = await executeSQL({ 
      sql: sqlRes.sql, 
      datasource_id: sqlRes.datasources[0] || ''
    })
    
    const agentMsg: MessageItem = { 
      type: 'agent', 
      queryResult: {
        natural_language: `扩展查询: ${drillDims.join(', ')}`,
        mql: mql,
        sql: sqlRes.sql,
        viewType: 'table',
        steps: [
          { 
            title: '维度扩展', 
            content: `已在当前查询基础上追加了维度 [${drillDims.join(', ')}]。`, 
            status: 'success' 
          }
        ],
        result: queryRes,
        query_id: 'add_dim_' + Date.now()
      }
    }
    messages.value.push(agentMsg)
    Message.success('分析已更新')

    // 解析时间范围
    if (agentMsg.queryResult?.mql && agentMsg.queryResult?.query_id) {
      fetchAndParseTimeRanges(agentMsg.queryResult.mql, agentMsg.queryResult.query_id)
    }

    // 保存完整的对话历史
    if (conversationId.value) {
      try {
        await saveConversationHistory(conversationId.value, messages.value.map(msg => ({
          type: msg.type,
          content: msg.content,
          queryResult: msg.queryResult
        })))
      } catch (e) {
        console.error('保存对话历史失败:', e)
      }
    }
  } catch (error: any) {
    console.error('Add dimension execution failed:', error)
    Message.error(error.message || '扩展维度失败')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function handleDrillDown() {
  if (drillDownForm.dimensions.length === 0) {
    Message.warning('请选择至少一个下钻目标维度')
    return
  }
  
  if (!activeQueryResult.value || !activeQueryResult.value.mql || !selectedRecord.value) {
    Message.error('下钻上下文丢失，请重新选择数据行')
    return
  }
  
  const mql = JSON.parse(JSON.stringify(activeQueryResult.value.mql))
  const record = toRaw(selectedRecord.value)
  const drillDims = [...drillDownForm.dimensions]
  
  if (!mql.filters || (typeof mql.filters === 'object' && !Array.isArray(mql.filters) && !(mql.filters as MQLFilterGroup).conditions)) {
    mql.filters = { operator: 'AND', conditions: [] }
  }

  // --- 下钻分析核心逻辑：维度替换 + 过滤锁定 ---
  // 获取当前查询的所有维度
  const currentDims = [...(mql.dimensions || [])]
  
  const conditions = (mql.filters as MQLFilterGroup).conditions || []
  currentDims.forEach((dim: string) => {
    // 获取该维度在行数据中的值
    const val = record[dim]
    
    if (val !== undefined && val !== null && val !== '') {
      // 避免重复添加相同的过滤条件
      const exists = conditions.some((c: any) => c.field === dim && c.value === String(val))
      if (!exists) {
        conditions.push({ field: dim, op: '=', value: String(val) })
      }
    }
  })
  
  // 执行维度替换：将当前维度替换为用户选择的下钻目标维度
  mql.dimensions = drillDims
  
  // 如果下钻目标中包含当前正在过滤的维度，且粒度更细，后端会自动处理
  // 这里我们只需要保证 MQL 结构正确
  
  drillDownVisible.value = false
  loading.value = true
  
  try {
    Message.info('正在执行下钻分析...')
    const sqlRes = await mql2sql(mql)
    const queryRes = await executeSQL({ 
      sql: sqlRes.sql, 
      datasource_id: sqlRes.datasources[0] || ''
    })
    
    // 构建新的回复消息
    const analysisTitle = `下钻分析: ${drillDims.map(d => formatDimensionName(d)).join(', ')}`
    const agentMsg: MessageItem = { 
      type: 'agent', 
      queryResult: {
        natural_language: analysisTitle,
        mql: mql,
        sql: sqlRes.sql,
        viewType: 'table',
        steps: [
          { 
            title: '下钻分析执行', 
            content: `已对选定数据行执行锁定，并深入分析维度：${drillDims.map(d => formatDimensionName(d)).join(', ')}。`, 
            status: 'success' 
          }
        ],
        result: queryRes,
        query_id: 'drill_' + Date.now()
      }
    }
    messages.value.push(agentMsg)
    Message.success('分析已完成')

    // 解析时间范围
    if (agentMsg.queryResult?.mql && agentMsg.queryResult?.query_id) {
      fetchAndParseTimeRanges(agentMsg.queryResult.mql, agentMsg.queryResult.query_id)
    }

    // 保存完整的对话历史
    if (conversationId.value) {
      try {
        await saveConversationHistory(conversationId.value, messages.value.map(msg => ({
          type: msg.type,
          content: msg.content,
          queryResult: msg.queryResult
        })))
      } catch (e) {
        console.error('保存对话历史失败:', e)
      }
    }
  } catch (error: any) {
    console.error('Drill down execution failed:', error)
    Message.error(error.message || '执行下钻分析失败')
  } finally {
    loading.value = false
    scrollToBottom()
    // 不要在 finally 中立即清除 selectedRecord，防止用户连续操作时丢失上下文
  }
}

// 开始新的对话
async function startNewConversation() {
  try {
    const response = await startConversation()
    conversationId.value = response.conversation_id
    messages.value = []  // 清空消息列表
    currentQueryTitle.value = '新对话'
  } catch (error) {
    console.error('Failed to start new conversation:', error)
    Message.error('无法开始新对话')
  }
}

// 加载对话历史记录
async function loadConversationHistory(convId: string) {
  loading.value = true
  try {
    // 尝试按对话ID加载（新格式）
    let detail;
    try {
      detail = await getConversationHistory(convId);
    } catch (conversationError) {
      // 如果按对话ID找不到，尝试按记录ID加载（传统格式）
      detail = await getQueryHistoryDetail(convId);
      
      // 将传统格式转换为新格式
      const agentMsg: MessageItem = { 
        type: 'agent', 
        queryResult: {
          natural_language: detail.natural_language,
          mql: detail.mql_query || {},
          sql: detail.sql_query || '',
          viewType: 'table',
          steps: [{ title: '历史记录恢复', content: '已从历史记录中恢复此对话。', status: 'success' }],
          result: { 
            columns: [], 
            data: [], 
            total_count: detail.result_count || 0, 
            execution_time: detail.execution_time || 0 
          },
          query_id: detail.id
        } 
      }
      messages.value = [
        { type: 'user', content: detail.natural_language },
        agentMsg
      ];
      
      // 设置当前对话ID
      // 如果没有 conversation_id，使用记录ID作为对话ID（保持兼容性）
      console.log('[History] 加载传统格式历史, detail.id:', detail.id, 'detail.conversation_id:', detail.conversation_id)
      conversationId.value = detail.conversation_id || detail.id || null;
      console.log('[History] 设置 conversationId.value:', conversationId.value)
      return;
    }
    
    currentQueryTitle.value = detail.natural_language?.slice(0, 15) || '历史对话'
    
    // 如果有完整的消息历史，直接使用
    if (detail.messages && Array.isArray(detail.messages)) {
      messages.value = detail.messages.map((msg: any) => ({
        type: msg.type,
        content: msg.content,
        queryResult: msg.queryResult
      }))
      
      // 检查是否有需要重新执行的查询
      // 从后往前查找最后一个agent消息
      const lastAgentMsg = [...messages.value].reverse().find((msg: any) => msg.type === 'agent' && msg.queryResult);
      if (lastAgentMsg && lastAgentMsg.queryResult) {
        const qr = lastAgentMsg.queryResult;
        if (qr.sql && qr.mql) {  // 无论结果是否为空，都重新执行以获取最新数据
          try {
            Message.info('正在重新执行历史查询以获取最新数据...')
            // 通过mql2sql API获取数据源信息
            let datasource_id = '';
            try {
              const sqlRes = await mql2sql(qr.mql);
              datasource_id = sqlRes.datasources?.[0] || '';
            } catch (mqlError) {
              console.error('mql2sql调用失败:', mqlError);
              datasource_id = 'default';
            }
            
            if (qr.sql && datasource_id) {
              try {
                const queryRes = await executeSQL({ 
                  sql: qr.sql, 
                  datasource_id: datasource_id
                });
                qr.result = queryRes;
              } catch (executeError) {
                console.error('executeSQL调用失败:', executeError);
                throw executeError;
              }
              
              // 确保steps数组存在
              if (!qr.steps) qr.steps = [];
              qr.steps.push({
                title: '查询重新执行', 
                content: `成功重新执行查询，获取到 ${qr.result.total_count} 条记录`, 
                status: 'success'
              })
            }
          } catch (e) {
            console.error('Failed to reload historical data:', e)
            Message.warning('无法重新执行历史查询，仅显示历史概要信息')
            
            // 确保steps数组存在
            if (!qr.steps) qr.steps = [];
            qr.steps.push({
              title: '查询重新执行', 
              content: '由于数据源或权限变更，无法重新执行查询', 
              status: 'error'
            })
          }
        }
      }
    } else {
      // 兼容旧的历史记录格式
      const agentMsg: MessageItem = { 
        type: 'agent', 
        queryResult: {
          natural_language: detail.natural_language,
          mql: detail.mql_query || {},
          sql: detail.sql_query || '',
          viewType: 'table',
          steps: [
            { title: '历史记录恢复', content: '已从历史记录中恢复此对话。', status: 'success' }
          ],
          result: { 
            columns: [], 
            data: [], 
            total_count: detail.result_count || 0, 
            execution_time: detail.execution_time || 0 
          },
          query_id: detail.id
        } 
      }
      messages.value = [
        { type: 'user', content: detail.natural_language },
        agentMsg
      ]
      
      // 如果历史记录状态为成功且有结果数量，尝试重新执行查询获取最新数据
      if (detail.status === 'success' && detail.result_count > 0 && detail.sql_query && agentMsg.queryResult) {
        try {
          Message.info('正在重新执行历史查询以获取最新数据...')
          // 尝试获取一个可用的数据源ID，或者后端mql2sql重新解析一次以获取数据源
          const sqlRes = await mql2sql(detail.mql_query)
          const datasource_id = sqlRes.datasources[0] || ''
          
          const queryRes = await executeSQL({ 
            sql: detail.sql_query, 
            datasource_id: datasource_id
          })
          agentMsg.queryResult.result = queryRes
          
          // 更新步骤信息以反映重新执行
          agentMsg.queryResult.steps.push({
            title: '查询重新执行', 
            content: `成功重新执行查询，获取到 ${queryRes.total_count} 条记录`, 
            status: 'success'
          })
        } catch (e) {
          console.error('Failed to reload historical data:', e)
          Message.warning('无法重新执行历史查询，仅显示历史概要信息')
          
          // 即使执行失败，也要更新步骤信息
          agentMsg.queryResult.steps.push({
            title: '查询重新执行', 
            content: '由于数据源或权限变更，无法重新执行查询', 
            status: 'error'
          })
        }
      } else if (detail.status === 'failed' && agentMsg.queryResult) {
        // 如果历史记录本身是失败的，显示失败信息
        agentMsg.queryResult.steps.push({
          title: '查询状态', 
          content: `查询曾失败: ${detail.error_message || '未知错误'}`, 
          status: 'error'
        })
      }
    }
    
    // 设置当前对话ID
    // 如果没有 conversation_id，使用记录ID作为对话ID（保持兼容性）
    console.log('[History] 加载历史记录, detail.id:', detail.id, 'detail.conversation_id:', detail.conversation_id)
    conversationId.value = detail.conversation_id || detail.id
    console.log('[History] 设置 conversationId.value:', conversationId.value)

    // 为所有消息解析时间范围
    nextTick(() => {
      for (const msg of messages.value) {
        if (msg.type === 'agent' && msg.queryResult?.mql && msg.queryResult?.query_id) {
          fetchAndParseTimeRanges(msg.queryResult.mql, msg.queryResult.query_id)
        }
      }
    })

  } catch (error) {
    console.error('Load conversation history error:', error)
    Message.error('加载对话历史失败')
    // 如果加载失败，开始新对话
    await startNewConversation()
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// 引用功能：将 MQL 作为上下文
function handleQuote(mql: any, viewId?: string) {
  quotedMql.value = JSON.parse(JSON.stringify(mql))
  quotedViewId.value = viewId || null
  queryInput.value = '' // 清空输入框，引导用户输入增量指令
  Message.success('已加载引用上下文，请输入您的调整或分析要求')
  
  nextTick(() => {
    const input = document.querySelector('.query-input textarea') as HTMLTextAreaElement
    if (input) input.focus()
  })
}

// 查看 SQL
function handleShowSql(queryResult: any) {
  currentViewingSql.value = queryResult.sql || ''
  sqlViewVisible.value = true
}

// 复制SQL到剪贴板
async function copySqlToClipboard() {
  try {
    await navigator.clipboard.writeText(currentViewingSql.value)
    Message.success('SQL已复制到剪贴板')
  } catch (e) {
    // fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = currentViewingSql.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    Message.success('SQL已复制到剪贴板')
  }
}

// 初始化视图标签
async function initViews() {
  try {
    allViews.value = await getViews()
    const defaultView = await getDefaultView()
    
    if (defaultView) {
      viewTabs.value.push({
        key: defaultView.id,
        viewId: defaultView.id,
        viewName: defaultView.display_name || defaultView.name,
        baseTableId: defaultView.base_table_id,
        closable: false
      })
      activeViewId.value = defaultView.id
    } else if (allViews.value.length > 0) {
      const firstView = allViews.value[0]
      if (firstView) {
        viewTabs.value.push({
          key: firstView.id,
          viewId: firstView.id,
          viewName: firstView.display_name || firstView.name,
          baseTableId: firstView.base_table_id,
          closable: false
        })
        activeViewId.value = firstView.id
      }
    }
  } catch (e) {
    console.error('Failed to load views:', e)
    Message.error('加载视图列表失败')
  }
}

// 添加视图标签
function handleAddViewTab() {
  showViewSelectModal.value = true
}

// 处理视图下拉菜单
function handleViewDropdown(key: string) {
  if (key === 'add') {
    showViewSelectModal.value = true
  } else if (key === 'manage') {
    router.push('/semantic/views')
  }
}

// 选择视图后添加标签
function handleViewSelect(view: View) {
  // 检查是否已存在
  if (viewTabs.value.some(t => t.viewId === view.id)) {
    activeViewId.value = view.id
    showViewSelectModal.value = false
    return
  }
  
  // 添加新标签
  viewTabs.value.push({
    key: view.id,
    viewId: view.id,
    viewName: view.display_name || view.name,
    baseTableId: view.base_table_id,
    closable: true
  })
  activeViewId.value = view.id
  showViewSelectModal.value = false
}

// 关闭标签
function handleCloseViewTab(key: string) {
  const index = viewTabs.value.findIndex(t => t.key === key)
  if (index === -1) return
  
  const closedViewId = viewTabs.value[index]?.viewId
  viewTabs.value.splice(index, 1)
  
  // 如果关闭的是当前活动标签，切换到相邻标签
  if (activeViewId.value === closedViewId) {
    const nextTab = viewTabs.value[Math.min(index, viewTabs.value.length - 1)]
    if (nextTab) {
      activeViewId.value = nextTab.viewId
    } else {
      activeViewId.value = ''
    }
  }
}

// 切换标签
function handleViewTabChange(key: string) {
  activeViewId.value = key
}

function getMetricsFromMql(mql: any) {
  return mql?.metrics || []
}

// 监听路由参数变化（加载历史或新建）
watch(() => route.query.id, async (newId) => {
  if (newId) {
    await loadConversationHistory(newId as string)
  } else {
    await startNewConversation()
  }
})

// 监听新建对话的时间戳
watch(() => route.query.t, async () => {
  if (!route.query.id) {
    await startNewConversation()
  }
})

function clearSession() {
  messages.value = []
  currentQueryTitle.value = '新对话'
}

async function loadHistorySession(id: string) {
  loading.value = true
  try {
    const detail = await getQueryHistoryDetail(id)
    currentQueryTitle.value = detail.natural_language.slice(0, 15)
    
    // 恢复对话展示
    const agentMsg: MessageItem = { 
      type: 'agent', 
      queryResult: {
        natural_language: detail.natural_language,
        mql: detail.mql_query || {},
        sql: detail.sql_query || '',
        viewType: 'table',
        steps: [
          { title: '历史记录恢复', content: '已从历史记录中恢复此对话。', status: 'success' }
        ],
        result: { 
          columns: [], 
          data: [], 
          total_count: detail.result_count || 0, 
          execution_time: detail.execution_time || 0 
        },
        query_id: detail.id
      } 
    }
    messages.value = [
      { type: 'user', content: detail.natural_language },
      agentMsg
    ]
    
    // 如果历史记录状态为成功且有结果数量，尝试重新执行查询获取最新数据
    if (detail.status === 'success' && detail.result_count > 0 && detail.sql_query && agentMsg.queryResult) {
      try {
        Message.info('正在重新执行历史查询以获取最新数据...')
        // 尝试获取一个可用的数据源ID，或者后端mql2sql重新解析一次以获取数据源
        const sqlRes = await mql2sql(detail.mql_query)
        const datasource_id = sqlRes.datasources[0] || ''
        
        const queryRes = await executeSQL({ 
          sql: detail.sql_query, 
          datasource_id: datasource_id
        })
        // 注意：在这种情况下，我们不希望重新保存历史记录，因为这是在加载历史记录
        // 所以我们不需要更新 agentMsg.queryResult.query_id
        agentMsg.queryResult.result = queryRes
        
        // 更新步骤信息以反映重新执行
        agentMsg.queryResult.steps.push({
          title: '查询重新执行', 
          content: `成功重新执行查询，获取到 ${queryRes.total_count} 条记录`, 
          status: 'success'
        })
      } catch (e) {
        console.error('Failed to reload historical data:', e)
        Message.warning('无法重新执行历史查询，仅显示历史概要信息')
        
        // 即使执行失败，也要更新步骤信息
        agentMsg.queryResult.steps.push({
          title: '查询重新执行', 
          content: '由于数据源或权限变更，无法重新执行查询', 
          status: 'error'
        })
      }
    } else if (detail.status === 'failed' && agentMsg.queryResult) {
      // 如果历史记录本身是失败的，显示失败信息
      agentMsg.queryResult.steps.push({
        title: '查询状态', 
        content: `查询曾失败: ${detail.error_message || '未知错误'}`, 
        status: 'error'
      })
    }
  } catch (error) {
    console.error('Load history error:', error)
    Message.error('加载历史失败')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  // 初始化视图标签
  await initViews()
  
  // 初始化对话
  if (route.query.id) {
    // 加载历史对话
    await loadConversationHistory(route.query.id as string)
  } else if (route.query.t) {
    // 新建对话
    await startNewConversation()
  } else {
    // 默认开始新对话
    await startNewConversation()
  }
  
  // 加载元数据用于调整查询和下钻（使用当前选中的视图过滤）
  try {
    // 获取当前视图的 base_table_id（关联到 dataset）
    const currentTab = viewTabs.value.find(t => t.viewId === activeViewId.value)
    const baseTableId = currentTab?.baseTableId
    const viewId = activeViewId.value
    
    const [m, d] = await Promise.all([
      getMetrics(baseTableId ? { dataset_id: baseTableId } : {}),
      getDimensions(baseTableId ? { dataset_id: baseTableId } : (viewId ? { view_id: viewId } : {}))
    ])
    allMetrics.value = m
    allDimensions.value = d
    
    // 获取时间格式配置
    const timeFormatSetting = await getSystemSetting('time_formats')
    timeFormats.value = timeFormatSetting?.value || []
  } catch (e) {
    console.error('Failed to load metadata or settings:', e)
  }
})

const loadingSteps: AnalysisStep[] = [
  { title: '意图识别', content: '正在识别意图...', status: 'loading' },
  { title: '指标检索', content: '正在检索指标...', status: 'pending' },
  { title: '指标查询', content: '正在执行查询...', status: 'pending' }
]

function formatColumns(cols: string[]) {
  if (!cols || cols.length === 0) return []
  const result = cols.map(col => {
    let title = col
    if (col && col.includes('__')) {
      const parts = col.split('__')
      const baseName = parts[0] || ''
      const suffix = parts[1] || ''
      const dim = baseName ? findDimension(baseName) : null
      title = dim ? `${dim.display_name || dim.name}(${suffix})` : col
    } else if (col) {
      const dim = findDimension(col)
      if (dim) title = dim.display_name || dim.name
      const metric = findMetric(col)
      if (metric) title = metric.display_name || metric.name
    }
    
    return {
      title: title,
      dataIndex: col,
      align: 'right' as const,
      headerCellStyle: { background: '#f2f3f5' }
    }
  })

  // 添加操作列 (Arco 原生行数据传递的推荐方式)
  result.push({
    title: '操作',
    slotName: 'actions',
    width: 80,
    fixed: 'right',
    align: 'center'
  } as any)

  return result
}

function formatData(result: any, queryId?: string) {
  if (!result || !result.columns) return []
  const { columns, data } = result
  return data.map((row: any, index: number) => {
    // 使用全局唯一的 key，防止跨卡片选中冲突
    const uniqueKey = (queryId || 'q') + '_' + index
    const obj: Record<string, any> = { key: uniqueKey }
    columns.forEach((col: string, i: number) => {
      obj[col] = typeof row[i] === 'number' && col.includes('同比') ? (row[i] * 100).toFixed(2) + '%' : row[i]
    })
    return obj
  })
}

function handleEnter(e: KeyboardEvent) {
  handleQuery()
}

// 显示数据格式配置弹窗
async function showDataFormatConfig() {
  // 加载当前结果绑定的视图的可过滤字段
  const viewId = activeQueryResult.value?.view_id || activeViewId.value
  if (viewId) {
    await loadFilterableFields(viewId)
  }
  dataFormatConfigVisible.value = true
}

// 处理生成API按钮点击
function handleGenerateApi(queryResult: FullQueryResponse) {
  activeQueryResult.value = queryResult
  showDataFormatConfig()
}

// 打开API调试
function openApiDebug(configId: string) {
  apiDebugConfigId.value = configId
  apiDebugVisible.value = true
}

// 处理数据格式配置保存
async function handleDataFormatSave(config: { targetFormat: any, apiParameters: string[] }) {
  dataFormatConfig.value = config
  
  // 如果是从"生成API"按钮触发的，立即生成配置
  if (activeQueryResult.value) {
    await generateDataFormatForQuery(activeQueryResult.value)
  }
}

// 为指定查询结果生成数据格式配置
async function generateDataFormatForQuery(queryResult: FullQueryResponse) {
  if (!dataFormatConfig.value) {
    Message.warning('请先配置数据格式')
    return
  }
  
  // 验证目标格式
  const targetFormat = dataFormatConfig.value.targetFormat
  if (!targetFormat) {
    Message.error('目标格式不能为空')
    return
  }
  
  // 如果是字符串，尝试解析为JSON
  let parsedTargetFormat = targetFormat
  if (typeof targetFormat === 'string') {
    try {
      parsedTargetFormat = JSON.parse(targetFormat)
    } catch (e) {
      Message.error('目标格式JSON解析失败')
      return
    }
  }
  
  // 确保是数组
  if (!Array.isArray(parsedTargetFormat)) {
    Message.error('目标格式必须是数组')
    return
  }
  
  try {
    // 添加加载步骤
    if (queryResult.steps) {
      queryResult.steps.push({ 
        title: '生成数据格式配置', 
        content: '正在生成数据格式配置...', 
        status: 'loading' 
      })
    }
    
    const apiParametersStr = dataFormatConfig.value.apiParameters.join('、')
    
    // 深度克隆数据，避免 Proxy 对象问题
    const clonedTargetFormat = JSON.parse(JSON.stringify(parsedTargetFormat))
    const mql = JSON.parse(JSON.stringify(queryResult.mql))
    const queryResultData = JSON.parse(JSON.stringify({
      columns: queryResult.result.columns || [],
      data: (queryResult.result.data || []).slice(0, 5),
      total_count: queryResult.result.total_count || 0,
      execution_time: queryResult.result.execution_time || 0
    }))
    
    // 构建请求数据
    const requestData: any = {
      natural_language: queryResult.natural_language || '',
      target_format_example: clonedTargetFormat,
      api_parameters: apiParametersStr || ''
    }
    
    // 传入前置查询结果
    if (mql && Object.keys(mql).length > 0) {
      requestData.existing_mql = mql
    }
    if (queryResult.sql) {
      requestData.existing_sql = queryResult.sql
    }
    if (queryResult.result && queryResult.result.data && queryResult.result.data.length > 0) {
      requestData.existing_query_result = queryResultData
    }
    
    console.log('发送数据格式配置请求:', JSON.stringify(requestData, null, 2))
    
    const configResult = await generateDataFormatConfig(requestData)
    
    // 移除loading步骤
    if (queryResult.steps) {
      queryResult.steps.pop()
    }
    
    if (configResult.success) {
      queryResult.dataFormatConfigId = configResult.configId
      if (queryResult.steps) {
        queryResult.steps.push({
          title: '数据格式配置',
          content: `数据格式配置已生成（ID: ${configResult.configId}），API端点：${configResult.apiEndpoint || '未生成'}`,
          status: 'success'
        })
      }
      Message.success('数据格式配置已生成')

      // 保存到历史记录
      if (conversationId.value) {
        try {
          await saveConversationHistory(conversationId.value, messages.value.map(msg => ({
            type: msg.type,
            content: msg.content,
            queryResult: msg.queryResult ? toRaw(msg.queryResult) : undefined
          })))
          console.log('历史记录已保存（包含 dataFormatConfigId）')
        } catch (error) {
          console.error('保存历史记录失败:', error)
        }
      }
    } else {
      if (queryResult.steps) {
        queryResult.steps.push({ 
          title: '数据格式配置', 
          content: `配置生成失败：${configResult.error || '未知错误'}`, 
          status: 'error' 
        })
      }
      console.error('数据格式配置生成失败:', configResult)
    }
  } catch (error: any) {
    console.error('生成数据格式配置失败:', error)
    console.error('错误详情:', error.response?.data || error.message)
    
    // 输出详细的验证错误
    if (error.response?.data?.detail) {
      console.error('验证错误详情:', JSON.stringify(error.response.data.detail, null, 2))
      
      // 构建友好的错误消息
      let errorMessage = error.response?.data?.detail
      if (Array.isArray(errorMessage)) {
        errorMessage = errorMessage.map((err: any) => {
          if (err.msg) return `${err.loc?.join('.') || 'field'}: ${err.msg}`
          return JSON.stringify(err)
        }).join('; ')
      }
      
      // 移除loading步骤
      if (queryResult.steps) {
        queryResult.steps.pop()
      }
      
      if (queryResult.steps) {
        queryResult.steps.push({ 
          title: '数据格式配置', 
          content: `配置生成出错：${errorMessage}`, 
          status: 'error' 
        })
      }
    } else {
      // 移除loading步骤
      if (queryResult.steps) {
        queryResult.steps.pop()
      }
      
      if (queryResult.steps) {
        queryResult.steps.push({ 
          title: '数据格式配置', 
          content: `配置生成出错：${error.message || '未知错误'}`, 
          status: 'error' 
        })
      }
    }
  }
}

// 构建意图识别阶段的内容
function buildPreparationContent(data: any): string {
  let content = data.content || '意图识别完成\n'
  
  if (data.intent_type) {
    content += `意图类型: ${data.intent_type}\n`
  }
  if (data.complexity) {
    content += `复杂度: ${data.complexity}\n`
  }
  if (data.suggested_metrics && data.suggested_metrics.length > 0) {
    content += `推荐指标: ${data.suggested_metrics.join(', ')}\n`
  }
  if (data.suggested_dimensions && data.suggested_dimensions.length > 0) {
    content += `推荐维度: ${data.suggested_dimensions.join(', ')}`
  }
  
  return content
}

// 构建MQL生成阶段的内容
function buildGenerationContent(data: any): string {
  let content = data.content || `MQL生成完成`
  
  if (data.mql_attempts) {
    content += `\n尝试次数: ${data.mql_attempts}`
  }
  
  if (data.mql_errors && data.mql_errors.length > 0) {
    content += `\n验证错误: ${data.mql_errors.join('; ')}`
  }
  
  return content
}

// 构建查询执行阶段的内容
function buildExecutionContent(data: any, result: any): string {
  let content = data.content || ''
  
  if (result && result.total_count !== undefined) {
    if (content) content += '\n'
    content += `返回 ${result.total_count} 条数据`
  }
  if (result && result.execution_time) {
    content += `\n执行时间: ${result.execution_time}ms`
  }
  if (data.sql) {
    content += `\nSQL: ${data.sql.substring(0, 100)}${data.sql.length > 100 ? '...' : ''}`
  }
  
  return content
}

// 构建结果解释阶段的内容
function buildInterpretationContent(data: any): string {
  let content = data.content || '结果解释完成\n'
  
  if (data.insights && data.insights.length > 0) {
    content += `\n洞察:\n`
    data.insights.forEach((insight: string, idx: number) => {
      content += `${idx + 1}. ${insight}\n`
    })
  }
  if (data.visualization) {
    content += `\n推荐图表: ${data.visualization}`
  }
  
  return content
}

async function handleQuery() {
  if (!queryInput.value.trim() || loading.value) return

  console.log('[History] handleQuery 开始, conversationId.value:', conversationId.value)

  // 确保有对话ID，如果没有则先创建
  if (!conversationId.value) {
    try {
      const response = await startConversation()
      conversationId.value = response.conversation_id
      console.log('[History] 创建新对话, new conversationId:', conversationId.value)
    } catch (error) {
      console.error('Failed to create conversation ID:', error)
    }
  }

  const userQuestion = queryInput.value
  messages.value.push({ type: 'user', content: userQuestion })
  queryInput.value = ''
  
  // 保存当前选中的视图ID，用于绑定到这次查询
  const currentViewId = activeViewId.value
  
  // 添加 agent 消息占位 - 使用流式接口
  messages.value.push({ 
    type: 'agent', 
    loading: true,
    queryResult: {
      natural_language: userQuestion,
      mql: {},
      sql: '',
      viewType: 'table',
      view_id: currentViewId,  // 绑定视图ID
      steps: [
        { title: 'Agent初始化', content: '正在启动 Agent 流式查询...', status: 'loading' }
      ],
      result: { columns: [], data: [], total_count: 0, execution_time: 0 },
      query_id: '',
      // 新增：意图识别相关字段（用于流式返回）
      intent: null,
      intent_type: '',
      complexity: '',
      suggested_metrics: [],
      suggested_dimensions: [],
      sql_datasources: [],
      mql_errors: [],
      confidence: undefined
    }
  })
  
  const agentIndex = messages.value.length - 1
  loading.value = true
  scrollToBottom()

  try {
    const agentMsg = messages.value[agentIndex]!
    const res = agentMsg.queryResult
    if (!res) return

    // 获取后端 API 地址
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'

    // 构建请求参数
    const requestBody: any = {
      natural_language: userQuestion,
      user_id: 'anonymous',
      conversation_id: conversationId.value || undefined,
      view_id: activeViewId.value || undefined
    }
    
    // 如果有引用上下文，传递给后端（使用引用时绑定的视图ID）
    if (quotedMql.value) {
      requestBody.context = {
        quoted_mql: quotedMql.value,
        view_id: quotedViewId.value || activeViewId.value
      }
    }
    
    // 使用 fetch API 发送 POST 请求并流式读取响应
    const response = await fetch(`${apiBaseUrl}/agent/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 创建可读流
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let eventType = ''

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }

      // 解码数据块
      buffer += decoder.decode(value, { stream: true })
      
      // 处理 SSE 格式的数据
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留不完整的行

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.substring(6).trim()
          continue
        }
        
        if (line.startsWith('data:')) {
          const dataStr = line.substring(5).trim()
          
          try {
            const data = JSON.parse(dataStr)
            
            if (eventType === 'step') {
              console.log('Stream step:', data)
              
              // 将步骤添加到结果中（流式更新界面）
              if (!res.steps) res.steps = []
              res.steps.push({
                title: data.skill || data.node || data.title || '处理中',
                content: data.message || data.description || data.content || '',
                status: 'success'
              })
              
              nextTick()
              scrollToBottom()
            } else if (eventType === 'intermediate') {
              // 中间结果 - 边执行边返回数据
              console.log('Stream intermediate:', data)
              
              const stage = data.stage
              
              // 根据不同阶段更新数据
              if (stage === 'preparation') {
                // 意图识别阶段完成
                res.suggested_metrics = data.suggested_metrics || []
                res.suggested_dimensions = data.suggested_dimensions || []
                res.intent = data.intent
                res.intent_type = data.intent_type || ''
                res.complexity = data.complexity || ''
                
                // 构建意图识别的详细信息
                const prepContent = buildPreparationContent(data)
                res.steps.push({
                  title: '意图识别',
                  content: prepContent,
                  status: 'success',
                  extra: {
                    suggested_metrics: data.suggested_metrics,
                    suggested_dimensions: data.suggested_dimensions,
                    intent_type: data.intent_type,
                    complexity: data.complexity
                  }
                })
              } else if (stage === 'generation') {
                // MQL 生成阶段完成
                res.mql = data.mql || {}
                res.mql_attempts = data.mql_attempts
                res.mql_errors = data.mql_errors || []
                
                const genContent = buildGenerationContent(data)
                res.steps.push({
                  title: 'MQL生成',
                  content: genContent,
                  status: 'success',
                  extra: {
                    mql: data.mql,
                    mql_attempts: data.mql_attempts,
                    mql_errors: data.mql_errors
                  }
                })
              } else if (stage === 'execution') {
                // 查询执行阶段完成 - 关键：此时已有数据可以显示
                res.sql = data.sql || ''
                res.sql_datasources = data.sql_datasources || []
                res.result = data.result || { columns: [], data: [], total_count: 0, execution_time: 0 }
                res.query_id = data.query_id || res.query_id
                
                // 确保 chart_recommendation 存在
                if (!res.result.chart_recommendation) {
                  res.result.chart_recommendation = 'table'
                }
                
                const execContent = buildExecutionContent(data, res.result)
                res.steps.push({
                  title: '查询执行',
                  content: execContent,
                  status: 'success',
                  extra: {
                    sql: data.sql,
                    result: res.result
                  }
                })
                
                // 关键：此时可以显示数据了，不需要等最后
                nextTick()
                scrollToBottom()
              } else if (stage === 'interpretation') {
                // 结果解释阶段完成
                res.interpretation = data.interpretation
                res.insights = data.insights || []
                res.visualization = data.visualization
                res.visualization_suggestion = data.visualization_suggestion
                
                const interpContent = buildInterpretationContent(data)
                res.steps.push({
                  title: '结果解释',
                  content: interpContent,
                  status: 'success',
                  extra: {
                    interpretation: data.interpretation,
                    insights: data.insights,
                    visualization: data.visualization
                  }
                })
              }
              
              nextTick()
              scrollToBottom()
            } else if (eventType === 'result') {
              console.log('Stream result:', data)
              
              // 填充最终结果 - 包含所有字段
              res.mql = data.mql || {}
              res.sql = data.sql || ''
              res.result = data.result || { columns: [], data: [], total_count: 0, execution_time: 0 }
              
              // 确保 chart_recommendation 存在
              if (!res.result.chart_recommendation && data.visualization) {
                res.result.chart_recommendation = data.visualization
              } else if (!res.result.chart_recommendation) {
                res.result.chart_recommendation = 'table'
              }
              
              res.query_id = data.query_id || 'stream_' + Date.now()
              res.interpretation = data.interpretation
              res.insights = data.insights || []
              
              // 新增：意图识别相关字段（从流式结果中获取）
              res.intent = data.intent || null
              res.intent_type = data.intent_type || ''
              res.complexity = data.complexity || ''
              res.suggested_metrics = data.suggested_metrics || []
              res.suggested_dimensions = data.suggested_dimensions || []
              res.sql_datasources = data.sql_datasources || []
              res.mql_errors = data.mql_errors || []
              res.confidence = data.confidence
              
              messages.value[agentIndex]!.loading = false
              
              // 将所有loading状态的步骤改为success（左侧加载动画变为勾）
              if (res.steps) {
                res.steps.forEach(step => {
                  if (step.status === 'loading') {
                    step.status = 'success'
                  }
                })
              }
              
              // 添加完成步骤
              if (!res.steps) res.steps = []
              res.steps.push({
                title: '查询完成',
                content: 'Agent流式查询成功完成',
                status: 'success'
              })

              Message.success('查询成功')

              // 解析时间范围
              if (res.mql && res.query_id) {
                fetchAndParseTimeRanges(res.mql, res.query_id)
              }

              nextTick()
              scrollToBottom()
            } else if (eventType === 'error') {
              console.error('Stream error:', data)
              
              if (!res.steps) res.steps = []
              res.steps.push({
                title: '错误',
                content: data.message || '查询过程中发生错误',
                status: 'error'
              })
              
              messages.value[agentIndex]!.loading = true
              Message.error('查询失败')
              
              nextTick()
              scrollToBottom()
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
    
    // 保存对话历史
    if (conversationId.value) {
      try {
        console.log('[History] 保存对话历史, conversationId:', conversationId.value, '消息数:', messages.value.length)
        saveConversationHistory(conversationId.value, messages.value.map(msg => ({
          type: msg.type,
          content: msg.content,
          queryResult: msg.queryResult
        }))).then(res => {
          console.log('[History] 保存结果:', res)
        })
      } catch (e) {
        console.error('保存对话历史失败:', e)
      }
    } else {
      console.log('[History] 未保存，conversationId 为空')
    }
  } catch (error: any) {
    console.error('查询失败:', error)
    
    // 显示错误步骤
    const agentMsg = messages.value[agentIndex]
    if (agentMsg && agentMsg.queryResult && agentMsg.queryResult.steps) {
      agentMsg.queryResult.steps.push({
        title: '查询失败',
        content: error.message || '查询过程中发生错误',
        status: 'error'
      })
    }
    
    Message.error(error.message || '查询失败')
  } finally {
    loading.value = false
    // 清空引用上下文
    quotedMql.value = null
    quotedViewId.value = null
    scrollToBottom()
  }
}

function scrollToBottom() {
  setTimeout(() => {
    nextTick(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTo({
          top: chatContainer.value.scrollHeight,
          behavior: 'smooth'
        })
      }
    })
  }, 100)
}

function findMetric(name: string) {
  return allMetrics.value.find(m => m.name === name || m.display_name === name)
}

function findDimension(name: string) {
  return allDimensions.value.find(d => d.name === name || d.display_name === name || d.physical_column === name)
}

function getMetricsFromCols(res: FullQueryResponse) {
  if (!res || !res.result || !res.result.columns) return []
  const mqlMetrics = res.mql?.metrics || []
  return res.result.columns.filter(col => mqlMetrics.includes(col))
}

function getDimensionsFromCols(res: FullQueryResponse) {
  if (!res || !res.result || !res.result.columns) return []
  const mqlDims = res.mql?.dimensions || []
  return res.result.columns.filter(col => mqlDims.includes(col))
}

function handleRowContextMenu(record: any, result: FullQueryResponse, ev: MouseEvent) {
  ev.preventDefault()
  handleRowSelection(record, result)
  
  // 使用 Dropdown.display 实现原生的右键菜单，且能直接传递行数据
  Dropdown.display({
    ev,
    content: () => h('div', { class: 'arco-dropdown-list' }, [
      h(Doption, { 
        onClick: () => showDrillDownDialog()
      }, { 
        default: () => '下钻分析',
        icon: () => h(IconLayers)
      })
    ])
  })
}

function handleActionSelect(val: any, record: any, result: FullQueryResponse) {
  handleRowSelection(record, result)
  if (val === 'drill') {
    showDrillDownDialog()
  }
}

function handleRowSelection(record: any, result?: FullQueryResponse) {
  if (!record || !result) return
  const rawData = toRaw(record)
  selectedRowKey.value = record.key
  selectedRecord.value = rawData
  activeQueryResult.value = result
}

function showDrillDownDialog() {
  if (!selectedRecord.value) {
    Message.warning('请先点击选中数据行')
    return
  }
  drillDownForm.dimensions = []
  drillDownVisible.value = true
  
  // 更新维度约束
  if (activeQueryResult.value) {
    updateAllowedDimensions(activeQueryResult.value)
  }
}

function showGlobalAddDimension(result: FullQueryResponse) {
  selectedRecord.value = null 
  selectedRowKey.value = null
  activeQueryResult.value = result
  addDimensionForm.dimensions = []
  addDimensionVisible.value = true
  
  // 更新维度约束
  updateAllowedDimensions(result)
}

async function updateAllowedDimensions(queryResult: FullQueryResponse) {
  if (!queryResult.mql?.metrics?.length) {
    allowedDimensions.value = []
    return
  }
  
  try {
    // 从MQL中提取指标ID
    const metricNames = queryResult.mql.metrics
    const metricIds = []
    
    for (const name of metricNames) {
      const metricDef = queryResult.mql.metricDefinitions?.[name]
      if (metricDef?.refMetric) {
        const metric = allMetrics.value.find(m => 
          m.name === metricDef.refMetric || m.measure_column === metricDef.refMetric
        )
        if (metric) {
          metricIds.push(metric.id)
        }
      }
    }
    
    if (metricIds.length > 0) {
      const allowedDims = await getMetricsAllowedDimensions(metricIds)
      allowedDimensions.value = allowedDims
    } else {
      allowedDimensions.value = []
    }
  } catch (error) {
    console.error('Failed to fetch allowed dimensions:', error)
    allowedDimensions.value = []
  }
}

/**
 * 调用后端解析时间范围
 */
async function fetchAndParseTimeRanges(mql: any, queryId: string) {
  if (!mql || !mql.filters) return

  try {
    const response = await parseTimeRanges({ mql })
    if (response.success && response.time_ranges) {
      parsedTimeRanges.value[queryId] = response.time_ranges
    }
  } catch (error) {
    console.error('Failed to parse time ranges:', error)
  }
}

/**
 * 获取解析后的时间范围（用于 UI 展示）
 */
function getParsedTimeRange(mql: any, queryId: string) {
  if (!queryId || !parsedTimeRanges.value[queryId]) {
    return null
  }

  const timeRanges = parsedTimeRanges.value[queryId]
  const timeConditions = extractTimeConditions(mql?.filters || {})

  if (timeConditions.length > 0) {
    const field = timeConditions[0].field
    return timeRanges[field] || null
  }

  return null
}

/**
 * 格式化时间范围显示
 * 从 filters 中提取时间字段的过滤条件并格式化显示
 */
function formatTimeRange(mql: any) {
  if (!mql) return ''

  // 首先尝试从 filters 中提取时间字段条件
  if (mql.filters) {
    const timeConditions = extractTimeConditions(mql.filters)

    // 找到时间过滤条件
    if (timeConditions.length > 0) {
      // 查找时间字段的显示名称
      let timeFieldName = ''
      const firstTimeCond = timeConditions[0]
      const dim = findDimension(firstTimeCond.field)
      if (dim) {
        timeFieldName = dim.display_name || dim.name
      }

      // 解析时间范围
      const range = parseTimeRangeFromConditions(timeConditions)

      if (range && range.start && range.end) {
        return `${timeFieldName ? timeFieldName + ': ' : ''}${range.start} - ${range.end}`
      } else if (range && range.start) {
        return `${timeFieldName ? timeFieldName + ': ' : ''}${range.start} 起`
      } else if (range && range.end) {
        return `${timeFieldName ? timeFieldName + ': ' : ''}${range.end} 止`
      }
    }
  }

  // 回退：尝试解析 timeConstraint（旧格式兼容）
  if (mql.timeConstraint && mql.timeConstraint !== 'true' && mql.timeConstraint !== '1=1') {
    const tc = mql.timeConstraint

    // 解析 BETWEEN 模式
    const betweenMatch = tc.match(/BETWEEN\s*'([^']+)'\s+AND\s*'([^']+)'/i)
    if (betweenMatch) {
      return `${formatDateString(betweenMatch[1])} - ${formatDateString(betweenMatch[2])}`
    }

    // 解析 >= 和 <= 模式
    const geMatch = tc.match(/>=\s*'([^']+)'/i)
    const leMatch = tc.match(/<=\s*'([^']+)'/i)
    if (geMatch && leMatch) {
      return `${formatDateString(geMatch[1])} - ${formatDateString(leMatch[1])}`
    } else if (geMatch) {
      return `${formatDateString(geMatch[1])} 起`
    } else if (leMatch) {
      return `${formatDateString(leMatch[1])} 止`
    }

    // 解析相对时间
    const lastNYears = tc.match(/LAST_N_YEARS\((\d+)\)/i)
    if (lastNYears) return `最近 ${lastNYears[1]} 年`

    const lastNMonths = tc.match(/LAST_N_MONTHS\((\d+)\)/i)
    if (lastNMonths) return `最近 ${lastNMonths[1]} 个月`

    const lastNDays = tc.match(/LAST_N_DAYS\((\d+)\)/i)
    if (lastNDays) return `最近 ${lastNDays[1]} 天`

    if (tc.includes('TODAY')) return '今天'
    if (tc.includes('YESTERDAY')) return '昨天'
  }

  return ''  // 无时间条件则返回空
}

/**
 * 从 filters 中提取时间字段的过滤条件
 */
function extractTimeConditions(filters: any): MQLFilterCondition[] {
  if (!filters) return []

  const result: MQLFilterCondition[] = []
  const flatFilters = flattenFilters(filters)

  flatFilters.forEach(f => {
    if (!f.field) return

    // 检查是否是时间字段
    const dim = findDimension(f.field)
    if (!dim) return

    const isTime = dim.dimension_type === 'time' ||
      ['date', 'datetime', 'timestamp'].includes(dim.data_type?.toLowerCase() || '')

    if (isTime) {
      result.push(f)
    }
  })

  return result
}

/**
 * 从时间条件中解析时间范围
 */
function parseTimeRangeFromConditions(conditions: MQLFilterCondition[]): { start?: string, end?: string } | null {
  if (conditions.length === 0) return null

  let startDate: string | null = null
  let endDate: string | null = null

  conditions.forEach(cond => {
    const value = cond.value?.replace(/['"]/g, '') || ''

    if (cond.op === '>=' || cond.op === '>') {
      // 如果已经有 startDate，取最大的（最新日期）
      if (!startDate || value > startDate) {
        startDate = value
      }
    } else if (cond.op === '<=' || cond.op === '<') {
      // 如果已经有 endDate，取最小的（最晚日期）
      if (!endDate || value < endDate) {
        endDate = value
      }
    } else if (cond.op === '=') {
      // 等于同时设置 start 和 end
      startDate = value
      endDate = value
    } else if (cond.op === 'BETWEEN') {
      // BETWEEN 格式: '2023-01-01 AND 2026-01-01'
      const parts = value.split(/AND|and/i)
      if (parts.length >= 2) {
        startDate = parts[0]?.trim()
        endDate = parts[1]?.trim()
      }
    }
  })

  if (!startDate && !endDate) return null

  return {
    start: startDate ? formatDateString(startDate) : undefined,
    end: endDate ? formatDateString(endDate) : undefined
  }
}

/**
 * 格式化日期字符串，确保显示完整的年月日
 */
function formatDateString(dateStr: string): string {
  if (!dateStr) return ''

  // 如果是完整的年月日格式
  if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
    return dateStr
  }

  // 如果是年月格式，补全为月初
  if (dateStr.match(/^\d{4}-\d{2}$/)) {
    return `${dateStr}-01`
  }

  // 如果是年格式，补全为年初
  if (dateStr.match(/^\d{4}$/)) {
    return `${dateStr}-01-01`
  }

  // 其他情况直接返回
  return dateStr
}

// 添加分析维度 (从卡片头部点击，全局追加)
// function showGlobalAddDimension(result: FullQueryResponse) {
//   activeQueryResult.value = result
//   selectedRecord.value = null // 清除行选择
//   showDrillDownDialog()
// }

// 维度细分 (兼容旧方法名或备用)
function showDrillDown(result: FullQueryResponse) {
  showGlobalAddDimension(result)
}

async function showAdjustment(result: FullQueryResponse) {
  activeQueryResult.value = result
  adjustmentVisible.value = true
  
  // 提取当前已选的指标和维度
  adjustmentForm.value.metrics = result.mql?.metrics || []
  adjustmentForm.value.dimensions = result.mql?.dimensions || []
  
  // 简单解析现有过滤条件（保留兼容旧格式）
  adjustmentForm.value.filters = flattenFilters(result.mql?.filters).map(f => ({ type: 'condition' as const, ...f }))

  // 递归将 MQLFilterGroup 条件节点转为 FeItem
  function toFeItem(node: MQLFilterCondition | MQLFilterGroup): FeCondition | FeSubGroup {
    if ('field' in node) {
      return { type: 'condition', field: (node as MQLFilterCondition).field, op: (node as MQLFilterCondition).op || '=', value: (node as MQLFilterCondition).value }
    }
    const sg = node as MQLFilterGroup
    const items: Array<FeCondition | FeSubGroup> = (sg.conditions || []).map(c => toFeItem(c))
    return { type: 'subgroup', operator: sg.operator || 'AND', items }
  }

  // 将结构化 filters 转为 filterGroups 供编辑器使用
  const raw = result.mql?.filters
  if (raw && typeof raw === 'object' && (raw as MQLFilterGroup).conditions) {
    const group = raw as MQLFilterGroup
    if (group.operator === 'OR') {
      adjustmentForm.value.filterGroups = group.conditions.map(sub => ({
        operator: 'AND' as const,
        items: [toFeItem(sub)]
      }))
    } else {
      adjustmentForm.value.filterGroups = [{
        operator: 'AND',
        items: (group.conditions || []).map(c => toFeItem(c))
      }]
    }
  } else if (raw && Array.isArray(raw) && raw.length > 0) {
    adjustmentForm.value.filterGroups = [{
      operator: 'AND',
      items: flattenFilters(raw).map(f => ({ type: 'condition' as const, field: f.field, op: f.op, value: f.value }))
    }]
  } else {
    adjustmentForm.value.filterGroups = [{ operator: 'AND', items: [{ type: 'condition' as const, field: '', op: '=', value: '' }] }]
  }
  
  // 使用结果绑定的视图的元数据加载下拉选项
  const viewId = result.view_id || activeViewId.value
  if (viewId) {
    try {
      const metadata = await getViewMetadata(viewId)
      adjustmentMetadata.value = metadata
    } catch (e) {
      console.error('Failed to load view metadata:', e)
      // 降级使用全局元数据
      adjustmentMetadata.value = {
        metrics: allMetrics.value,
        dimensions: allDimensions.value
      }
    }
  } else {
    adjustmentMetadata.value = {
      metrics: allMetrics.value,
      dimensions: allDimensions.value
    }
  }
}

async function handleAdjust() {
  if (!activeQueryResult.value) return
  
  // 校验逻辑
  if (adjustmentForm.value.metrics.length === 0) {
    Message.warning('请至少选择一个指标')
    return
  }
  
  adjustmentVisible.value = false
  Message.info('正在根据调整后的条件重新查询...')
  
  // 构建新的 MQL
  const newMql = JSON.parse(JSON.stringify(activeQueryResult.value.mql || {}))
  
  // 确保结构完整
  newMql.metrics = adjustmentForm.value.metrics
  newMql.dimensions = adjustmentForm.value.dimensions
  // 构建结构化 filters
  const rootOp = (filterEditorRef.value?.getRootOperator() || 'AND') as 'AND' | 'OR'

  function buildConditions(items: any[]) {
    return items
      .filter(item => item.type === 'condition' && item.field && item.value)
      .map(item => ({ field: item.field, op: item.op, value: item.value }))
  }

  function buildGroups(groups: any[]) {
    return groups
      .filter(g => g.items.some((i: any) => (i.type === 'condition' && i.field && i.value) || i.type === 'subgroup'))
      .map(g => {
        const leafConds = buildConditions(g.items)
        const subGroups = (g.items || [])
          .filter((i: any) => i.type === 'subgroup')
          .map((sg: any) => ({
            operator: sg.operator,
            conditions: buildConditions(sg.items || [])
          }))
        const allConds = [...leafConds, ...subGroups]
        return { operator: g.operator, conditions: allConds }
      })
  }

  const validGroups = buildGroups(adjustmentForm.value.filterGroups)

  if (validGroups.length === 0) {
    newMql.filters = {}
  } else if (validGroups.length === 1 && validGroups[0]) {
    newMql.filters = { operator: validGroups[0].operator, conditions: validGroups[0].conditions }
  } else {
    newMql.filters = { operator: rootOp, conditions: validGroups }
  }
  
  if (!newMql.metricDefinitions) newMql.metricDefinitions = {}
  
  // 关键：补全指标定义，确保后端能正确识别新增指标
  newMql.metrics.forEach((mName: string) => {
    if (!newMql.metricDefinitions[mName]) {
      const metricObj = findMetric(mName)
      if (metricObj) {
        newMql.metricDefinitions[mName] = {
          refMetric: metricObj.name // 使用指标唯一标识名
        }
      }
    }
  })
  
  // 移除不再需要的指标定义（保持 MQL 整洁）
  const currentMetricSet = new Set(newMql.metrics)
  Object.keys(newMql.metricDefinitions).forEach(key => {
    if (!currentMetricSet.has(key)) {
      delete newMql.metricDefinitions[key]
    }
  })
  
  loading.value = true
  try {
    const sqlRes = await mql2sql(newMql)
    const queryRes = await executeSQL({ 
      sql: sqlRes.sql, 
      datasource_id: sqlRes.datasources[0] || ''
    })
    
    // 更新当前活动消息的结果
    activeQueryResult.value.mql = newMql
    activeQueryResult.value.sql = sqlRes.sql
    activeQueryResult.value.result = queryRes
    
    // 强制视图重置或更新
    if (!activeQueryResult.value.steps) activeQueryResult.value.steps = []
    activeQueryResult.value.steps.push({ 
      title: '调整查询', 
      content: `查询条件已更新：使用了 ${newMql.metrics.length} 个指标，${newMql.dimensions.length} 个维度。`, 
      status: 'success' 
    })
    
    Message.success('查询已更新')
    
    // 保存更新后的对话历史（调整查询修改了现有消息）
    if (conversationId.value) {
      try {
        await saveConversationHistory(conversationId.value, messages.value.map(msg => ({
          type: msg.type,
          content: msg.content,
          queryResult: msg.queryResult
        })))
      } catch (e) {
        console.error('保存对话历史失败:', e)
      }
    }
  } catch (error: any) {
    console.error('Adjustment error:', error)
    Message.error(error.message || '调整查询失败，请检查条件是否合法')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.query-page {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  background: #fff;
  position: relative;
  overflow: hidden;
}

.query-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #f2f3f5;
  flex-shrink: 0;
  background: #fff;
}

.query-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}

.view-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-selector :deep(.arco-radio-group-button) {
  background: #f2f3f5;
  border-radius: 6px;
  padding: 2px;
}

.view-selector :deep(.arco-radio-button) {
  border: none;
  border-radius: 4px !important;
  padding: 4px 12px;
  font-size: 13px;
  transition: all 0.2s;
}

.view-selector :deep(.arco-radio-button:hover) {
  background: #e5e6eb;
}

.view-selector :deep(.arco-radio-button-checked) {
  background: #165dff;
  color: #fff;
  box-shadow: none;
}

.view-selector :deep(.arco-radio-button-checked:hover) {
  background: #4080ff;
}

.tab-close-icon {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.tab-close-icon:hover {
  opacity: 1;
}

.add-view-trigger {
  color: #86909c;
  padding: 4px;
}

.add-view-trigger:hover {
  color: #165dff;
  background: #f2f3f5;
  border-radius: 4px;
}

.query-title {
  font-weight: 600;
  color: var(--color-text-1);
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 10% 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  scroll-behavior: smooth;
}

.result-content-wrapper {
  min-height: 200px;
  margin-top: 12px;
}

.meta-tag-link {
  color: var(--color-primary-light-4);
  cursor: help;
  border-bottom: 1px dashed var(--color-primary-light-4);
}

.metadata-popup {
  max-width: 280px;
  padding: 4px;
}

.metadata-popup .p-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--color-text-1);
}

.metadata-popup .p-desc {
  color: var(--color-text-2);
  font-size: 12px;
  margin-bottom: 8px;
  line-height: 1.5;
}

.metadata-popup .p-formula {
  background: var(--color-fill-2);
  padding: 6px;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  color: var(--color-text-3);
}

.message-item {
  display: flex;
  flex-direction: column;
}

.drill-down-context {
  margin-bottom: 16px;
}

.context-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-2);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.current-dims-display {
  padding: 12px;
  border-radius: 6px;
  min-height: 40px;
}

.current-dims-display.drill-mode {
  background: var(--color-primary-light-1);
  border: 1px solid var(--color-primary-light-2);
}

.current-dims-display.global-mode {
  background: var(--color-success-light-1);
  border: 1px solid var(--color-success-light-2);
}

.tag-label {
  opacity: 0.8;
  margin-right: 4px;
}

.tag-value {
  font-weight: 600;
}

.context-tip {
  font-size: 12px;
  color: var(--color-text-3);
  margin-top: 8px;
  font-style: italic;
}

.user-bubble {
  align-self: flex-end;
  background: #e8f3ff;
  color: #165dff;
  padding: 8px 16px;
  border-radius: 16px 16px 0 16px;
  max-width: 70%;
  font-size: 14px;
}

.agent-message {
  align-self: flex-start;
  width: 100%;
}

.result-card {
  border: 1px solid #e5e6eb;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  margin-top: 16px;
}

.result-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metrics-name {
  font-size: 16px;
  font-weight: 600;
}

.result-body-container {
  display: flex;
  flex-direction: column;
}

/* 查询元信息面板 */
.query-meta-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f7f8fa 0%, #f0f1f5 100%);
  border-radius: 12px;
  border: 1px solid #e8e9eb;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 16px;
  animation: fadeIn 0.4s ease-out;
  animation-fill-mode: both;
}

.meta-row:nth-child(1) { animation-delay: 0.05s; }
.meta-row:nth-child(2) { animation-delay: 0.1s; }
.meta-row:nth-child(3) { animation-delay: 0.15s; }
.meta-row:nth-child(4) { animation-delay: 0.2s; }

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.meta-label {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  min-width: 80px;
  height: 28px;
  font-size: 12px;
  color: #8e8e8e;
  font-weight: 500;
}

.meta-label :deep(.arco-icon) {
  font-size: 14px;
  color: #6b6b6b;
}

.meta-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-2);
}

/* 时间范围样式 */
.time-range-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.time-range-box:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.time-field-name-in-box {
  padding: 2px 8px;
  background: linear-gradient(135deg, #165dff 0%, #4080ff 100%);
  color: #fff;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(22, 93, 255, 0.2);
}

.time-date {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
  letter-spacing: 0.5px;
}

.time-separator {
  color: #8e8e8e;
  font-weight: 500;
}

/* 标签芯片样式 */
.meta-tag-chip {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.meta-tag-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.metric-chip {
  background: linear-gradient(135deg, #f0f5ff 0%, #e6f0ff 100%);
  color: #165dff;
  border-color: #c9dcff;
}

.metric-chip:hover {
  background: linear-gradient(135deg, #e6f0ff 0%, #d9e6ff 100%);
  border-color: #93b5ff;
}

.dimension-chip {
  background: linear-gradient(135deg, #f5f0ff 0%, #ede6ff 100%);
  color: #722ed1;
  border-color: #d9b8ff;
}

.dimension-chip:hover {
  background: linear-gradient(135deg, #ede6ff 0%, #e0d6ff 100%);
  border-color: #b87fff;
}

/* 过滤条件样式 */
.filter-content {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
  font-size: 12px;
}

/* 旧的 result-meta-tags 保留兼容 */
.result-meta-tags {
  display: none; /* 隐藏旧样式，由新样式替代 */
}


.result-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f2f3f5;
  color: var(--color-text-4);
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-right {
  display: flex;
  align-items: center;
}

.config-id {
  color: var(--color-success-light-3);
  font-weight: 500;
}

.input-container {
  padding: 16px 15% 40px;
  background: #fff;
  flex-shrink: 0;
  border-top: 1px solid #f2f3f5;
}

.quoted-mql-box {
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  padding: 8px 16px;
  margin-bottom: 0;
}

.quoted-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.quoted-label {
  font-size: 12px;
  color: var(--color-text-3);
  display: flex;
  align-items: center;
  gap: 4px;
}

.quoted-content {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.quoted-time {
  font-size: 11px;
  color: var(--color-text-4);
  background: #fff;
  padding: 0 6px;
  border-radius: 4px;
  border: 1px solid #e5e6eb;
}

.input-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 0 0 12px 12px;
  padding: 8px;
  background: #fff;
  box-shadow: 0 4px 10px rgba(0,0,0,0.02);
}

.query-input {
  border: none;
  background: transparent;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.input-hint {
  font-size: 12px;
  color: var(--color-text-4);
}

.send-btn {
  background: #165dff;
}

:deep(.arco-textarea) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

:deep(.arco-table-th) {
  font-weight: 600;
}

/* 选中行的高亮样式 - 依赖 Arco 原生类名进行扩展 */
:deep(.arco-table-tr.arco-table-tr-checked),
:deep(.arco-table-tr.arco-table-tr-checked:hover) {
  background-color: var(--color-primary-light-1) !important;
}

:deep(.arco-table-tr.arco-table-tr-checked td),
:deep(.arco-table-tr.arco-table-tr-checked:hover td) {
  background-color: var(--color-primary-light-1) !important;
}

:deep(.result-card .arco-card-header) {
  border-bottom: none;
  padding: 16px 20px 0;
}

:deep(.result-card .arco-card-body) {
  padding: 16px 20px;
}

.sql-view-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sql-toolbar {
  display: flex;
  justify-content: flex-end;
}

.sql-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  background: #f7f8fa;
  border-radius: 4px;
}

.insights-panel {
  border-top: 1px solid var(--color-fill-2);
  padding: 12px 20px;
  background: #f7f8fa;
}

.insights-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.insights-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--color-text-1);
}

.insights-content {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-item {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid var(--color-fill-2);
}

.insight-index {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #4080ff 0%, #0e42d2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.insight-text {
  flex: 1;
  color: var(--color-text-1);
  line-height: 1.6;
  font-size: 13px;
}
</style>