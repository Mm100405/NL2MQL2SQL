import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏折叠状态
  const sidebarCollapsed = ref(false)
  
  // 当前主题
  const theme = ref<'light' | 'dark'>('light')
  
  // 全局加载状态
  const globalLoading = ref(false)

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // 设置主题
  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    document.body.setAttribute('arco-theme', newTheme)
  }

  // 设置全局加载
  function setGlobalLoading(loading: boolean) {
    globalLoading.value = loading
  }

  return {
    sidebarCollapsed,
    theme,
    globalLoading,
    toggleSidebar,
    setTheme,
    setGlobalLoading
  }
})
