<template>
  <div class="reserved-page">
    <a-result status="info" title="功能开发中" subtitle="此功能正在规划开发中，敬请期待">
      <template #icon>
        <icon-tool :size="64" />
      </template>
      <template #extra>
        <a-button type="primary" @click="goBack">返回首页</a-button>
      </template>
    </a-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goBack() {
  router.push('/')
}
</script>

<style scoped>
.reserved-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
