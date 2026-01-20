import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getModelConfigStatus, testModelConnection, type ModelConfig } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  // 模型配置状态
  const isModelConfigured = ref(false)
  const isModelAvailable = ref(false) // 新增：模型是否可用
  const modelConfigs = ref<ModelConfig[]>([])
  const defaultModelConfig = ref<ModelConfig | null>(null)
  const loading = ref(false)

  // 计算属性
  const hasActiveModel = computed(() => {
    return modelConfigs.value.some(config => config.is_active)
  })

  // 检查模型配置状态
  async function checkModelConfigStatus() {
    try {
      loading.value = true
      const status = await getModelConfigStatus()
      isModelConfigured.value = status.is_configured
      if (status.default_model) {
        defaultModelConfig.value = status.default_model
        // 测试默认模型是否可用
        await testDefaultModelAvailability()
      } else {
        isModelAvailable.value = false
      }
    } catch (error) {
      console.error('Failed to check model config status:', error)
      isModelConfigured.value = false
      isModelAvailable.value = false
    } finally {
      loading.value = false
    }
  }

  // 测试默认模型是否可用
  async function testDefaultModelAvailability() {
    if (!defaultModelConfig.value) {
      isModelAvailable.value = false
      return
    }

    try {
      const result = await testModelConnection(defaultModelConfig.value.id)
      isModelAvailable.value = result.success
    } catch (error) {
      console.error('Failed to test model availability:', error)
      isModelAvailable.value = false
    }
  }

  // 更新模型配置状态
  function setModelConfigured(configured: boolean) {
    isModelConfigured.value = configured
  }

  // 设置模型配置列表
  function setModelConfigs(configs: ModelConfig[]) {
    modelConfigs.value = configs
    const defaultConfig = configs.find(c => c.is_default && c.is_active)
    if (defaultConfig) {
      defaultModelConfig.value = defaultConfig
      isModelConfigured.value = true
    }
  }

  return {
    isModelConfigured,
    isModelAvailable,  // 新增
    modelConfigs,
    defaultModelConfig,
    loading,
    hasActiveModel,
    checkModelConfigStatus,
    testDefaultModelAvailability,  // 新增
    setModelConfigured,
    setModelConfigs
  }
})
