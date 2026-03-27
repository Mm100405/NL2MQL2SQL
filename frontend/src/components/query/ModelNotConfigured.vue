<template>
  <div class="model-not-configured">
    <a-empty>
      <template #image>
        <icon-robot :size="80" style="color: var(--color-text-3)" />
      </template>
      <template #description>
        <div class="description">
          <h3>{{ settingsStore.isModelConfigured ? 'AI模型不可用' : '暂未配置AI模型' }}</h3>
          <p>{{ settingsStore.isModelConfigured ? '当前配置的AI模型无法连接，请检查配置' : '智能问数功能需要配置AI模型才能使用' }}</p>
          <p class="hint">支持 OpenAI、Ollama、Azure OpenAI 等多种模型</p>
        </div>
      </template>
      <a-button type="primary" size="large" @click="goToConfig">
        <template #icon><icon-settings /></template>
        前往配置
      </a-button>
    </a-empty>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'

const router = useRouter()
const settingsStore = useSettingsStore()

function goToConfig() {
  router.push('/management/system/model')
}
</script>

<style scoped>
.model-not-configured {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--color-bg-1);
  border-radius: 8px;
}

.description {
  text-align: center;
}

.description h3 {
  margin: 16px 0 8px;
  font-size: 18px;
  color: var(--color-text-1);
}

.description p {
  margin: 4px 0;
  color: var(--color-text-2);
}

.description .hint {
  font-size: 12px;
  color: var(--color-text-3);
}
</style>
