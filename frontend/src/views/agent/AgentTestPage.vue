<template>
  <div class="agent-page">
    <!-- 左侧侧边栏 -->
    <div class="agent-sidebar">
      <!-- Logo -->
      <div class="sidebar-header">
        <span class="logo-text">NL2MQL2SQL Agent</span>
      </div>

      <!-- 新建对话 -->
      <div class="new-chat-wrapper">
        <a-button type="primary" long class="new-chat-btn" @click="startNewConversation">
          <template #icon><icon-plus-circle-fill /></template>
          新建对话
        </a-button>
      </div>

      <!-- 历史查询 -->
      <div class="chat-history">
        <div class="history-group">
          <div class="group-title">历史查询</div>
          <div
            v-for="item in chatHistory"
            :key="item.conversation_id || item.id"
            class="history-item"
            :class="{ active: currentConversationId === (item.conversation_id || item.id) }"
            @click="loadHistorySession(item.conversation_id || item.id)"
          >
            {{ (item.natural_language || item.query || '').slice(0, 20) }}{{ (item.natural_language || item.query || '').length > 20 ? '...' : '' }}
          </div>
          <div v-if="chatHistory.length === 0" class="empty-history">暂无历史</div>
        </div>
      </div>

      <!-- 用户信息 -->
      <div class="user-info">
        <a-avatar :size="24">云轩</a-avatar>
        <span>向云轩</span>
      </div>
    </div>

    <!-- 右侧主内容区 -->
    <div class="agent-main">
      <!-- 顶部标题栏 -->
      <div class="agent-header">
        <span class="agent-title">{{ currentQueryTitle }}</span>
        <a-button type="primary" @click="openStatusModal" size="small">
          <template #icon><icon-menu /></template>
          Agent状态
        </a-button>
      </div>

      <!-- 消息列表 -->
      <div class="chat-container" ref="chatContainer">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.type">
          <!-- 用户消息 -->
          <div v-if="msg.type === 'user'" class="user-bubble">
            {{ msg.content }}
          </div>

          <!-- Agent消息 -->
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
                      <a-button type="text" size="small" @click="handleQuote(msg.queryResult.mql)">
                        <template #icon><icon-share-alt /></template>
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
                    :data="formatData(msg.queryResult.result)"
                    :pagination="false"
                    :bordered="false"
                    size="small"
                    :scroll="{ x: '100%', y: 400 }"
                    row-key="key"
                    :row-class-name="(record: any) => record.key === selectedRowKey ? 'arco-table-tr-checked' : ''"
                    @row-click="(record: any) => handleRowSelection(record, msg.queryResult)"
                    @row-contextmenu="(record: any, ev: MouseEvent) => handleRowContextMenu(record, msg.queryResult, ev)"
                  >
                    <template #actions="{ record }">
                      <a-dropdown @select="(val: any) => handleActionSelect(val, record, msg.queryResult)">
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
                </div>
                <div class="footer-right">
                  <a-button
                    type="outline"
                    size="small"
                    @click="handleGenerateApi(msg.queryResult)"
                  >
                    <template #icon><icon-thunderbolt /></template>
                    生成API
                  </a-button>
                </div>
              </div>
              </div>

              <!-- 洞察面板 -->
              <div class="insight-panel">
                <div class="insight-header">
                  <icon-bulb />
                  <span>数据洞察</span>
                </div>
                <div class="insight-content">
                  <div v-if="msg.queryResult.interpretation" class="insight-item">
                    {{ msg.queryResult.interpretation }}
                  </div>
                  <div v-else class="insight-placeholder">
                    <icon-info-circle />
                    <span>暂无数据分析洞察</span>
                  </div>
                </div>
              </div>
            </a-card>

            <!-- 错误信息 -->
            <a-alert v-if="msg.queryResult?.message && !msg.queryResult.success" type="error" style="margin-top: 12px;">
              {{ msg.queryResult.message }}
            </a-alert>
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
              :loading="queryLoading"
              @click="handleQuery"
              class="send-btn"
            >
              <template #icon><icon-send /></template>
            </a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent状态弹窗 -->
    <a-modal
      v-model:visible="showSkillsModal"
      title="Agent状态"
      width="900px"
      :footer="false"
    >
      <div class="skills-management">
        <!-- 状态概览 -->
        <a-row :gutter="16" style="margin-bottom: 20px;">
          <a-col :span="8">
            <a-card hoverable>
              <a-statistic
                title="Agent状态"
                :value="agentStatus.is_available ? 1 : 0"
                :value-style="{ color: agentStatus.is_available ? '#00B42A' : '#F53F3F' }"
              >
                <template #formatter>
                  <span>{{ agentStatus.is_available ? '可用' : '不可用' }}</span>
                </template>
                <template #suffix>
                  <icon-check-circle v-if="agentStatus.is_available" />
                  <icon-close-circle v-else />
                </template>
              </a-statistic>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card hoverable>
              <a-statistic title="模型配置" :value="agentStatus.model_configured ? 1 : 0">
                <template #formatter>
                  <span>{{ agentStatus.model_configured ? '已配置' : '未配置' }}</span>
                </template>
                <template #suffix>
                  <icon-check-circle v-if="agentStatus.model_configured" style="color: #00B42A" />
                  <icon-close-circle v-else style="color: #F53F3F" />
                </template>
              </a-statistic>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card hoverable>
              <a-statistic title="已加载Skills" :value="agentStatus.skills_loaded || 0" />
            </a-card>
          </a-col>
        </a-row>

        <!-- 模型信息 -->
        <a-card v-if="agentStatus.model_info" title="当前模型" style="margin-bottom: 20px;">
          <a-descriptions :column="2" bordered size="small">
            <a-descriptions-item label="配置名称">
              {{ agentStatus.model_info?.name || '-' }}
            </a-descriptions-item>
            <a-descriptions-item label="提供商">
              <a-tag v-if="agentStatus.model_info?.provider">{{ getModelProviderLabel(agentStatus.model_info.provider) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="模型名称">
              {{ agentStatus.model_info?.model_name || '-' }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-divider>技能配置</a-divider>

        <a-tabs type="line" default-active-key="code">
          <a-tab-pane key="code" title="代码技能">
            <div class="skills-list">
              <div
                v-for="skill in codeSkills"
                :key="skill.name"
                class="skill-item"
              >
                <div class="skill-info">
                  <div class="skill-header">
                    <icon-code style="color: #165DFF; margin-right: 8px;" />
                    <span class="skill-name">{{ skill.name }}</span>
                    <a-switch
                      v-model="skillStates[skill.name]"
                      :loading="skillLoading[skill.name]"
                      @change="(val) => toggleSkill(skill.name, val)"
                      style="margin-left: auto;"
                    />
                  </div>
                  <div class="skill-description">{{ skill.description }}</div>
                  <div class="skill-meta">
                    <a-tag v-for="dep in skill.dependencies" :key="dep" size="small" color="blue">
                      {{ dep }}
                    </a-tag>
                  </div>
                </div>
              </div>
            </div>
          </a-tab-pane>
          <a-tab-pane key="markdown" title="Markdown技能">
            <div class="skills-list">
              <div
                v-for="skill in markdownSkills"
                :key="skill.name"
                class="skill-item"
              >
                <div class="skill-info">
                  <div class="skill-header">
                    <icon-file style="color: #00B42A; margin-right: 8px;" />
                    <span class="skill-name">{{ skill.name }}</span>
                    <a-switch
                      v-model="skillStates[skill.name]"
                      :loading="skillLoading[skill.name]"
                      @change="(val) => toggleSkill(skill.name, val)"
                      style="margin-left: auto;"
                    />
                  </div>
                  <div class="skill-description">{{ skill.description }}</div>
                </div>
              </div>
            </div>
          </a-tab-pane>
          <a-tab-pane key="workflow" title="工作流">
            <div class="workflow-container">
              <a-empty v-if="!workflowInfo.nodes" description="工作流加载中..." />
              <div v-else class="workflow-graph">
                <div class="workflow-header">
                  <a-statistic-group direction="row">
                    <a-statistic :value="workflowInfo.total_nodes" title="节点数" />
                    <a-statistic :value="workflowInfo.total_edges" title="边数" />
                  </a-statistic-group>
                </div>
                <div class="workflow-nodes">
                  <div
                    v-for="node in workflowInfo.nodes"
                    :key="node.name"
                    class="workflow-node"
                  >
                    <a-card size="small" :bordered="true">
                      <template #title>
                        <a-space>
                          <icon-tool />
                          {{ node.name }}
                        </a-space>
                      </template>
                      <a-tag color="arcoblue">Node</a-tag>
                    </a-card>
                  </div>
                </div>
                <div class="workflow-edges">
                  <a-descriptions :column="1" bordered size="small">
                    <a-descriptions-item
                      v-for="(edge, index) in workflowInfo.edges"
                      :key="index"
                      :label="`步骤 ${index + 1}`"
                    >
                      <a-space>
                        <span>{{ edge.from }}</span>
                        <icon-arrow-right />
                        <span>{{ edge.to }}</span>
                      </a-space>
                    </a-descriptions-item>
                  </a-descriptions>
                </div>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconCheckCircle,
  IconCloseCircle,
  IconCode,
  IconFile,
  IconArrowRight,
  IconTool,
  IconBulb,
  IconMenu,
  IconPlusCircleFill,
  IconSend,
  IconDownload,
  IconMosaic,
  IconDriveFile,
  IconInfoCircle,
  IconShareAlt,
  IconPlusCircle,
  IconSettings,
  IconMore,
  IconLayers,
  IconThunderbolt
} from '@arco-design/web-vue/es/icon'
import QuerySteps from '@/components/query/QuerySteps.vue'
import ChartContainer from '@/components/common/ChartContainer.vue'

// API调用
import axios from 'axios'

const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api/v1'}/agent`

// 打开状态弹窗时刷新状态
async function openStatusModal() {
  await checkStatus()
  await loadSkills()
  await loadWorkflowInfo()
  showSkillsModal.value = true
}

// 对话相关状态
interface MessageItem {
  type: 'user' | 'agent'
  content: string
  queryResult?: any
  loading?: boolean
  stepsExpanded?: boolean
}

const messages = ref<MessageItem[]>([])
const chatContainer = ref<HTMLElement | null>(null)
const currentQueryTitle = ref('新对话')
const currentConversationId = ref<string | null>(null)
const chatHistory = ref<any[]>([])
const loadingSteps = ref<any[]>([])

// 状态
const statusLoading = ref(false)
const queryLoading = ref(false)
const showSkillsModal = ref(false)
const queryInput = ref('')
const queryResult = ref<any>(null)

// 技能状态管理
const skillStates = ref<Record<string, boolean>>({})
const skillLoading = ref<Record<string, boolean>>({})

const agentStatus = ref({
  is_available: false,
  model_configured: false,
  model_info: null as { name?: string; provider?: string; model_name?: string } | null,
  skills_loaded: 0
})

const codeSkills = ref<Array<{name: string, description: string, dependencies?: string[], enabled?: boolean}>>([])
const markdownSkills = ref<Array<{name: string, description: string, enabled?: boolean}>>([])
const workflowInfo = ref<{
  nodes: any[];
  edges: any[];
  total_nodes: number;
  total_edges: number
}>({
  nodes: [],
  edges: [],
  total_nodes: 0,
  total_edges: 0
})

// 结果面板相关状态
const selectedRowKey = ref<string | null>(null)
const selectedRecord = ref<any>(null)
const activeQueryResult = ref<any>(null)

// 获取模型提供商标签
function getModelProviderLabel(provider: string) {
  const labels: Record<string, string> = {
    openai: 'OpenAI',
    ollama: 'Ollama',
    azure: 'Azure OpenAI',
    custom: '自定义'
  }
  return labels[provider] || provider
}

// 格式化数据
function formatData(result: any) {
  if (!result || !result.columns) return []
  const { columns, data } = result
  return data.map((row: any, index: number) => {
    const obj: Record<string, any> = { key: `r_${index}` }
    columns.forEach((col: string, i: number) => {
      obj[col] = row[i]
    })
    return obj
  })
}

// 格式化表格列
function formatColumns(cols: string[]) {
  if (!cols || cols.length === 0) return []
  const result = cols.map(col => {
    let title = col
    if (col && col.includes('__')) {
      const parts = col.split('__')
      const baseName = parts[0] || ''
      const suffix = parts[1] || ''
      title = `${baseName}(${suffix})`
    }
    return {
      title: title,
      dataIndex: col,
      align: 'right' as const,
      headerCellStyle: { background: '#f2f3f5' }
    }
  })
  // 添加操作列
  result.push({
    title: '操作',
    slotName: 'actions',
    width: 80,
    fixed: 'right',
    align: 'center'
  } as any)
  return result
}

// 查找指标
function findMetric(name: string) {
  return {
    name: name,
    display_name: name,
    description: '',
    calculation_formula: ''
  }
}

// 查找维度
function findDimension(name: string) {
  return {
    name: name,
    display_name: name,
    description: ''
  }
}

// 获取指标列
function getMetricsFromCols(res: any) {
  if (!res || !res.result || !res.result.columns) return []
  const mqlMetrics = res.mql?.metrics || []
  return res.result.columns.filter((col: string) => mqlMetrics.includes(col))
}

// 获取维度列
function getDimensionsFromCols(res: any) {
  if (!res || !res.result || !res.result.columns) return []
  const mqlDims = res.mql?.dimensions || []
  return res.result.columns.filter((col: string) => mqlDims.includes(col))
}

// 格式化时间范围
function formatTimeRange(mql: any) {
  if (!mql) return '全部'
  return mql.timeConstraint || '全部'
}

// 格式化过滤条件显示
function formatFilterDisplay(filterStr: string) {
  if (!filterStr) return ''
  const match = filterStr.match(/\[(.*?)\]\s*(.*)/)
  if (match) {
    return `${match[1]} ${match[2]}`
  }
  return filterStr
}

// 行选择处理
function handleRowSelection(record: any, result?: any) {
  if (!record || !result) return
  selectedRowKey.value = record.key
  selectedRecord.value = record
  activeQueryResult.value = result
}

// 右键菜单
function handleRowContextMenu(record: any, result: any, ev: MouseEvent) {
  ev.preventDefault()
  handleRowSelection(record, result)
  Message.info('右键菜单功能')
}

// 操作选择
function handleActionSelect(val: any, record: any, result: any) {
  handleRowSelection(record, result)
  if (val === 'drill') {
    Message.info('下钻分析功能')
  }
}

// 引用MQL
function handleQuote(_mql: any) {
  Message.info('引用MQL功能')
}

// 维度细分
function showGlobalAddDimension(result: any) {
  activeQueryResult.value = result
  selectedRecord.value = null
  selectedRowKey.value = null
  Message.info('维度细分功能')
}

// 调整查询
function showAdjustment(result: any) {
  activeQueryResult.value = result
  Message.info('调整查询功能')
}

// 生成API
function handleGenerateApi(_result: any) {
  Message.info('生成API功能')
}

// 检查Agent状态
async function checkStatus() {
  statusLoading.value = true
  try {
    const response = await axios.get(`${API_BASE}/status`)
    agentStatus.value = response.data
    Message.success('状态检查成功')
  } catch (error: any) {
    Message.error(`状态检查失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    statusLoading.value = false
  }
}

// 加载Skills
async function loadSkills() {
  try {
    const response = await axios.get(`${API_BASE}/skills`)
    codeSkills.value = response.data.code_skills || []
    markdownSkills.value = response.data.markdown_skills || []

    // 初始化技能状态
    codeSkills.value.forEach(skill => {
      skillStates.value[skill.name] = skill.enabled !== false
      skillLoading.value[skill.name] = false
    })
    markdownSkills.value.forEach(skill => {
      skillStates.value[skill.name] = skill.enabled !== false
      skillLoading.value[skill.name] = false
    })
  } catch (error: any) {
    Message.error(`Skills加载失败: ${error.response?.data?.detail || error.message}`)
  }
}

// 切换技能状态
async function toggleSkill(skillName: string, value: string | number | boolean) {
  const enabled = Boolean(value)
  skillLoading.value[skillName] = true
  try {
    await axios.post(`${API_BASE}/skills/toggle`, {
      skill_name: skillName,
      enabled: enabled
    })
    Message.success(`${skillName}已${enabled ? '启用' : '禁用'}`)
  } catch (error: any) {
    // 回滚状态
    skillStates.value[skillName] = !enabled
    Message.error(`操作失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    skillLoading.value[skillName] = false
  }
}

// 加载工作流信息
async function loadWorkflowInfo() {
  try {
    const response = await axios.get(`${API_BASE}/workflow`)
    workflowInfo.value = response.data
  } catch (error: any) {
    Message.error(`工作流加载失败: ${error.response?.data?.detail || error.message}`)
  }
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 开始新对话
async function startNewConversation() {
  messages.value = []
  currentQueryTitle.value = '新对话'
  currentConversationId.value = null
  queryInput.value = ''
  queryResult.value = null
}

// 加载历史会话
async function loadHistorySession(id: string) {
  queryLoading.value = true
  try {
    const response = await axios.get(`${API_BASE}/history/${id}`)
    if (response.data) {
      currentConversationId.value = id
      currentQueryTitle.value = (response.data.natural_language || '').slice(0, 15) || '历史对话'
      messages.value = [
        { type: 'user', content: response.data.natural_language },
        {
          type: 'agent',
          content: '',
          queryResult: {
            mql: response.data.mql_query,
            sql: response.data.sql_query,
            result: response.data.result,
            steps: response.data.steps || []
          },
          stepsExpanded: false
        }
      ]
    }
  } catch (error: any) {
    Message.error('加载历史失败')
    console.error('Load history error:', error)
  } finally {
    queryLoading.value = false
  }
}

// 加载对话历史列表
async function loadChatHistory() {
  try {
    const response = await axios.get(`${API_BASE}/history`)
    chatHistory.value = response.data || []
  } catch (error: any) {
    console.error('Load chat history error:', error)
    chatHistory.value = []
  }
}

// 处理回车发送
function handleEnter(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    handleQuery()
  }
}

// 发送查询
async function handleQuery() {
  if (!queryInput.value.trim() || queryLoading.value) return

  const userQuestion = queryInput.value
  messages.value.push({ type: 'user', content: userQuestion })
  queryInput.value = ''

  // 添加 agent 消息占位
  const agentMsg: MessageItem = {
    type: 'agent',
    content: '',
    loading: true,
    queryResult: {},
    stepsExpanded: true
  }
  messages.value.push(agentMsg)

  scrollToBottom()

  queryLoading.value = true

  try {
    const response = await fetch(`${API_BASE}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        natural_language: userQuestion,
        context: {},
        user_id: 'test_user'
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let currentEventType = ''
    let resultData: any = {}

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEventType = line.replace('event:', '').trim()
        } else if (line.startsWith('data:')) {
          const dataStr = line.replace('data:', '').trim()
          if (!dataStr || !currentEventType) continue

          try {
            const data = JSON.parse(dataStr)
            if (currentEventType === 'step') {
              loadingSteps.value.push(data)
            } else if (currentEventType === 'result') {
              resultData = data
            } else if (currentEventType === 'error') {
              agentMsg.queryResult = {
                success: false,
                message: data.message
              }
            }
          } catch (e) {
            console.error('[SSE Parse Error]:', e)
          }
          currentEventType = ''
        }
      }
    }

    // 更新结果
    agentMsg.queryResult = {
      success: true,
      mql: resultData.mql,
      sql: resultData.sql,
      result: resultData.result,
      interpretation: resultData.interpretation,
      steps: loadingSteps.value,
      viewType: 'table',
      query_id: 'agent_' + Date.now()
    }
    agentMsg.loading = false
    loadingSteps.value = []

  } catch (error: any) {
    console.error('[Query Error]:', error)
    agentMsg.queryResult = {
      success: false,
      message: error.message
    }
    agentMsg.loading = false
  } finally {
    queryLoading.value = false
    scrollToBottom()
  }
}

// 组件卸载时
onUnmounted(() => {
  // 清理工作
})

// 初始化
onMounted(async () => {
  await startNewConversation()
  await loadChatHistory()
  await checkStatus()
  await loadSkills()
  await loadWorkflowInfo()
})

</script>

<style scoped>
.agent-page {
  display: flex;
  height: 100vh;
  background: #f7f8fa;
}

/* 侧边栏样式 */
.agent-sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e5e6eb;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #f2f3f5;
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text-1);
}

.new-chat-wrapper {
  padding: 12px 16px;
}

.new-chat-btn {
  width: 100%;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.history-group {
  padding: 8px 0;
}

.group-title {
  font-size: 12px;
  color: var(--color-text-3);
  padding: 4px 8px;
  margin-bottom: 8px;
}

.history-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item:hover {
  background: #f2f3f5;
}

.history-item.active {
  background: #e8f3ff;
  color: #165dff;
}

.empty-history {
  padding: 16px;
  text-align: center;
  color: var(--color-text-3);
  font-size: 13px;
}

.user-info {
  padding: 12px 16px;
  border-top: 1px solid #e5e6eb;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

/* 主内容区 */
.agent-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

.agent-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #f2f3f5;
  flex-shrink: 0;
}

.agent-title {
  font-weight: 600;
  color: var(--color-text-1);
}

/* 消息列表 */
.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 10% 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.message-item {
  display: flex;
  flex-direction: column;
}

.message-item.user {
  align-items: flex-end;
}

.message-item.agent {
  align-items: flex-start;
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

/* 结果卡片样式 */
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

/* 洞察面板样式 */
.insight-panel {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f2f3f5;
}

.insight-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 12px;
}

.insight-header svg {
  color: #ff7d00;
}

.insight-content {
  padding: 12px;
  background: #fff7e8;
  border-radius: 6px;
  border-left: 3px solid #ff7d00;
}

.insight-item {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-2);
}

.insight-placeholder {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-3);
}

.insight-placeholder svg {
  font-size: 14px;
}

/* 输入框 */
.input-container {
  padding: 16px 15% 40px;
  background: #fff;
  flex-shrink: 0;
  border-top: 1px solid #f2f3f5;
}

.input-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 0 0 12px 12px;
  padding: 8px;
  background: #fff;
  box-shadow: 0 4px 10px rgba(0,0,0,0.02);
}

.query-input {
  border: none !important;
  background: transparent !important;
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

/* 其他样式 */
.code-block {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* 技能管理样式 */
.skills-management {
  padding: 8px 0;
}

.skills-list {
  max-height: 500px;
  overflow-y: auto;
}

.skill-item {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.skill-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(22, 93, 255, 0.1);
}

.skill-info {
  width: 100%;
}

.skill-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.skill-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-1);
}

.skill-description {
  color: var(--color-text-2);
  font-size: 13px;
  margin-bottom: 8px;
  line-height: 1.5;
}

.skill-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.workflow-container {
  padding: 20px;
}

.workflow-graph {
  max-height: 600px;
  overflow-y: auto;
}

.workflow-header {
  margin-bottom: 20px;
  text-align: center;
}

.workflow-nodes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.workflow-node {
  transition: transform 0.3s;
}

.workflow-node:hover {
  transform: translateY(-4px);
}

.selected-example {
  background-color: #e6f7ff;
}

/* 深度样式 */
::deep(.arco-textarea) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

::deep(.arco-table-th) {
  font-weight: 600;
}

/* 选中行的高亮样式 */
::deep(.arco-table-tr.arco-table-tr-checked),
::deep(.arco-table-tr.arco-table-tr-checked:hover) {
  background-color: var(--color-primary-light-1) !important;
}

::deep(.arco-table-tr.arco-table-tr-checked td),
::deep(.arco-table-tr.arco-table-tr-checked:hover td) {
  background-color: var(--color-primary-light-1) !important;
}

::deep(.result-card .arco-card-header) {
  border-bottom: none;
  padding: 16px 20px 0;
}

::deep(.result-card .arco-card-body) {
  padding: 16px 20px;
}
</style>
