<template>
  <a-layout class="main-layout">
    <!-- 侧边栏 -->
    <a-layout-sider
      :collapsed="appStore.sidebarCollapsed"
      :width="260"
      :collapsed-width="48"
      collapsible
      breakpoint="lg"
      @collapse="appStore.toggleSidebar"
      class="sidebar-sider"
    >
      <!-- Logo -->
      <div class="logo">
        <span v-if="!appStore.sidebarCollapsed" class="logo-text">NL2MQL2SQL Agent</span>
        <icon-menu-unfold v-if="appStore.sidebarCollapsed" @click="appStore.toggleSidebar" />
        <icon-menu-fold v-else class="fold-icon" @click="appStore.toggleSidebar" />
      </div>

      <!-- 问数页面特有侧边栏 -->
      <template v-if="(route.name === 'Query' || route.name === 'AgentQuery') && !appStore.sidebarCollapsed && showAgentSidebar">
        <div class="sidebar-header-actions">
          <a-button type="text" size="small" @click="toggleSidebarMode">
            <template #icon><icon-left /></template>
            返回导航
          </a-button>
        </div>

        <div class="new-chat-wrapper">
          <a-button type="primary" long class="new-chat-btn" @click="handleNewChat">
            <template #icon><icon-plus-circle-fill /></template>
            新建对话
          </a-button>
        </div>

        <div class="chat-history">
          <div class="history-group">
            <div class="group-title">历史查询</div>
            <div 
              v-for="item in chatHistory" 
              :key="item.conversation_id || item.id" 
              class="history-item"
              :class="{ active: route.query.id === item.conversation_id || route.query.id === item.id }"
              @click="handleHistoryClick(item.conversation_id || item.id)"
            >
              {{ item.natural_language.slice(0, 20) }}{{ item.natural_language.length > 20 ? '...' : '' }}
            </div>
            <div v-if="chatHistory.length === 0" class="empty-history">暂无历史</div>
          </div>
        </div>

        <div class="user-info">
          <a-avatar :size="24">云轩</a-avatar>
          <span class="user-name">向云轩</span>
          <a-button type="text" size="small" class="settings-btn" @click="openSettings">
            <template #icon><icon-settings /></template>
          </a-button>
        </div>
      </template>

      <!-- 导航菜单 (非问数页面或折叠时显示) -->
      <a-menu
        v-else
        :selected-keys="selectedKeys"
        v-model:open-keys="openKeys"
        :auto-open-selected="true"
        :accordion="false"
        @menu-item-click="handleMenuClick"
      >
        <a-menu-item v-if="route.name === 'Query'" key="toggle" @click="toggleSidebarMode">
          <template #icon><icon-apps /></template>
          返回 Agent 视图
        </a-menu-item>
        <!-- 智能问数 -->
        <a-menu-item key="Query">
          <template #icon><icon-search /></template>
          智能问数
        </a-menu-item>
        <a-menu-item key="AgentQuery">
          <template #icon><icon-thunderbolt /></template>
          Agent查询
        </a-menu-item>
        <a-menu-item key="QueryHistory">
          <template #icon><icon-history /></template>
          查询历史
        </a-menu-item>

        <a-divider style="margin: 8px 0" />

        <!-- 语义层管理 -->
        <a-sub-menu key="Semantic">
          <template #icon><icon-layers /></template>
          <template #title>语义层管理</template>
          <a-menu-item key="DataSources">数据源管理</a-menu-item>
          <a-menu-item key="Datasets">物理表管理</a-menu-item>
          <a-menu-item key="Views">视图管理</a-menu-item>
          <a-menu-item key="Metrics">指标管理</a-menu-item>
          <a-menu-item key="Dimensions">维度管理</a-menu-item>
          <a-menu-item key="Dictionaries">字典管理</a-menu-item>
          <a-menu-item key="Lineage">血缘管理</a-menu-item>
        </a-sub-menu>

        <!-- 系统设置 -->
        <a-sub-menu key="Settings">
          <template #icon><icon-settings /></template>
          <template #title>系统设置</template>
          <a-menu-item key="ModelConfig">模型配置</a-menu-item>
          <a-menu-item key="QueryConfig">问数配置</a-menu-item>
          <a-menu-item key="AgentTest">Agent测试</a-menu-item>
        </a-sub-menu>

        <a-divider style="margin: 8px 0" />

        <!-- AIR模块 -->
        <a-sub-menu key="Air">
          <template #icon><icon-cloud /></template>
          <template #title>AIR</template>
          <a-menu-item key="Workbook">工作簿</a-menu-item>
          <a-menu-item key="Integration">数据集成</a-menu-item>
          <a-menu-item key="Consolidation">数据整合</a-menu-item>
          <a-menu-item key="AirAcceleration">数据加速</a-menu-item>
        </a-sub-menu>

        <!-- CAN模块 -->
        <a-sub-menu key="Can">
          <template #icon><icon-bar-chart /></template>
          <template #title>CAN</template>
          <a-menu-item key="Catalog">指标目录</a-menu-item>
          <a-menu-item key="Application">指标应用</a-menu-item>
          <a-menu-item key="CanAcceleration">指标加速</a-menu-item>
          <a-menu-item key="CanSettings">管理设置</a-menu-item>
        </a-sub-menu>

        <!-- BIG模块 -->
        <a-sub-menu key="Big">
          <template #icon><icon-branch /></template>
          <template #title>BIG</template>
          <a-menu-item key="OperatorLineage">算子级血缘</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <!-- 主内容区 -->
    <a-layout>
      <!-- 顶部栏 -->
      <a-layout-header class="layout-header">
        <div class="header-left">
          <a-breadcrumb>
            <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              <router-link v-if="item.path" :to="item.path">{{ item.title }}</router-link>
              <span v-else>{{ item.title }}</span>
            </a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 模型配置状态提示 -->
          <a-tooltip v-if="!settingsStore.isModelConfigured" content="AI模型未配置，点击前往配置">
            <a-button type="text" status="warning" @click="goToModelConfig">
              <template #icon><icon-exclamation-circle /></template>
              模型未配置
            </a-button>
          </a-tooltip>
          <a-tooltip v-else-if="!settingsStore.isModelAvailable" content="AI模型已配置但不可用，点击前往配置">
            <a-button type="text" status="warning" @click="goToModelConfig">
              <template #icon><icon-exclamation-circle /></template>
              模型不可用
            </a-button>
          </a-tooltip>
          <a-tooltip v-else content="AI模型已配置且可用">
            <a-button type="text" status="success">
              <template #icon><icon-check-circle /></template>
              模型已就绪
            </a-button>
          </a-tooltip>
        </div>
      </a-layout-header>

      <!-- 内容区 -->
      <a-layout-content class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </a-layout-content>
    </a-layout>
  </a-layout>

  <!-- 设置弹窗 -->
  <a-modal
    v-model:visible="settingsVisible"
    title="设置"
    :width="1100"
    :footer="false"
    @cancel="closeSettings"
    class="settings-modal"
  >
    <div class="settings-content">
      <!-- 左侧：通用设置 -->
      <div class="settings-left">
        <div class="user-profile">
          <a-avatar :size="80">云轩</a-avatar>
          <h3 class="profile-name">向云轩</h3>
          <p class="profile-role">数据分析专家</p>
        </div>

        <a-divider style="margin: 16px 0;" />

        <div class="profile-settings">
          <a-form layout="vertical">
            <a-form-item label="头像">
              <a-input v-model="userProfile.avatar" placeholder="输入头像URL" />
            </a-form-item>
            <a-form-item label="用户名">
              <a-input v-model="userProfile.name" placeholder="输入用户名" />
            </a-form-item>
          </a-form>
        </div>
      </div>

      <!-- 右侧：分标签设置 -->
      <div class="settings-right">
        <a-tabs v-model:active-key="activeTab" type="line">
          <!-- 智能体状态 -->
          <a-tab-pane key="status" title="智能体状态">
            <div class="status-panel">
              <a-descriptions :column="2" bordered>
                <a-descriptions-item label="Agent状态">
                  <a-tag :color="agentStatus.color">{{ agentStatus.text }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="当前模型">
                  {{ agentStatus.currentModel || '未配置' }}
                </a-descriptions-item>
                <a-descriptions-item label="已加载Skills">
                  {{ agentStatus.loadedSkills || 0 }} 个
                </a-descriptions-item>
                <a-descriptions-item label="核心工具">
                  {{ agentStatus.coreTools || 8 }} 个
                </a-descriptions-item>
              </a-descriptions>

              <a-divider style="margin: 24px 0;" />

              <!-- Agent 信息 -->
              <h4>Agent 信息</h4>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="工具总数">
                  {{ agentInfo.totalTools || 0 }} 个
                </a-descriptions-item>
                <a-descriptions-item label="工具路径">
                  <a-tag color="blue" size="small">
                    {{ agentInfo.skillPaths?.length || 0 }} 个路径
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="启用技能">
                  {{ agentInfo.enabledSkills || 0 }} 个
                </a-descriptions-item>
                <a-descriptions-item label="健康状态">
                  <a-tag :color="agentInfo.healthy ? 'green' : 'red'">
                    {{ agentInfo.healthy ? '正常' : '异常' }}
                  </a-tag>
                </a-descriptions-item>
              </a-descriptions>

              <a-divider style="margin: 24px 0;" />

              <h4>模型配置</h4>
              <a-form layout="vertical">
                <a-row :gutter="16">
                  <a-col :span="12">
                    <a-form-item label="LLM模型">
                      <a-select v-model="modelConfig.llmModel" placeholder="选择模型">
                        <a-option value="gpt-4">GPT-4</a-option>
                        <a-option value="gpt-3.5-turbo">GPT-3.5 Turbo</a-option>
                        <a-option value="claude-3">Claude-3</a-option>
                      </a-select>
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item label="温度">
                      <a-slider v-model="modelConfig.temperature" :min="0" :max="1" :step="0.1" />
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-row :gutter="16">
                  <a-col :span="12">
                    <a-form-item label="最大重试次数">
                      <a-input-number v-model="modelConfig.maxRetries" :min="1" :max="10" />
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item label="超时时间（秒）">
                      <a-input-number v-model="modelConfig.timeout" :min="10" :max="300" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>

              <div style="text-align: right; margin-top: 16px;">
                <a-button type="primary" @click="saveModelConfig">
                  保存配置
                </a-button>
              </div>
            </div>
          </a-tab-pane>

          <!-- 技能管理 -->
          <a-tab-pane key="skills" title="技能管理">
            <div class="skills-panel">
              <a-tabs v-model:active-key="skillsTab" type="card-gutter">
                <!-- 核心技能 -->
                <a-tab-pane key="core" title="核心技能">
                  <div class="skills-list">
                    <a-alert
                      type="info"
                      content="核心技能是系统内置的基础工具，不可关闭或删除"
                      style="margin-bottom: 16px;"
                    />
                    <a-list :data="coreSkills" size="small">
                      <template #item="{ item }">
                        <a-list-item>
                          <a-list-item-meta :title="item.name" :description="item.description">
                            <template #avatar>
                              <icon-tool :size="24" style="color: rgb(var(--primary-6))" />
                            </template>
                          </a-list-item-meta>
                          <template #actions>
                            <a-tag color="arcoblue">核心</a-tag>
                          </template>
                        </a-list-item>
                      </template>
                    </a-list>
                  </div>
                </a-tab-pane>

                <!-- 外部技能 -->
                <a-tab-pane key="external" title="外部技能">
                  <div class="external-skills-section">
                    <!-- 操作栏 -->
                    <div class="skills-toolbar">
                      <a-space>
                        <a-button type="primary" @click="openLoadSkillModal">
                          <template #icon>
                            <icon-plus />
                          </template>
                          加载技能
                        </a-button>
                        <a-button @click="refreshSkillsList">
                          <template #icon>
                            <icon-refresh />
                          </template>
                          刷新
                        </a-button>
                        <a-button status="danger" @click="unloadAllSkills" :disabled="externalSkills.length === 0">
                          <template #icon>
                            <icon-delete />
                          </template>
                          卸载全部
                        </a-button>
                        <a-input-search
                          v-model="skillSearch"
                          placeholder="搜索技能"
                          style="width: 200px;"
                          @search="filterSkills"
                        />
                      </a-space>
                      <a-space>
                        <span class="skills-count">
                          已加载: {{ externalSkills.length }} 个
                        </span>
                      </a-space>
                    </div>

                    <!-- 技能列表 -->
                    <a-spin :loading="skillsLoading">
                      <div v-if="externalSkills.length === 0" class="empty-skills">
                        <a-empty description="暂无外部技能，请点击加载技能添加">
                          <template #image>
                            <icon-file :size="64" style="color: #c9cdd4;" />
                          </template>
                        </a-empty>
                      </div>
                      <a-list v-else :data="filteredExternalSkills" size="small" class="skills-list">
                        <template #item="{ item }">
                          <a-list-item @click="showSkillDetail(item)" style="cursor: pointer;">
                            <a-list-item-meta
                              :title="item.name || item.skill_id"
                              :description="item.description || item.skill_id"
                            >
                              <template #avatar>
                                <icon-apps :size="24" :style="{ color: item.enabled ? 'rgb(var(--success-6))' : '#c9cdd4' }" />
                              </template>
                            </a-list-item-meta>
                            <template #actions>
                              <a-switch
                                v-model="item.enabled"
                                :loading="item.switching"
                                @click.stop="toggleSkill(item)"
                              />
                              <a-button
                                type="text"
                                status="danger"
                                size="small"
                                @click.stop="unloadSkill(item.skill_id)"
                              >
                                <template #icon>
                                  <icon-delete />
                                </template>
                              </a-button>
                            </template>
                          </a-list-item>
                        </template>
                      </a-list>
                    </a-spin>
                  </div>
                </a-tab-pane>
              </a-tabs>
            </div>
          </a-tab-pane>

          <!-- 关于我们 -->
          <a-tab-pane key="about" title="关于我们">
            <div class="about-panel">
              <div class="about-header">
                <h3>智能问数系统</h3>
                <p class="version">版本: v1.0.0</p>
              </div>

              <a-divider />

              <div class="about-content">
                <h4>系统简介</h4>
                <p>
                  智能问数系统是一个基于 LangChain Deep Agents 的数据分析平台，
                  支持自然语言查询、动态技能加载和流式结果展示。
                </p>

                <h4>核心功能</h4>
                <ul>
                  <li>自然语言查询：用日常语言提问，系统自动转换为查询</li>
                  <li>流式输出：实时展示查询步骤和结果</li>
                  <li>动态技能：运行时加载、卸载外部技能</li>
                  <li>多数据源支持：支持多种数据库和数据源</li>
                </ul>

                <h4>技术栈</h4>
                <a-space wrap>
                  <a-tag color="arcoblue">Vue 3</a-tag>
                  <a-tag color="arcoblue">TypeScript</a-tag>
                  <a-tag color="arcoblue">Arco Design</a-tag>
                  <a-tag color="green">Python</a-tag>
                  <a-tag color="green">FastAPI</a-tag>
                  <a-tag color="orange">LangChain</a-tag>
                  <a-tag color="orange">Deep Agents</a-tag>
                </a-space>
              </div>

              <a-divider />

              <div class="about-footer">
                <p>© 2026 Qoder. All rights reserved.</p>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>
  </a-modal>

  <!-- 加载技能弹窗 -->
  <a-modal
    v-model:visible="loadSkillModalVisible"
    title="加载外部技能"
    :width="600"
    @ok="handleLoadSkill"
    @cancel="closeLoadSkillModal"
  >
    <a-form layout="vertical">
      <a-form-item label="加载方式">
        <a-radio-group v-model="loadSkillMethod">
          <a-radio value="directory">从目录加载</a-radio>
          <a-radio value="url">从URL加载</a-radio>
        </a-radio-group>
      </a-form-item>

      <a-form-item v-if="loadSkillMethod === 'directory'" label="目录路径">
        <a-input
          v-model="loadSkillForm.directory"
          placeholder="例如: backend/app/agents/external_skills"
        />
      </a-form-item>

      <a-form-item v-if="loadSkillMethod === 'url'" label="技能ID">
        <a-input v-model="loadSkillForm.skill_id" placeholder="例如: web-search" />
      </a-form-item>

      <a-form-item v-if="loadSkillMethod === 'url'" label="URL">
        <a-input
          v-model="loadSkillForm.url"
          placeholder="https://example.com/skill/SKILL.md"
        />
      </a-form-item>

      <a-form-item>
        <a-checkbox v-model="loadSkillForm.force_reload">
          强制重新加载（如果已存在）
        </a-checkbox>
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- 技能详情弹窗 -->
  <a-modal
    v-model:visible="skillDetailVisible"
    :title="`技能详情 - ${currentSkill?.name || currentSkill?.skill_id}`"
    :width="800"
    :footer="false"
    @cancel="skillDetailVisible = false"
  >
    <div v-if="currentSkill" class="skill-detail">
      <a-descriptions :column="2" bordered>
        <a-descriptions-item label="技能ID">
          {{ currentSkill.skill_id }}
        </a-descriptions-item>
        <a-descriptions-item label="名称">
          {{ currentSkill.name }}
        </a-descriptions-item>
        <a-descriptions-item label="来源" span="2">
          <a-tag :color="currentSkill.source === 'url' ? 'blue' : 'green'">
            {{ currentSkill.source === 'url' ? 'URL加载' : '本地加载' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="描述" span="2">
          {{ currentSkill.description || '暂无描述' }}
        </a-descriptions-item>
        <a-descriptions-item label="加载时间">
          {{ currentSkill.loaded_at || '未知' }}
        </a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="currentSkill.enabled ? 'green' : 'red'">
            {{ currentSkill.enabled ? '已启用' : '已禁用' }}
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>

      <a-divider />

      <h4>元数据</h4>
      <a-card size="small" style="background: #f7f8fa;">
        <pre style="white-space: pre-wrap; word-break: break-all;">{{ JSON.stringify(currentSkill.metadata || {}, null, 2) }}</pre>
      </a-card>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useSettingsStore } from '@/stores/settings'
import { getQueryHistory } from '@/api/query'
import type { QueryHistory } from '@/api/types'
import { Message, Modal } from '@arco-design/web-vue'
import {
  IconSettings,
  IconTool,
  IconApps,
  IconPlus,
  IconRefresh,
  IconDelete,
  IconFile,
  IconCheckCircle
} from '@arco-design/web-vue/es/icon'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

const showAgentSidebar = ref(true)
const chatHistory = ref<QueryHistory[]>([])

// ===== 设置相关 =====
const settingsVisible = ref(false)
const activeTab = ref('status')
const userProfile = ref({
  name: '向云轩',
  avatar: ''
})

// ===== 智能体状态 =====
const agentStatus = ref({
  color: 'green',
  text: '运行中',
  currentModel: 'gpt-3.5-turbo',
  loadedSkills: 0,
  coreTools: 8
})

const agentInfo = ref({
  totalTools: 0,
  skillPaths: [],
  enabledSkills: 0,
  healthy: false
})

const modelConfig = ref({
  llmModel: 'gpt-3.5-turbo',
  temperature: 0.7,
  maxRetries: 3,
  timeout: 60
})

// ===== 技能管理 =====
const skillsTab = ref('external')
const skillsLoading = ref(false)
const externalSkills = ref<any[]>([])
const skillSearch = ref('')
const coreSkills = ref([
  { name: '意图分析', description: '分析用户查询的意图和需求' },
  { name: '元数据检索', description: '检索数据源的元数据信息' },
  { name: 'MQL生成', description: '将自然语言转换为MQL查询' },
  { name: 'MQL验证', description: '验证生成的MQL是否正确' },
  { name: 'MQL修正', description: '自动修正有误的MQL' },
  { name: 'SQL转换', description: '将MQL转换为可执行的SQL' },
  { name: '查询执行', description: '执行SQL查询并返回结果' },
  { name: '结果分析', description: '分析查询结果并提供洞察' }
])

// ===== 加载技能弹窗 =====
const loadSkillModalVisible = ref(false)
const loadSkillMethod = ref('directory')
const loadSkillForm = ref({
  directory: 'backend/app/agents/external_skills',
  skill_id: '',
  url: '',
  force_reload: false
})

// ===== 技能详情弹窗 =====
const skillDetailVisible = ref(false)
const currentSkill = ref<any>(null)

async function showSkillDetail(skill: any) {
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/info/${skill.skill_id}`)
    const data = await response.json()
    if (data.success) {
      currentSkill.value = data.skill_info
      skillDetailVisible.value = true
    } else {
      Message.error(`获取技能详情失败: ${data.message}`)
    }
  } catch (error: any) {
    Message.error(`获取技能详情失败: ${error.message}`)
  }
}

// ===== 计算属性 =====
const filteredExternalSkills = computed(() => {
  if (!skillSearch.value) {
    return externalSkills.value
  }
  const keyword = skillSearch.value.toLowerCase()
  return externalSkills.value.filter(
    (skill) =>
      skill.skill_id.toLowerCase().includes(keyword) ||
      (skill.name && skill.name.toLowerCase().includes(keyword)) ||
      (skill.description && skill.description.toLowerCase().includes(keyword))
  )
})

async function fetchHistory() {
  try {
    const res = await getQueryHistory({ page: 1, page_size: 10 })
    chatHistory.value = res.items
  } catch (error) {
    console.error('Failed to fetch history:', error)
  }
}

async function handleHistoryClick(id: string) {
  showAgentSidebar.value = true;  // 确保显示Agent侧边栏
  
  // 根据当前路由决定跳转到哪个页面
  const targetRoute = route.name === 'AgentQuery' ? 'AgentQuery' : 'Query'
  router.push({ name: targetRoute, query: { id } });
  
  // 延迟刷新历史记录列表，确保路由变化完成
  setTimeout(async () => {
    await fetchHistory();
  }, 100);
}

async function handleNewChat() {
  showAgentSidebar.value = true;  // 确保显示Agent侧边栏
  
  // 根据当前路由决定跳转到哪个页面
  const targetRoute = route.name === 'AgentQuery' ? 'AgentQuery' : 'Query'
  router.push({ name: targetRoute, query: { t: Date.now() } })
  
  // 延迟刷新历史记录列表，确保路由变化完成
  setTimeout(async () => {
    await fetchHistory();
  }, 100);
}

function toggleSidebarMode() {
  showAgentSidebar.value = !showAgentSidebar.value
}

// 当前选中的菜单项
const selectedKeys = computed(() => {
  return [route.name as string]
})

// 展开的子菜单 - 使用ref实现双向绑定
const openKeys = ref<string[]>([])

// 根据路由自动展开对应的父菜单
function updateOpenKeys() {
  const routeName = route.name as string
  // 定义菜单结构映射
  const menuMap: Record<string, string> = {
    'DataSources': 'Semantic',
    'Datasets': 'Semantic',
    'Metrics': 'Semantic',
    'Dimensions': 'Semantic',
    'Dictionaries': 'Semantic',
    'Lineage': 'Semantic',
    'ModelConfig': 'Settings',
    'QueryConfig': 'Settings',
    'AgentTest': 'Settings',
    'Workbook': 'Air',
    'Integration': 'Air',
    'Consolidation': 'Air',
    'AirAcceleration': 'Air',
    'Catalog': 'Can',
    'Application': 'Can',
    'CanAcceleration': 'Can',
    'CanSettings': 'Can',
    'OperatorLineage': 'Big'
  }
  
  const parentKey = menuMap[routeName]
  if (parentKey && !openKeys.value.includes(parentKey)) {
    openKeys.value = [...openKeys.value, parentKey]
  }
}

// 面包屑
const breadcrumbs = computed(() => {
  const items: { title: string; path?: string }[] = []
  route.matched.forEach(item => {
    if (item.meta?.title) {
      items.push({
        title: item.meta.title as string,
        path: item.path !== route.path ? item.path : undefined
      })
    }
  })
  return items
})

// 菜单点击处理
function handleMenuClick(key: string) {
  if (key === 'Query' || key === 'AgentQuery') {
    showAgentSidebar.value = true
  } else {
    // 如果切换到非Query页面，重置为显示普通导航菜单
    showAgentSidebar.value = false
  }
  router.push({ name: key })
}

// 跳转到模型配置页面
function goToModelConfig() {
  router.push({ name: 'ModelConfig' })
}

// ===== 设置相关 =====
function openSettings() {
  settingsVisible.value = true
  refreshSkillsList()
  loadAgentStatus()
  loadAgentInfo()
  checkAgentHealth()
}

function closeSettings() {
  settingsVisible.value = false
}

async function loadAgentStatus() {
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/stats`)
    const data = await response.json()
    if (data.success) {
      agentStatus.value.loadedSkills = data.data?.total || 0
      agentInfo.value.enabledSkills = data.data?.total || 0
    }
  } catch (error) {
    console.error('Failed to load agent status:', error)
  }
}

async function loadAgentInfo() {
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/agent/info`)
    const data = await response.json()
    if (data.success) {
      agentInfo.value = {
        totalTools: data.info?.total_tools || 0,
        skillPaths: data.info?.skill_paths || [],
        enabledSkills: data.info?.enabled_skills || 0,
        healthy: data.info?.healthy || false
      }
    }
  } catch (error) {
    console.error('Failed to load agent info:', error)
  }
}

async function checkAgentHealth() {
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/health`)
    const data = await response.json()
    if (data.success) {
      agentInfo.value.healthy = true
    } else {
      agentInfo.value.healthy = false
      console.warn('Agent health check failed:', data.message)
    }
  } catch (error) {
    agentInfo.value.healthy = false
    console.error('Agent health check error:', error)
  }
}

async function saveModelConfig() {
  try {
    // TODO: 调用API保存模型配置
    Message.success('配置已保存')
  } catch (error: any) {
    Message.error(`保存失败: ${error.message}`)
  }
}

// ===== 技能管理相关 =====
async function refreshSkillsList() {
  skillsLoading.value = true
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/list`)
    const data = await response.json()
    if (data.success && data.data) {
      externalSkills.value = data.data.map((skill: any) => ({
        ...skill,
        enabled: skill.enabled !== false
      }))
      agentStatus.value.loadedSkills = externalSkills.value.length
    }
  } catch (error: any) {
    Message.error(`加载技能列表失败: ${error.message}`)
  } finally {
    skillsLoading.value = false
  }
}

function openLoadSkillModal() {
  loadSkillModalVisible.value = true
}

function closeLoadSkillModal() {
  loadSkillModalVisible.value = false
  loadSkillForm.value = {
    directory: 'backend/app/agents/external_skills',
    skill_id: '',
    url: '',
    force_reload: false
  }
}

async function handleLoadSkill() {
  if (loadSkillMethod.value === 'directory' && !loadSkillForm.value.directory) {
    Message.warning('请输入目录路径')
    return
  }

  if (loadSkillMethod.value === 'url' && (!loadSkillForm.value.skill_id || !loadSkillForm.value.url)) {
    Message.warning('请填写技能ID和URL')
    return
  }

  skillsLoading.value = true
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    let url = ''
    let body: any = {}

    if (loadSkillMethod.value === 'directory') {
      url = `${API_BASE}/skills/load/directory`
      body = {
        directory: loadSkillForm.value.directory,
        force_reload: loadSkillForm.value.force_reload
      }
    } else {
      url = `${API_BASE}/skills/load/url`
      body = {
        skill_id: loadSkillForm.value.skill_id,
        url: loadSkillForm.value.url,
        force_reload: loadSkillForm.value.force_reload
      }
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    const data = await response.json()
    if (data.success) {
      Message.success('技能加载成功')
      closeLoadSkillModal()
      await refreshSkillsList()
    } else {
      Message.error(`加载失败: ${data.message || '未知错误'}`)
    }
  } catch (error: any) {
    Message.error(`加载失败: ${error.message}`)
  } finally {
    skillsLoading.value = false
  }
}

async function toggleSkill(skill: any) {
  skill.switching = true
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/agent/skills/toggle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        skill_name: skill.name || skill.skill_id,
        enabled: skill.enabled
      })
    })

    const data = await response.json()
    if (data.success) {
      Message.success(`${skill.name || skill.skill_id} 已${skill.enabled ? '启用' : '禁用'}`)
      await loadAgentStatus()
    } else {
      // 如果后端API调用失败，回滚状态
      skill.enabled = !skill.enabled
      Message.error(`操作失败: ${data.message || '未知错误'}`)
    }

    // 如果禁用，可以提示用户是否要卸载技能
    if (!skill.enabled) {
      Modal.confirm({
        title: '提示',
        content: '技能已禁用。是否要完全卸载该技能？',
        okText: '卸载',
        cancelText: '保留',
        onOk: async () => {
          await unloadSkill(skill.skill_id)
        }
      })
    }
  } catch (error: any) {
    // 发生错误时回滚状态
    skill.enabled = !skill.enabled
    Message.error(`操作失败: ${error.message}`)
  } finally {
    skill.switching = false
  }
}

async function unloadSkill(skillId: string) {
  try {
    const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
    const response = await fetch(`${API_BASE}/skills/unload/${skillId}`, {
      method: 'DELETE'
    })

    const data = await response.json()
    if (data.success) {
      Message.success('技能已卸载')
      await refreshSkillsList()
    } else {
      Message.error(`卸载失败: ${data.message || '未知错误'}`)
    }
  } catch (error: any) {
    Message.error(`卸载失败: ${error.message}`)
  }
}

async function unloadAllSkills() {
  if (externalSkills.value.length === 0) {
    Message.warning('没有可卸载的技能')
    return
  }

  Modal.confirm({
    title: '确认卸载',
    content: `确定要卸载所有 ${externalSkills.value.length} 个技能吗？`,
    okText: '确定',
    cancelText: '取消',
    onOk: async () => {
      try {
        const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8011/api/v1'}`
        const response = await fetch(`${API_BASE}/skills/unload/all`, {
          method: 'DELETE'
        })

        const data = await response.json()
        if (data.success) {
          Message.success(`已卸载 ${data.unloaded?.length || 0} 个技能`)
          await refreshSkillsList()
        } else {
          Message.error(`卸载失败: ${data.message || '未知错误'}`)
        }
      } catch (error: any) {
        Message.error(`批量卸载失败: ${error.message}`)
      }
    }
  })
}

function filterSkills() {
  // 搜索已在 computed 中处理
}

// 初始化时检查模型配置状态
onMounted(() => {
  settingsStore.checkModelConfigStatus()
  updateOpenKeys()
  fetchHistory()

  // 定期检查模型可用性（每5分钟）
  setInterval(async () => {
    if (settingsStore.isModelConfigured && settingsStore.defaultModelConfig) {
      await settingsStore.testDefaultModelAvailability()
    }
  }, 5 * 60 * 1000)
})

// 路由变化时更新展开的菜单
watch(() => route.name, () => {
  updateOpenKeys()
})

// 监听路由参数变化，当进入查询历史详情时刷新历史列表
watch(() => route.query, async (newQuery, oldQuery) => {
  // 如果是Query页面并且有id参数变化，则刷新历史记录
  if (route.name === 'Query' && newQuery.id && newQuery.id !== oldQuery.id) {
    await fetchHistory();
  }
}, { immediate: false });

// 监听路由路径变化，当进入Query页面时刷新历史记录
watch(() => route.path, async (newPath, oldPath) => {
  if (newPath.includes('/query') && !oldPath?.includes('/query')) {
    await fetchHistory();
  }
});
</script>

<style scoped>
.sidebar-header-actions {
  padding: 0 16px 8px;
}

.empty-history {
  padding: 8px 12px;
  color: var(--color-text-4);
  font-size: 12px;
  text-align: center;
}

.sidebar-sider {
  background: #f7f8fa !important;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: transparent;
  border-bottom: none;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}

.fold-icon {
  cursor: pointer;
  color: #4e5969;
}

.new-chat-wrapper {
  padding: 0 16px 16px;
}

.new-chat-btn {
  height: 36px;
  border-radius: 6px;
  font-weight: 600;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.history-group {
  margin-bottom: 24px;
}

.group-title {
  padding: 8px 12px;
  font-size: 12px;
  color: #86909c;
}

.history-item {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #4e5969;
  cursor: pointer;
  margin-bottom: 2px;
}

.history-item:hover {
  background: #e5e6eb;
}

.history-item.active {
  background: #e8f3ff;
  color: #165dff;
  font-weight: 600;
}

.user-info {
  margin-top: auto;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid #e5e6eb;
  color: #4e5969;
}

.user-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-btn {
  padding: 4px 8px;
  margin-left: auto;
}

.main-layout {
  height: 100vh;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 64px;
  background: var(--color-bg-1);
  border-bottom: 1px solid var(--color-border);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.layout-content {
  padding: 20px;
  background: var(--color-bg-2);
  overflow: auto;
}

/* 路由过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 侧边栏样式覆盖 */
:deep(.arco-layout-sider) {
  background: var(--color-bg-1);
  border-right: 1px solid var(--color-border);
}

:deep(.arco-menu) {
  height: calc(100vh - 64px);
  overflow: auto;
}

/* ===== 设置弹窗样式 ===== */
.settings-modal :deep(.arco-modal-body) {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.settings-content {
  display: flex;
  gap: 24px;
  min-height: 500px;
}

/* 左侧通用设置 */
.settings-left {
  width: 280px;
  padding: 24px;
  background: #f7f8fa;
  border-radius: 4px;
  flex-shrink: 0;
}

.user-profile {
  text-align: center;
}

.profile-name {
  margin: 16px 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
}

.profile-role {
  margin: 0;
  color: #86909c;
  font-size: 13px;
}

.profile-settings :deep(.arco-form-item-label-col) {
  padding-bottom: 4px;
}

/* 右侧标签页 */
.settings-right {
  flex: 1;
  min-width: 0;
}

.settings-right :deep(.arco-tabs-content) {
  padding-top: 16px;
}

/* 智能体状态 */
.status-panel h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #1d2129;
}

/* 技能管理 */
.skills-panel {
  height: 100%;
}

.skills-list {
  max-height: 400px;
  overflow-y: auto;
}

.skills-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e6eb;
}

.skills-count {
  color: #86909c;
  font-size: 13px;
}

.external-skills-section {
  min-height: 400px;
}

.empty-skills {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #c9cdd4;
}

/* 关于我们 */
.about-panel {
  padding: 16px;
}

.about-header {
  text-align: center;
  padding: 24px 0;
}

.about-header h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #1d2129;
}

.version {
  margin: 0;
  color: #86909c;
  font-size: 13px;
}

.about-content h4 {
  margin: 16px 0 8px 0;
  font-size: 14px;
  color: #1d2129;
}

.about-content p {
  margin: 8px 0;
  color: #4e5969;
  line-height: 1.6;
}

.about-content ul {
  margin: 8px 0;
  padding-left: 20px;
  color: #4e5969;
  line-height: 1.8;
}

.about-footer {
  text-align: center;
  margin-top: 24px;
  color: #86909c;
  font-size: 13px;
}
</style>
