<template>
  <div class="attribution">
    <a-space direction="vertical" fill>
      <a-alert type="info">
        选择指标和维度进行归因分析，了解各因素对结果的贡献度
      </a-alert>
      <a-form :model="form" layout="vertical">
        <a-form-item label="分析指标">
          <a-select v-model="form.metric" placeholder="选择要分析的指标">
            <a-option v-for="m in metrics" :key="m" :value="m">{{ m }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分析维度">
          <a-select v-model="form.dimensions" placeholder="选择分析维度" multiple :max-tag-count="3">
            <a-option v-for="d in dimensions" :key="d" :value="d">{{ d }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="时间范围">
          <a-range-picker v-model="form.dateRange" style="width: 100%" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :disabled="!canAnalyze" @click="handleAnalyze">
            <template #icon><icon-bulb /></template>
            开始归因分析
          </a-button>
        </a-form-item>
      </a-form>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

defineProps<{
  queryId: string
  metrics: string[]
  dimensions: string[]
}>()

const emit = defineEmits<{
  (e: 'analyze', params: any): void
}>()

const form = ref({
  metric: '',
  dimensions: [] as string[],
  dateRange: []
})

const canAnalyze = computed(() => {
  return form.value.metric && form.value.dimensions.length > 0
})

function handleAnalyze() {
  emit('analyze', {
    metric: form.value.metric,
    dimensions: form.value.dimensions,
    date_range: form.value.dateRange
  })
}
</script>

<style scoped>
.attribution {
  padding: 16px 0;
}
</style>
