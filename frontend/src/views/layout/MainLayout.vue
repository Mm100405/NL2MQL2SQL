<template>
  <a-layout class="main-layout">
    <!-- 侧边栏 -->
    <a-layout-sider
      :collapsed="appStore.sidebarCollapsed"
      :width="220"
      :collapsed-width="48"
      collapsible
      breakpoint="lg"
      @collapse="appStore.toggleSidebar"
    >
      <!-- Logo -->
      <div class="logo">
        <icon-robot :size="28" />
        <span v-if="!appStore.sidebarCollapsed" class="logo-text">NL2MQL2SQL</span>
      </div>

      <!-- 导航菜单 -->
      <a-menu
        :selected-keys="selectedKeys"
        v-model:open-keys="openKeys"
        :auto-open-selected="true"
        :accordion="false"
        @menu-item-click="handleMenuClick"
      >
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
          <a-tooltip v-else content="AI模型已配置">
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

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

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
})

// 路由变化时更新展开的菜单
watch(() => route.name, () => {
  updateOpenKeys()
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border);
}

.logo-text {
  margin-left: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
  white-space: nowrap;
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
