<template>
  <div class="drill-down">
    <a-space direction="vertical" fill>
      <a-alert type="info">
        选择一个维度进行下钻分析，查看更细粒度的数据
      </a-alert>
      <div class="dimension-list">
        <a-tag
          v-for="dim in dimensions"
          :key="dim"
          checkable
          :checked="selectedDimension === dim"
          @check="handleSelect(dim)"
        >
          {{ dim }}
        </a-tag>
      </div>
      <a-button
        type="primary"
        :disabled="!selectedDimension"
        @click="handleDrill"
      >
        <template #icon><icon-arrow-down /></template>
        下钻分析
      </a-button>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  queryId: string
  dimensions: string[]
}>()

const emit = defineEmits<{
  (e: 'drill', dimension: string): void
}>()

const selectedDimension = ref('')

function handleSelect(dim: string) {
  selectedDimension.value = selectedDimension.value === dim ? '' : dim
}

function handleDrill() {
  if (selectedDimension.value) {
    emit('drill', selectedDimension.value)
  }
}
</script>

<style scoped>
.drill-down {
  padding: 16px 0;
}

.dimension-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
