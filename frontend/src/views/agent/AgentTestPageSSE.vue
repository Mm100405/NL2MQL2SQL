<!-- Agent测试页面 - SSE流式输出示例 -->
<template>
  <div class="agent-test-page">
    <a-card title="Agent测试页面 - SSE流式输出">
      <a-button type="primary" @click="executeQueryWithSSE" :loading="loading">
        执行查询（SSE）
      </a-button>

      <!-- 实时步骤展示 -->
      <div v-if="steps.length > 0" style="margin-top: 20px;">
        <a-timeline>
          <a-timeline-item
            v-for="(step, index) in steps"
            :key="index"
            :dot-color="getStepColor(step.status)"
          >
            <template #dot>
              <icon-loading v-if="step.status === 'processing'" />
              <icon-check-circle v-else-if="step.status === 'success'" />
              <icon-close-circle v-else />
            </template>
            <a-card size="small">
              <p><strong>{{ step.title }}</strong></p>
              <p v-if="step.content">{{ step.content }}</p>
              <p style="color: #86909c; font-size: 12px;">
                {{ step.timestamp }}
              </p>
            </a-card>
          </a-timeline-item>
        </a-timeline>
      </div>

      <!-- 最终结果 -->
      <a-card v-if="result" title="查询结果" style="margin-top: 20px;">
        <pre>{{ JSON.stringify(result, null, 2) }}</pre>
      </a-card>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconLoading,
  IconCheckCircle,
  IconCloseCircle
} from '@arco-design/web-vue/es/icon'

const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api/v1'}/agent`

const loading = ref(false)
const steps = ref<any[]>([])
const result = ref<any>(null)

function getStepColor(status: string) {
  const colors: Record<string, string> = {
    success: 'green',
    processing: 'blue',
    error: 'red',
    warning: 'orange'
  }
  return colors[status] || 'gray'
}

function executeQueryWithSSE() {
  const query = "查询最近7天的销售额"

  loading.value = true
  steps.value = []
  result.value = null

  // 构造URL参数
  const params = new URLSearchParams({
    natural_language: query,
    user_id: 'test_user'
  })

  // 创建SSE连接
  const eventSource = new EventSource(`${API_BASE}/query/stream?${params.toString()}`)

  // 监听步骤事件
  eventSource.addEventListener('step', (event: MessageEvent) => {
    const step = JSON.parse(event.data)
    console.log('[SSE Step]:', step)
    steps.value.push(step)
  })

  // 监听结果事件
  eventSource.addEventListener('result', (event: MessageEvent) => {
    const data = JSON.parse(event.data)
    console.log('[SSE Result]:', data)
    result.value = data
    Message.success('查询完成')
    loading.value = false

    // 关闭SSE连接
    eventSource.close()
  })

  // 监听错误事件
  eventSource.addEventListener('error', (event: MessageEvent) => {
    const error = JSON.parse(event.data)
    console.error('[SSE Error]:', error)
    Message.error(`查询失败: ${error.message}`)
    loading.value = false

    // 关闭SSE连接
    eventSource.close()
  })

  // 监听连接错误
  eventSource.onerror = (error) => {
    console.error('[SSE Connection Error]:', error)
    Message.error('连接失败')
    loading.value = false
    eventSource.close()
  }
}
</script>

<style scoped>
.agent-test-page {
  padding: 20px;
  background: #f7f8fa;
  min-height: 100vh;
}
</style>
