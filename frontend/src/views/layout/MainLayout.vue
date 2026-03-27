<template>
  <a-layout class="main-layout">
    <!-- 极简侧边栏 -->
    <a-layout-sider
      v-model:collapsed="sidebarCollapsed"
      :width="240"
      :collapsed-width="56"
      collapsible
      hide-trigger
      breakpoint="lg"
      class="sidebar-sider"
    >
      <!-- Logo -->
      <div class="logo">
        <icon-thunderbolt class="logo-icon" />
        <span v-if="!sidebarCollapsed" class="logo-text">Agent</span>
      </div>

      <!-- 收起/展开按钮 -->
      <div class="toggle-wrapper">
        <a-button
          type="text"
          size="mini"
          class="toggle-btn"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <template #icon>
            <icon-menu-fold v-if="!sidebarCollapsed" />
            <icon-menu-unfold v-else />
          </template>
        </a-button>
      </div>

      <!-- 新建对话按钮 -->
      <div class="new-chat-wrapper">
        <a-button
          v-if="!sidebarCollapsed"
          type="primary"
          long
          class="new-chat-btn"
          @click="handleNewChat"
        >
          <template #icon><icon-plus /></template>
          新建对话
        </a-button>
        <a-tooltip v-else content="新建对话" position="right">
          <a-button
            type="primary"
            shape="circle"
            size="small"
            class="new-chat-btn-collapsed"
            @click="handleNewChat"
          >
            <template #icon><icon-plus /></template>
          </a-button>
        </a-tooltip>
      </div>

      <!-- 历史对话列表 (展开时显示) -->
      <div v-if="!sidebarCollapsed" class="chat-history">
        <div class="history-group">
          <div class="group-title">历史对话</div>
          <div class="history-list">
            <div
              v-for="item in chatHistory"
              :key="item.conversation_id || item.id"
              class="history-item"
              :class="{ active: route.query.id === item.conversation_id || route.query.id === item.id }"
              @click="handleHistoryClick(item.conversation_id || item.id)"
            >
              <icon-message class="history-icon" />
              <span class="history-text">
                {{ item.natural_language.slice(0, 18) }}{{ item.natural_language.length > 18 ? '...' : '' }}
              </span>
              <icon-delete
                class="delete-icon"
                @click.stop="handleDeleteHistory(item.conversation_id || item.id)"
              />
            </div>
            <div v-if="chatHistory.length === 0" class="empty-history">
              <icon-chat class="empty-icon" />
              <span>暂无历史对话</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 用户信息 -->
      <div class="user-info">
        <a-dropdown trigger="click" position="top" @select="handleUserMenuSelect">
          <div class="user-avatar-wrapper">
            <a-avatar :size="sidebarCollapsed ? 32 : 36" class="user-avatar">云轩</a-avatar>
            <icon-down v-if="!sidebarCollapsed" class="dropdown-icon" />
          </div>
          <template #content>
            <a-doption value="profile">
              <template #icon><icon-user /></template>
              个人设置
            </a-doption>
            <a-doption value="model-status">
              <template #icon>
                <icon-check-circle v-if="settingsStore.isModelAvailable" />
                <icon-exclamation-circle v-else />
              </template>
              模型状态
              <a-tag v-if="settingsStore.isModelAvailable" color="green" size="small">正常</a-tag>
              <a-tag v-else color="red" size="small">异常</a-tag>
            </a-doption>
            <a-divider style="margin: 4px 0" />
            <a-doption value="management">
              <template #icon><icon-settings /></template>
              管理中心
            </a-doption>
            <a-doption value="logout">
              <template #icon><icon-export /></template>
              退出登录
            </a-doption>
          </template>
        </a-dropdown>
        <div v-if="!sidebarCollapsed" class="user-details">
          <div class="user-name">向云轩</div>
          <div class="user-role">数据分析师</div>
        </div>
      </div>
    </a-layout-sider>

    <!-- 主内容区 -->
    <a-layout class="content-layout">
      <a-layout-content class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </a-layout-content>
    </a-layout>

    <!-- 个人设置弹窗 -->
    <a-modal
      v-model:visible="profileVisible"
      title="个人设置"
      :width="500"
      :footer="false"
      @cancel="profileVisible = false"
      class="profile-modal"
    >
      <a-form :model="profileForm" layout="vertical">
        <a-form-item label="用户名">
          <a-input v-model="profileForm.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model="profileForm.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="角色">
          <a-input v-model="profileForm.role" disabled />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 模型状态弹窗 -->
    <a-modal
      v-model:visible="modelStatusVisible"
      title="模型状态"
      :width="600"
      :footer="false"
      @cancel="modelStatusVisible = false"
      class="model-status-modal"
    >
      <div class="status-content">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="模型状态">
            <a-tag v-if="settingsStore.isModelAvailable" color="green">
              <template #icon><icon-check-circle /></template>
              正常运行
            </a-tag>
            <a-tag v-else color="red">
              <template #icon><icon-close-circle /></template>
              不可用
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="模型提供商">
            {{ modelConfig.provider || '未配置' }}
          </a-descriptions-item>
          <a-descriptions-item label="模型名称">
            {{ modelConfig.model_name || '未配置' }}
          </a-descriptions-item>
          <a-descriptions-item label="接口地址">
            {{ modelConfig.base_url || '默认' }}
          </a-descriptions-item>
        </a-descriptions>
        <div class="status-actions">
          <a-button type="primary" @click="goToModelConfig">
            <template #icon><icon-settings /></template>
            配置模型
          </a-button>
          <a-button @click="testModelConnection">
            <template #icon><icon-refresh /></template>
            测试连接
          </a-button>
        </div>
      </div>
    </a-modal>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useAppStore } from '@/stores/app'
import { useSettingsStore } from '@/stores/settings'
import { startConversation, getQueryHistory, deleteQueryHistory } from '@/api/query'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

const chatHistory = ref<any[]>([])
const sidebarCollapsed = ref(false)
const profileVisible = ref(false)
const modelStatusVisible = ref(false)

const profileForm = reactive({
  username: '向云轩',
  email: 'yunxuan@example.com',
  role: '数据分析师'
})

const modelConfig = reactive({
  provider: '',
  model_name: '',
  base_url: ''
})

// 加载历史对话
const loadChatHistory = async () => {
  try {
    const response = await getQueryHistory({ page: 1, page_size: 50 })
    chatHistory.value = response.items || []
  } catch (error) {
    console.error('加载历史对话失败:', error)
    Message.error('加载历史对话失败')
  }
}

// 加载模型配置
const loadModelConfig = async () => {
  try {
    await settingsStore.checkModelConfigStatus()
    if (settingsStore.defaultModelConfig) {
      modelConfig.provider = settingsStore.defaultModelConfig.provider || ''
      modelConfig.model_name = settingsStore.defaultModelConfig.model_name || ''
      modelConfig.base_url = settingsStore.defaultModelConfig.base_url || ''
    }
  } catch (error) {
    console.error('加载模型配置失败:', error)
  }
}

// 新建对话
const handleNewChat = async () => {
  try {
    // 不需要调用 API，直接跳转到新对话页面
    // 使用 timestamp 参数标识这是一个新对话
    router.push({
      path: '/agent-query',
      query: { t: Date.now().toString() }
    })
    Message.success('已创建新对话')
  } catch (error) {
    console.error('创建对话失败:', error)
    Message.error('创建对话失败')
    // 即使失败也跳转到新页面
    router.push('/agent-query')
  }
}

// 点击历史对话
const handleHistoryClick = (id: string) => {
  router.push({
    path: '/agent-query',
    query: { id }
  })
}

// 删除历史对话
const handleDeleteHistory = async (id: string) => {
  try {
    await deleteQueryHistory(id)
    chatHistory.value = chatHistory.value.filter(
      item => (item.conversation_id || item.id) !== id
    )
    Message.success('已删除历史对话')
  } catch (error) {
    console.error('删除失败:', error)
    Message.error('删除失败')
  }
}

// 用户菜单选择
const handleUserMenuSelect = (value: string | number | Record<string, any> | undefined) => {
  switch (value) {
    case 'profile':
      profileVisible.value = true
      break
    case 'model-status':
      modelStatusVisible.value = true
      break
    case 'management':
      router.push('/management')
      break
    case 'logout':
      Message.info('退出登录功能开发中...')
      break
  }
}

// 跳转到模型配置
const goToModelConfig = () => {
  modelStatusVisible.value = false
  router.push('/management/system/model')
}

// 测试模型连接
const testModelConnection = async () => {
  try {
    Message.info('正在测试模型连接...')
    await settingsStore.testDefaultModelAvailability()
    if (settingsStore.isModelAvailable) {
      Message.success('模型连接正常')
    } else {
      Message.error('模型连接失败')
    }
  } catch (error) {
    console.error('模型连接测试失败:', error)
    Message.error('模型连接测试失败')
  }
}

onMounted(() => {
  loadChatHistory()
  loadModelConfig()
})
</script>

<style scoped>
/* ========================================
   极简柔和设计 - Main Layout (纯对话模式)
   ======================================== */

.main-layout {
  height: 100vh;
  background: var(--bg-base);
  overflow: hidden;
}

/* ===== 侧边栏 ===== */
.sidebar-sider {
  background: var(--bg-elevated) !important;
  border-right: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-base) var(--ease-smooth);
}

/* 穿透 Arco LayoutSider 内部容器，使其成为 flex 纵向布局 */
.sidebar-sider :deep(.arco-layout-sider-children) {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* ===== Logo ===== */
.logo {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  border-bottom: 1px solid var(--border-light);
  position: relative;
  flex-shrink: 0;
}

.logo::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--space-lg);
  right: var(--space-lg);
  height: 1px;
  background: var(--border-light);
}

.logo-icon {
  font-size: 24px;
  color: var(--soft-primary);
  transition: transform var(--duration-base) var(--ease-smooth);
}

.sidebar-sider:hover .logo-icon {
  transform: scale(1.05);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

/* ===== 收起/展开按钮 ===== */
.toggle-wrapper {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  flex-shrink: 0;
}

.toggle-btn {
  color: var(--text-tertiary);
  font-size: 14px;
}

.toggle-btn:hover {
  color: var(--soft-primary);
  background: var(--soft-primary-lighter);
}

/* ===== 新建对话按钮 ===== */
.new-chat-wrapper {
  padding: var(--space-sm) var(--space-md);
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.new-chat-btn {
  height: 30px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.01em;
  box-shadow: var(--shadow-xs);
  transition: all var(--duration-base) var(--ease-smooth);
}

.new-chat-btn:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.new-chat-btn:active {
  transform: translateY(0);
}

/* ===== 历史对话列表 ===== */
.chat-history {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: var(--space-sm);
  min-height: 0; /* 重要：允许 flex 子项收缩 */
}

.history-group {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 var(--space-md);
  min-height: 0; /* 重要：允许 flex 子项收缩 */
}

.history-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0; /* 重要：允许滚动 */
}

.group-title {
  padding: var(--space-sm) var(--space-md);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 自定义滚动条 */
.history-list::-webkit-scrollbar {
  width: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: var(--radius-full);
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: var(--soft-primary-light);
}

.history-item {
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  margin-bottom: var(--space-xs);
  transition: all var(--duration-base) var(--ease-smooth);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.history-item::before {
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

.history-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  padding-left: calc(var(--space-md) + 8px);
}

.history-item:hover .delete-icon {
  opacity: 1;
}

.history-item:hover::before {
  height: 60%;
}

.history-item.active {
  background: var(--soft-primary-lighter);
  color: var(--soft-primary);
  font-weight: 600;
  padding-left: calc(var(--space-md) + 8px);
}

.history-item.active::before {
  height: 60%;
}

.history-icon {
  font-size: 11px;
  opacity: 0.6;
  flex-shrink: 0;
}

.history-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-icon {
  font-size: 14px;
  opacity: 0;
  color: var(--text-tertiary);
  transition: all var(--duration-base) var(--ease-smooth);
  flex-shrink: 0;
}

.delete-icon:hover {
  color: var(--color-danger);
  transform: scale(1.2);
}

/* 空状态 */
.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-xxl);
  color: var(--text-disabled);
  gap: var(--space-sm);
}

.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}

/* ===== 用户信息 ===== */
.user-info {
  padding: var(--space-sm) var(--space-md);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.user-avatar-wrapper {
  cursor: pointer;
  position: relative;
  transition: transform var(--duration-base) var(--ease-smooth);
}

.user-avatar-wrapper:hover {
  transform: scale(1.05);
}

.user-avatar {
  background: var(--soft-primary);
  color: #fff;
  transition: all var(--duration-base) var(--ease-smooth);
}

.dropdown-icon {
  position: absolute;
  bottom: -4px;
  right: -4px;
  font-size: 10px;
  background: var(--bg-elevated);
  border-radius: 50%;
  padding: 2px;
  opacity: 0;
  transition: opacity var(--duration-base) var(--ease-smooth);
}

.user-avatar-wrapper:hover .dropdown-icon {
  opacity: 1;
}

.user-details {
  flex: 1;
  overflow: hidden;
}

.user-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 11px;
  margin-bottom: 2px;
}

.user-role {
  color: var(--text-tertiary);
  font-size: 10px;
}

/* ===== 下拉菜单样式 ===== */
::deep(.arco-dropdown-option) {
  padding: var(--space-sm) var(--space-md);
  transition: all var(--duration-base) var(--ease-smooth);
}

::deep(.arco-dropdown-option:hover) {
  background: var(--soft-primary-lighter);
}

/* ===== 主内容区 ===== */
.content-layout {
  flex: 1;
  background: var(--bg-base);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.layout-content {
  flex: 1;
  overflow: hidden;
  background: var(--bg-base);
  display: flex;
  flex-direction: column;
}

/* ===== 页面切换动画 ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-smooth);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== 弹窗样式 ===== */
.profile-modal :deep(.arco-modal-body),
.model-status-modal :deep(.arco-modal-body) {
  padding: var(--space-lg);
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.status-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: flex-end;
}

/* ===== 折叠态新建对话按钮 ===== */
.new-chat-btn-collapsed {
  width: 36px !important;
  height: 36px !important;
  min-width: 36px !important;
  max-width: 36px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-xs);
  transition: all var(--duration-base) var(--ease-smooth);
}

.new-chat-btn-collapsed:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

/* ===== 折叠态侧边栏调整 ===== */
.sidebar-sider :deep(.arco-layout-sider-collapsed) {
  /* Arco 折叠态内部样式 */
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .sidebar-sider {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
    transform: translateX(-100%);
  }

  .sidebar-sider.mobile-open {
    transform: translateX(0);
  }
}
</style>
