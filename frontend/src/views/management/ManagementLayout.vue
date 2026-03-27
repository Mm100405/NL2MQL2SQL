<template>
  <a-layout class="management-layout">
    <!-- 左侧导航 -->
    <a-layout-sider
      :collapsed="sidebarCollapsed"
      :width="240"
      :collapsed-width="64"
      collapsible
      breakpoint="lg"
      @collapse="sidebarCollapsed = !sidebarCollapsed"
      class="management-sider"
    >
      <!-- Logo -->
      <div class="management-logo">
        <icon-settings class="logo-icon" />
        <span v-if="!sidebarCollapsed" class="logo-text">管理中心</span>
      </div>

      <!-- 导航菜单 -->
      <a-menu
        :selected-keys="selectedKeys"
        :open-keys="openKeys"
        :auto-open-selected="true"
        @menu-item-click="handleMenuClick"
        @sub-menu-click="handleSubMenuClick"
      >
        <!-- 数据管理 -->
        <a-sub-menu key="data">
          <template #icon><icon-storage /></template>
          <template #title>数据管理</template>
          <a-menu-item key="DataSources">数据源管理</a-menu-item>
          <a-menu-item key="Datasets">物理表管理</a-menu-item>
          <a-menu-item key="Metrics">指标管理</a-menu-item>
          <a-menu-item key="Dimensions">维度管理</a-menu-item>
          <a-menu-item key="Views">视图管理</a-menu-item>
          <a-menu-item key="Dictionaries">字典管理</a-menu-item>
        </a-sub-menu>

        <!-- 系统配置 -->
        <a-sub-menu key="system">
          <template #icon><icon-settings /></template>
          <template #title>系统配置</template>
          <a-menu-item key="ModelConfig">模型配置</a-menu-item>
          <a-menu-item key="QueryConfig">问数配置</a-menu-item>
          <a-menu-item key="Lineage">血缘管理</a-menu-item>
        </a-sub-menu>

        <!-- 高级模块 -->
        <a-sub-menu key="advanced">
          <template #icon><icon-bulb /></template>
          <template #title>高级模块</template>
          <a-menu-item key="Workbook">AIR - 工作簿</a-menu-item>
          <a-menu-item key="Catalog">CAN - 指标目录</a-menu-item>
          <a-menu-item key="OperatorLineage">BIG - 算子血缘</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <!-- 右侧内容 -->
    <a-layout>
      <!-- 顶部工具栏 -->
      <div class="management-header">
        <div class="header-left">
          <a-breadcrumb>
            <a-breadcrumb-item>
              <router-link to="/" class="breadcrumb-link">
                <icon-home />
                主页
              </router-link>
            </a-breadcrumb-item>
            <a-breadcrumb-item>{{ currentPageTitle }}</a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="header-right">
          <a-button type="text" @click="goHome">
            <template #icon><icon-export /></template>
            返回主页
          </a-button>
        </div>
      </div>

      <!-- 内容区域 -->
      <a-layout-content class="management-content">
        <router-view v-slot="{ Component, route }">
          <transition name="slide-fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const sidebarCollapsed = ref(false)
const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>(['data', 'system', 'advanced'])

// 路由映射
const routeMap: Record<string, { path: string; group: string }> = {
  DataSources: { path: '/management/data/datasources', group: 'data' },
  Datasets: { path: '/management/data/datasets', group: 'data' },
  Metrics: { path: '/management/data/metrics', group: 'data' },
  Dimensions: { path: '/management/data/dimensions', group: 'data' },
  Views: { path: '/management/data/views', group: 'data' },
  Dictionaries: { path: '/management/data/dictionaries', group: 'data' },
  ModelConfig: { path: '/management/system/model', group: 'system' },
  QueryConfig: { path: '/management/system/query', group: 'system' },
  Lineage: { path: '/management/system/lineage', group: 'system' },
  Workbook: { path: '/management/advanced/air/workbook', group: 'advanced' },
  Catalog: { path: '/management/advanced/can/catalog', group: 'advanced' },
  OperatorLineage: { path: '/management/advanced/big/lineage', group: 'advanced' }
}

// 标题映射
const titleMap: Record<string, string> = {
  DataSources: '数据源管理',
  Datasets: '物理表管理',
  Metrics: '指标管理',
  Dimensions: '维度管理',
  Views: '视图管理',
  Dictionaries: '字典管理',
  ModelConfig: '模型配置',
  QueryConfig: '问数配置',
  Lineage: '血缘管理',
  Workbook: 'AIR - 工作簿',
  Catalog: 'CAN - 指标目录',
  OperatorLineage: 'BIG - 算子血缘'
}

const currentPageTitle = computed(() => {
  const key = selectedKeys.value[0]
  return titleMap[key] || '管理中心'
})

// 监听路由变化
watch(
  () => route.name,
  (name) => {
    if (name) {
      selectedKeys.value = [name as string]
      const routeInfo = routeMap[name as string]
      if (routeInfo && !openKeys.value.includes(routeInfo.group)) {
        openKeys.value = [...openKeys.value, routeInfo.group]
      }
    }
  },
  { immediate: true }
)

const handleMenuClick = (key: string) => {
  const routeInfo = routeMap[key]
  if (routeInfo) {
    router.push(routeInfo.path)
  }
}

const handleSubMenuClick = (key: string, openKeysArr: string[]) => {
  openKeys.value = openKeysArr
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
/* ========================================
   管理中心 - 极简柔和设计
   ======================================== */

.management-layout {
  height: 100vh;
  background: var(--bg-base);
}

/* ===== 左侧导航 ===== */
.management-sider {
  background: var(--bg-elevated) !important;
  border-right: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  transition: width var(--duration-base) var(--ease-smooth);
}

.management-logo {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  border-bottom: 1px solid var(--border-light);
  position: relative;
}

.management-logo::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--space-md);
  right: var(--space-md);
  height: 1px;
  background: var(--border-light);
}

.logo-icon {
  font-size: 24px;
  color: var(--soft-primary);
  transition: transform var(--duration-base) var(--ease-smooth);
}

.management-sider:hover .logo-icon {
  transform: scale(1.05);
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

/* 菜单样式 */
::deep(.arco-menu) {
  height: calc(100vh - 72px);
  background: transparent;
  border: none;
}

::deep(.arco-menu-item),
::deep(.arco-menu-inline-header) {
  border-radius: var(--radius-md);
  margin: 2px var(--space-sm);
  transition: all var(--duration-base) var(--ease-smooth);
  position: relative;
  overflow: hidden;
}

::deep(.arco-menu-item::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: var(--soft-primary);
  border-radius: var(--radius-full);
  transition: height var(--duration-base) var(--ease-smooth);
}

::deep(.arco-menu-item:hover) {
  background: var(--bg-hover);
  padding-left: calc(var(--space-lg) + 8px);
}

::deep(.arco-menu-item:hover::before) {
  height: 60%;
}

::deep(.arco-menu-item.arco-menu-selected) {
  background: var(--soft-primary-lighter) !important;
  color: var(--soft-primary) !important;
  font-weight: 600;
  padding-left: calc(var(--space-lg) + 8px);
}

::deep(.arco-menu-item.arco-menu-selected::before) {
  height: 60%;
}

::deep(.arco-menu-inline-header:hover) {
  background: var(--bg-hover);
}

/* ===== 顶部工具栏 ===== */
.management-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-xl);
  height: 64px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-light);
  box-shadow: var(--shadow-xs);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.breadcrumb-link {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--duration-base) var(--ease-smooth);
}

.breadcrumb-link:hover {
  color: var(--soft-primary);
}

/* ===== 内容区域 ===== */
.management-content {
  padding: var(--space-xl);
  background: var(--bg-base);
  overflow: auto;
  min-height: calc(100vh - 64px);
}

/* ===== 页面切换动画 ===== */
.slide-fade-enter-active {
  transition: all var(--duration-slow) var(--ease-smooth);
}

.slide-fade-leave-active {
  transition: all var(--duration-base) var(--ease-smooth);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .management-content {
    padding: var(--space-md);
  }
}
</style>
