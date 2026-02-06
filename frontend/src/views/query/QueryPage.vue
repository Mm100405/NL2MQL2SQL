<template>
  <div class="query-page">
    <ModelNotConfigured v-if="!settingsStore.isModelAvailable" />

    <template v-else>
      <!-- 顶部问数标题 -->
      <div class="query-header">
        <span class="query-title">{{ currentQueryTitle }}</span>
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
              :mql="msg.queryResult?.mql"
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
                      <a-button type="text" size="small" @click="handleQuote(msg.queryResult.mql)">
                        <template #icon><icon-share-internal /></template>
                        引用
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
                        <template #icon><icon-bar-chart /></template>
                        图表
                      </a-button>
                      <a-button 
                        :type="msg.queryResult.viewType !== 'chart' ? 'primary' : 'outline'" 
                        size="small"
                        @click="msg.queryResult.viewType = 'table'"
                        :style="msg.queryResult.viewType !== 'chart' ? {} : { color: '#4e5969' }"
                      >
                        <template #icon><icon-table /></template>
                        表格
                      </a-button>
                    </a-space>
                  </div>
                </div>
              </template>

              <div class="result-body-container">
                <div class="result-meta-tags">
                  <span>时间范围: {{ formatTimeRange(msg.queryResult.mql) }}</span>
                  <span>指标: 
                    <a-space size="mini">
                      <a-popover v-for="col in getMetricsFromCols(msg.queryResult)" :key="col" position="bottom">
                        <span class="meta-tag-link">{{ findMetric(col)?.display_name || col }}</span>
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
                  </span>
                  <span>维度: 
                    <a-space size="mini">
                      <a-popover v-for="col in getDimensionsFromCols(msg.queryResult)" :key="col" position="bottom">
                        <span class="meta-tag-link">
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
                  </span>
                  <span v-if="msg.queryResult.mql.filters?.length">过滤条件: 
                    <a-tag v-for="f in msg.queryResult.mql.filters" :key="f" size="small" style="margin-right: 4px;" color="orange">
                      {{ formatFilterDisplay(f) }}
                    </a-tag>
                  </span>
                </div>

                <div class="result-content-wrapper">
                  <a-table
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
                <span class="timestamp">{{ msg.queryResult.query_id }}</span>
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
            <span class="quoted-label"><icon-share-internal /> 正在引用上下文进行分析</span>
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
            <span class="input-hint">服务生成的所有内容均由人工智能模型生成，请谨慎识别数据准确性。</span>
            <a-button 
              type="primary" 
              shape="circle" 
              :loading="loading" 
              @click="handleQuery"
              class="send-btn"
            >
              <template #icon><icon-send /></template>
            </a-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 调整查询弹窗 -->
    <a-modal v-model:visible="adjustmentVisible" title="调整查询" @ok="handleAdjust" width="600px">
      <a-form :model="adjustmentForm" layout="vertical">
        <a-form-item label="已选指标">
          <a-select v-model="adjustmentForm.metrics" multiple placeholder="请选择指标">
            <a-option v-for="m in allMetrics" :key="m.id" :value="m.name">{{ m.display_name || m.name }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分析维度">
          <a-select v-model="adjustmentForm.dimensions" multiple placeholder="请选择分析维度">
            <a-option v-for="d in allDimensions" :key="d.id" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="过滤条件">
          <a-space direction="vertical" fill>
            <div v-for="(f, i) in adjustmentForm.filters" :key="i" style="display: flex; gap: 8px">
              <a-select v-model="f.field" style="width: 150px">
                <a-option v-for="d in allDimensions" :key="d.id" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
              </a-select>
              <a-select v-model="f.op" style="width: 80px">
                <a-option value="=">=</a-option>
                <a-option value=">">></a-option>
                <a-option value="<"><</a-option>
                <a-option value="IN">IN</a-option>
              </a-select>
              <a-input v-model="f.value" placeholder="值" style="flex: 1" />
              <a-button type="text" status="danger" @click="adjustmentForm.filters.splice(i, 1)"><icon-delete /></a-button>
            </div>
            <a-button type="outline" size="small" @click="adjustmentForm.filters.push({ field: '', op: '=', value: '' })">
              <template #icon><icon-plus /></template>添加条件
            </a-button>
          </a-space>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, watch, toRaw, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Dropdown, Doption } from '@arco-design/web-vue'
import { IconLayers, IconSettings, IconMore } from '@arco-design/web-vue/es/icon'
import { useSettingsStore } from '@/stores/settings'
import ModelNotConfigured from '@/components/query/ModelNotConfigured.vue'
import QuerySteps from '@/components/query/QuerySteps.vue'
import ChartContainer from '@/components/common/ChartContainer.vue'
import type { FullQueryResponse, AnalysisStep } from '@/api/types'
import { analyzeIntent, generateMQL, mql2sql, executeSQL, getQueryHistoryDetail, startConversation, getConversationHistory, saveConversationHistory } from '@/api/query'
import { getMetrics, getDimensions, getMetricsAllowedDimensions } from '@/api/semantic'
import type { Metric, Dimension } from '@/api/types'

const settingsStore = useSettingsStore()
const route = useRoute()
const router = useRouter()

const queryInput = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const currentQueryTitle = ref('问数对话')
const conversationId = ref<string | null>(null)  // 当前对话ID

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
const timeFormats = ref<any[]>([])
const quotedMql = ref<any>(null)
const selectedRecord = ref<any>(null)
const activeQueryResult = ref<FullQueryResponse | null>(null)
const selectedRowKey = ref<string | null>(null) // 当前选中的行 key (全局唯一)

const drillDownVisible = ref(false)
const addDimensionVisible = ref(false)
const drillDownForm = reactive({
  dimensions: [] as string[]
})
const addDimensionForm = reactive({
  dimensions: [] as string[]
})

const adjustmentVisible = ref(false)
const adjustmentForm = ref<{
  metrics: string[],
  dimensions: string[],
  filters: { field: string, op: string, value: string }[]
}>({
  metrics: [],
  dimensions: [],
  filters: []
})

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
  
  if (!mql.filters) mql.filters = []

  // --- 下钻分析核心逻辑：维度替换 + 过滤锁定 ---
  // 获取当前查询的所有维度
  const currentDims = [...(mql.dimensions || [])]
  
  currentDims.forEach((dim: string) => {
    // 获取该维度在行数据中的值
    const val = record[dim]
    
    if (val !== undefined && val !== null && val !== '') {
      // 构造过滤条件。如果是衍生维度（如：日期__按月），后端 process_mql_expression 能够识别 [展示名__后缀]
      const filterStr = `[${dim}] = '${val}'`
      
      // 避免重复添加相同的过滤条件
      if (!mql.filters.includes(filterStr)) {
        mql.filters.push(filterStr)
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
      conversationId.value = detail.conversation_id || null;
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
    conversationId.value = detail.conversation_id
    
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
function handleQuote(mql: any) {
  quotedMql.value = JSON.parse(JSON.stringify(mql))
  queryInput.value = '' // 清空输入框，引导用户输入增量指令
  Message.success('已加载引用上下文，请输入您的调整或分析要求')
  
  nextTick(() => {
    const input = document.querySelector('.query-input textarea') as HTMLTextAreaElement
    if (input) input.focus()
  })
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
  
  // 加载元数据用于调整查询和下钻
  try {
    const [m, d] = await Promise.all([getMetrics(), getDimensions()])
    allMetrics.value = m
    allDimensions.value = d
    
    // 获取时间格式配置
    const settings = await fetch('/api/v1/settings/system/time_formats').then(res => res.json())
    timeFormats.value = settings.value || []
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

async function handleQuery() {
  if (!queryInput.value.trim() || loading.value) return

  // 确保有对话ID，如果没有则先创建
  if (!conversationId.value) {
    try {
      const response = await startConversation()
      conversationId.value = response.conversation_id
    } catch (error) {
      console.error('Failed to create conversation ID:', error)
    }
  }

  const userQuestion = queryInput.value
  messages.value.push({ type: 'user', content: userQuestion })
  queryInput.value = ''
  
  const agentMsg: MessageItem = { 
    type: 'agent', 
    loading: true,
    queryResult: {
      natural_language: userQuestion,
      mql: {},
      sql: '',
      viewType: 'table',
      steps: [
        { title: '意图识别', content: '正在分析您的查询意图...', status: 'loading' },
        { title: '指标检索', content: '正在检索相关指标和维度...', status: 'pending' },
        { title: '指标查询', content: '正在生成查询并执行...', status: 'pending' }
      ],
      result: { columns: [], data: [], total_count: 0, execution_time: 0 },
      query_id: ''
    }
  }
  messages.value.push(agentMsg)
  
  loading.value = true
  scrollToBottom()

  try {
    const res = agentMsg.queryResult
    if (!res) return

    // 步骤 1: 意图识别
    const intentRes = await analyzeIntent({ natural_language: userQuestion })
    res.steps = intentRes.steps.map((s: any) => ({ ...s, status: 'success' }))
    // 立即显示意图识别结果并更新界面
    res.steps.push({ title: '指标查询', content: '正在分析元数据并生成 MQL...', status: 'loading' })
    await nextTick()
    scrollToBottom()

    // 步骤 2: 生成 MQL
    const mqlRes = await generateMQL({ 
      natural_language: userQuestion,
      context: {
        suggested_metrics: intentRes.suggested_metrics,
        suggested_dimensions: intentRes.suggested_dimensions,
        quoted_mql: quotedMql.value // 传入引用的上下文
      }
    })
    
    res.mql = mqlRes.mql
    quotedMql.value = null // 使用后清空
    // 立即更新 MQL 展示
    res.steps.pop()
    res.steps = [...res.steps, ...mqlRes.steps.slice(2)]
    
    if (res.steps && res.steps.length > 0) {
      const last = res.steps[res.steps.length - 1]
      if (last) last.status = 'success'
    }
    res.steps.push({ title: '数据执行', content: '正在将 MQL 转换为 SQL 并执行查询...', status: 'loading' })
    await nextTick()
    scrollToBottom()

    // 步骤 3: 转换 SQL
    const sqlRes = await mql2sql(mqlRes.mql)
    res.sql = sqlRes.sql
    await nextTick()

    // 步骤 4: 执行并展示结果
    const queryRes = await executeSQL({ 
      sql: sqlRes.sql, 
      datasource_id: sqlRes.datasources[0] || ''
    })
    
    res.result = queryRes
    res.query_id = 'query_' + Date.now()
    
    res.steps.pop()
    res.steps.push({ title: '查询完成', content: '数据已成功检索。', status: 'success' })
    
    agentMsg.loading = false
    Message.success('查询成功')
    
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
  } catch (error) {
    console.error('Query execution error:', error)
    agentMsg.loading = false
    agentMsg.error = true
    if (agentMsg.queryResult && agentMsg.queryResult.steps) {
      const lastStep = agentMsg.queryResult.steps[agentMsg.queryResult.steps.length - 1]
      if (lastStep) lastStep.status = 'error'
    }
    Message.error('查询失败，流程中断')
  } finally {
    loading.value = false
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

function formatTimeRange(mql: any) {
  if (!mql) return '全部'
  
  let timeStr = ''
  let timeField = ''
  const tc = mql.timeConstraint
  
  // 1. Check timeConstraint
  if (tc && tc !== 'true' && tc !== '1=1') {
    // Extract field name from [field]
    const fieldMatch = tc.match(/\[(.*?)\]/)
    if (fieldMatch && fieldMatch[1]) {
      const rawField = fieldMatch[1]
      let fieldDisplayName = rawField
      
      if (rawField.includes('__')) {
        const parts = rawField.split('__')
        const baseName = parts[0] || ''
        const suffix = parts[1] || ''
        const dim = baseName ? findDimension(baseName) : null
        fieldDisplayName = dim ? `${dim.display_name || dim.name}(${suffix})` : rawField
      } else {
        const dim = findDimension(rawField)
        fieldDisplayName = dim ? (dim.display_name || dim.name) : rawField
      }
      timeField = fieldDisplayName
    }

    // Relative Time Patterns (LAST_N_YEARS, TODAY, etc.)
    if (tc.includes('LAST_N_YEARS')) {
      const match = tc.match(/LAST_N_YEARS\((\d+)\)/)
      if (match) timeStr = `最近${match[1]}年`
    } else if (tc.includes('LAST_N_MONTHS')) {
      const match = tc.match(/LAST_N_MONTHS\((\d+)\)/)
      if (match) timeStr = `最近${match[1]}个月`
    } else if (tc.includes('LAST_N_DAYS')) {
      const match = tc.match(/LAST_N_DAYS\((\d+)\)/)
      if (match) timeStr = `最近${match[1]}天`
    } else if (tc.includes('TODAY')) {
      const match = tc.match(/TODAY\(-(\d+)\)/)
      if (match) timeStr = `自${match[1]}天前至今`
      else timeStr = '今天'
    }

    // DateTrunc MONTH pattern
    if (!timeStr) {
      let match = tc.match(/DateTrunc\s*\(.*?\s*,\s*'MONTH'\s*\)\s*=\s*'(.*?)'/i)
      if (match) {
        const dateStr = match[1]
        timeStr = `${dateStr.substring(0, 4)}年${dateStr.substring(5, 7)}月`
      }
    }
    
    // DateTrunc YEAR pattern
    if (!timeStr) {
      let match = tc.match(/DateTrunc\s*\(.*?\s*,\s*'YEAR'\s*\)\s*=\s*'(.*?)'/i)
      if (match) {
        timeStr = `${match[1].substring(0, 4)}年`
      }
    }
    
    // BETWEEN pattern
    if (!timeStr) {
      let match = tc.match(/BETWEEN\s*'(.*?)'\s*AND\s*'(.*?)'/i)
      if (match) timeStr = `${match[1]} 至 ${match[2]}`
    }
    
    // Greater/Less than pattern
    if (!timeStr) {
      const gtMatch = tc.match(/>=\s*'(.*?)'/i)
      const ltMatch = tc.match(/<=\s*'(.*?)'/i)
      if (gtMatch && ltMatch) timeStr = `${gtMatch[1]} 至 ${ltMatch[1]}`
      else if (gtMatch) timeStr = `自 ${gtMatch[1]} 起`
      else if (ltMatch) timeStr = `至 ${ltMatch[1]} 止`
    }
    
    if (!timeStr) {
      // Fallback clean up
      timeStr = tc.replace(/\[|\]/g, '')
                 .replace(/DateTrunc\(.*?,/gi, '时间(')
                 .replace(/AddMonths\(.*?,/gi, '时间偏移(')
    }
  }

  // 2. Check filters for additional time constraints
  let filterParts: string[] = []
  if (mql.filters && mql.filters.length > 0) {
    mql.filters.forEach((f: string) => {
      if (f === 'true' || f === '1=1') return
      
      // Try to parse filter and make it readable
      let readableFilter = f.replace(/['"]/g, '')
      const fMatch = f.match(/^([a-zA-Z0-9_]+)\s*(>=|<=|>|<|=)\s*(.*)/)
      if (fMatch && fMatch[1] && fMatch[2] && fMatch[3]) {
        const col = fMatch[1]
        const dim = findDimension(col)
        const colName = dim ? (dim.display_name || dim.name) : col
        readableFilter = `${colName} ${fMatch[2]} ${fMatch[3].replace(/['"]/g, '')}`
      }
      filterParts.push(readableFilter)
    })
  }

  const finalParts = []
  if (timeField && timeStr) {
    finalParts.push(`${timeField}: ${timeStr}`)
  } else if (timeStr) {
    finalParts.push(timeStr)
  }
  
  if (filterParts.length > 0) {
    finalParts.push(filterParts.join('; '))
  }

  return finalParts.join('; ') || '全部'
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

function showAdjustment(result: FullQueryResponse) {
  activeQueryResult.value = result
  adjustmentVisible.value = true
  
  // 提取当前已选的指标和维度
  adjustmentForm.value.metrics = result.mql?.metrics || []
  adjustmentForm.value.dimensions = result.mql?.dimensions || []
  
  // 简单解析现有过滤条件
  adjustmentForm.value.filters = (result.mql?.filters || []).map((f: string) => {
    const parts = f.split(' ')
    return { field: parts[0] || '', op: parts[1] || '=', value: parts[2]?.replace(/'/g, '') || '' }
  })
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
  newMql.filters = adjustmentForm.value.filters
    .filter(f => f.field && f.value)
    .map(f => `${f.field} ${f.op} '${f.value}'`)
  
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
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #f2f3f5;
  flex-shrink: 0;
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

.result-meta-tags {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-3);
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.result-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f2f3f5;
  color: var(--color-text-4);
  font-size: 12px;
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
</style>