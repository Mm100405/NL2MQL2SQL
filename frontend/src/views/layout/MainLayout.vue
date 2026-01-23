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
      <template v-if="route.name === 'Query' && !appStore.sidebarCollapsed && showAgentSidebar">
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
              :key="item.id" 
              class="history-item"
              :class="{ active: route.query.id === item.id }"
              @click="handleHistoryClick(item.id)"
            >
              {{ item.natural_language.slice(0, 20) }}{{ item.natural_language.length > 20 ? '...' : '' }}
            </div>
            <div v-if="chatHistory.length === 0" class="empty-history">暂无历史</div>
          </div>
        </div>

        <div class="user-info">
          <a-avatar :size="24">demo</a-avatar>
          <span>demo</span>
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
          <a-menu-item key="Datasets">数据集管理</a-menu-item>
          <a-menu-item key="Metrics">指标管理</a-menu-item>
          <a-menu-item key="Dimensions">维度管理</a-menu-item>
          <a-menu-item key="Lineage">血缘管理</a-menu-item>
        </a-sub-menu>

        <!-- 系统设置 -->
        <a-sub-menu key="Settings">
          <template #icon><icon-settings /></template>
          <template #title>系统设置</template>
          <a-menu-item key="ModelConfig">模型配置</a-menu-item>
          <a-menu-item key="QueryConfig">问数配置</a-menu-item>
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
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useSettingsStore } from '@/stores/settings'
import { getQueryHistory } from '@/api/query'
import type { QueryHistory } from '@/api/types'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

const showAgentSidebar = ref(true)
const chatHistory = ref<QueryHistory[]>([])

async function fetchHistory() {
  try {
    const res = await getQueryHistory({ page: 1, page_size: 20 })
    chatHistory.value = res.items
  } catch (error) {
    console.error('Failed to fetch history:', error)
  }
}

function handleHistoryClick(id: string) {
  router.push({ name: 'Query', query: { id } })
}

function handleNewChat() {
  router.push({ name: 'Query', query: { t: Date.now() } })
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
    'Lineage': 'Semantic',
    'ModelConfig': 'Settings',
    'QueryConfig': 'Settings',
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
  if (key === 'Query') {
    showAgentSidebar.value = true
  }
  router.push({ name: key })
}

// 跳转到模型配置页面
function goToModelConfig() {
  router.push({ name: 'ModelConfig' })
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
</style>
