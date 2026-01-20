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
                      <a-button type="text" size="small"><template #icon><icon-share-internal /></template>引用</a-button>
                      <a-button type="text" size="small" @click="showDrillDown(msg.queryResult)"><template #icon><icon-apps /></template>维度细分</a-button>
                      <a-button type="text" size="small" @click="showAdjustment(msg.queryResult)"><template #icon><icon-settings /></template>调整查询</a-button>
                      <a-button type="text" size="small"><template #icon><icon-download /></template></a-button>
                      <a-button 
                        :type="msg.queryResult.viewType === 'chart' ? 'primary' : 'outline'" 
                        size="small"
                        @click="msg.queryResult.viewType = 'chart'"
                        :style="msg.queryResult.viewType === 'chart' ? {} : { color: '#4e5969' }"
                      >
                        <template #icon><icon-bar-chart /></template>
                      </a-button>
                      <a-button 
                        :type="msg.queryResult.viewType !== 'chart' ? 'primary' : 'outline'" 
                        size="small"
                        @click="msg.queryResult.viewType = 'table'"
                        :style="msg.queryResult.viewType !== 'chart' ? {} : { color: '#4e5969' }"
                      >
                        <template #icon><icon-table /></template>
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
                        <span class="meta-tag-link">{{ col }}</span>
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
                        <span class="meta-tag-link">{{ col }}</span>
                        <template #content>
                          <div class="metadata-popup">
                            <div v-if="col && findDimension(col)">
                              <div class="p-title">{{ findDimension(col)?.display_name || col }}</div>
                              <div class="p-desc">{{ findDimension(col)?.description || '暂无描述' }}</div>
                            </div>
                            <div v-else>未知维度</div>
                          </div>
                        </template>
                      </a-popover>
                    </a-space>
                  </span>
                </div>

                <div class="result-content-wrapper">
                <a-table
                  v-if="msg.queryResult.viewType !== 'chart'"
                  :columns="formatColumns(msg.queryResult.result.columns)"
                  :data="formatData(msg.queryResult.result)"
                  :pagination="false"
                  :bordered="false"
                  size="small"
                  :scroll="{ x: '100%', y: 400 }"
                />
                
                <ChartContainer
                  v-else
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useSettingsStore } from '@/stores/settings'
import ModelNotConfigured from '@/components/query/ModelNotConfigured.vue'
import QuerySteps from '@/components/query/QuerySteps.vue'
import ChartContainer from '@/components/common/ChartContainer.vue'
import type { FullQueryResponse, AnalysisStep } from '@/api/types'
import { analyzeIntent, generateMQL, mql2sql, executeSQL, getQueryHistoryDetail } from '@/api/query'
import { getMetrics, getDimensions } from '@/api/semantic'
import type { Metric, Dimension } from '@/api/types'

const settingsStore = useSettingsStore()
const route = useRoute()
const router = useRouter()

const queryInput = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const currentQueryTitle = ref('问数对话')

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

// 监听路由参数变化（加载历史或新建）
watch(() => route.query.id, (newId) => {
  if (newId) {
    loadHistorySession(newId as string)
  } else {
    clearSession()
  }
})

// 监听新建对话的时间戳
watch(() => route.query.t, () => {
  if (!route.query.id) {
    clearSession()
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
    
    // 如果有 SQL，尝试重新获取数据
    if (detail.sql_query && agentMsg.queryResult) {
      try {
        Message.info('正在加载历史数据...')
        // 尝试获取一个可用的数据源ID，或者后端mql2sql重新解析一次以获取数据源
        const sqlRes = await mql2sql(detail.mql_query)
        const datasource_id = sqlRes.datasources[0] || ''
        
        const queryRes = await executeSQL({ 
          sql: detail.sql_query, 
          datasource_id: datasource_id 
        })
        agentMsg.queryResult.result = queryRes
      } catch (e) {
        console.error('Failed to reload historical data:', e)
        Message.warning('历史数据加载失败，仅显示结构')
      }
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
  if (route.query.id) {
    loadHistorySession(route.query.id as string)
  }
  
  // 加载元数据用于调整查询
  try {
    const [m, d] = await Promise.all([getMetrics(), getDimensions()])
    allMetrics.value = m
    allDimensions.value = d
  } catch (e) {
    console.error('Failed to load metadata:', e)
  }
})

const loadingSteps: AnalysisStep[] = [
  { title: '意图识别', content: '正在识别意图...', status: 'loading' },
  { title: '指标检索', content: '正在检索指标...', status: 'pending' },
  { title: '指标查询', content: '正在执行查询...', status: 'pending' }
]

function formatColumns(cols: string[]) {
  if (!cols || cols.length === 0) return []
  return cols.map(col => ({
    title: col,
    dataIndex: col,
    align: 'right' as const,
    headerCellStyle: { background: '#f2f3f5' }
  }))
}

function formatData(result: any) {
  if (!result || !result.columns) return []
  const { columns, data } = result
  return data.map((row: any, index: number) => {
    const obj: Record<string, any> = { key: index }
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
        suggested_dimensions: intentRes.suggested_dimensions
      }
    })
    
    res.mql = mqlRes.mql
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

function formatTimeRange(mql: any) {
  if (!mql) return '全部'
  
  let timeStr = ''
  let timeField = ''
  const tc = mql.timeConstraint
  
  // 1. Check timeConstraint
  if (tc && tc !== 'true' && tc !== '1=1') {
    // Extract field name from [field]
    const fieldMatch = tc.match(/\[(.*?)\]/)
    if (fieldMatch) {
      const dim = findDimension(fieldMatch[1])
      timeField = dim ? (dim.display_name || dim.name) : fieldMatch[1]
    }

    // Relative Time Patterns (DateAdd)
    const dateAddMatch = tc.match(/DateAdd\s*\(\s*'(YEAR|MONTH|DAY)'\s*,\s*-(\d+)\s*,\s*CurrentDate\(\)\s*\)/i)
    if (dateAddMatch) {
      const unitMap: Record<string, string> = { 'YEAR': '年', 'MONTH': '个月', 'DAY': '天' }
      const unit = unitMap[dateAddMatch[1].toUpperCase()]
      timeStr = `近${dateAddMatch[2]}${unit}`
    }

    // DateTrunc MONTH pattern
    if (!timeStr) {
      let match = tc.match(/DateTrunc\s*\(.*?\s*,\s*'MONTH'\s*\)\s*=\s*'(.*?)'/i)
      if (match) {
        const date = new Date(match[1])
        timeStr = `${date.getFullYear()}年${date.getMonth() + 1}月`
      }
    }
    
    // DateTrunc YEAR pattern
    if (!timeStr) {
      let match = tc.match(/DateTrunc\s*\(.*?\s*,\s*'YEAR'\s*\)\s*=\s*'(.*?)'/i)
      if (match) {
        const date = new Date(match[1])
        timeStr = `${date.getFullYear()}年`
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
      timeStr = tc.replace(/\[|\]/g, '').replace(/DateTrunc\(.*?\)/gi, '时间')
    }
  }

  // 2. Check filters for additional time constraints if tc is empty or generic
  let filterTimeStr = ''
  if (mql.filters && mql.filters.length > 0) {
    const timeFilters = mql.filters.filter((f: string) => 
      f !== 'true' && f !== '1=1' &&
      /time|date|日期|时间/i.test(f) && /(>=|<=|>|<|BETWEEN|=)/i.test(f)
    )
    
    if (timeFilters.length > 0) {
      filterTimeStr = timeFilters.map((f: string) => {
        // Try to get field display name for filter too
        const fMatch = f.match(/^([a-zA-Z0-9_]+)/)
        let fName = ''
        if (fMatch && fMatch[1]) {
          const dim = findDimension(fMatch[1])
          fName = dim ? (dim.display_name || dim.name) : fMatch[1]
        }
        
        const val = f.replace(/['"]/g, '')
                    .replace(/^[a-zA-Z0-9_]+\s*/, '') // Remove physical col name from start
                    .trim()
        return fName ? `${fName} ${val}` : val
      }).join('; ')
    }
  }

  const finalTimeStr = [timeField ? `${timeField}: ${timeStr}` : timeStr, filterTimeStr].filter(Boolean).join('; ')
  return finalTimeStr || '全部'
}

// 维度细分
function showDrillDown(result: FullQueryResponse) {
  // 维度细分本质上是调整查询的一种快捷方式，这里可以跳转到调整弹窗并聚焦在维度上
  // 或者实现一个更简洁的弹窗。为了保持连贯，先复用调整弹窗
  showAdjustment(result)
}

// 调整查询
const adjustmentVisible = ref(false)
const activeQueryResult = ref<FullQueryResponse | null>(null)
const adjustmentForm = ref<{
  metrics: string[],
  dimensions: string[],
  filters: { field: string, op: string, value: string }[]
}>({
  metrics: [],
  dimensions: [],
  filters: []
})

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
  padding: 24px 15% 40px;
  background: #fff;
  flex-shrink: 0;
}

.input-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 8px;
  background: #fff;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.02);
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

:deep(.result-card .arco-card-header) {
  border-bottom: none;
  padding: 16px 20px 0;
}

:deep(.result-card .arco-card-body) {
  padding: 16px 20px;
}
</style>
