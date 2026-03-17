<template>
  <a-modal
    v-model:visible="visible"
    title="API 调试"
    width="1000px"
    @ok="handleClose"
    @cancel="handleClose"
    :footer="false"
  >
    <div class="api-debug-container">
      <!-- API 信息 -->
      <div class="api-info-section">
        <h3>API 端点</h3>
      <a-alert type="info" class="api-endpoint">
        <template #icon><icon-link /></template>
        <span class="endpoint-text">{{ apiDocs?.api?.endpoint || '未生成' }}</span>
        <a-space>
          <a-button type="text" size="mini" @click="handleRegenerate" :loading="regenerating">
            重新生成
          </a-button>
          <a-button type="text" size="mini" @click="copyEndpoint">
            <template #icon><icon-copy /></template>
          </a-button>
        </a-space>
      </a-alert>
      </div>

      <!-- 参数配置 -->
      <div class="params-section">
        <h3>请求参数</h3>
        <div v-if="apiDocs?.api?.parameterConfig && Object.keys(apiDocs?.api?.parameterConfig).length > 0" class="params-list">
          <div
            v-for="(config, fieldName) in apiDocs?.api?.parameterConfig"
            :key="fieldName"
            class="param-item"
          >
            <div class="param-label">
              <span class="param-name">{{ config.paramName || fieldName }}</span>
              <a-tag size="small" :color="getTypeColor(config.fieldType)">{{ config.fieldType || 'string' }}</a-tag>
            </div>
            <!-- 如果有字典值，使用选择框 -->
            <a-select
              v-if="config.dictValues && config.dictValues.length > 0"
              v-model="requestParams[config.paramName || fieldName]"
              :placeholder="`请选择${config.paramName || fieldName}`"
              allow-clear
              class="param-input"
            >
              <a-option
                v-for="item in config.dictValues"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label || item.value }}
              </a-option>
            </a-select>
            <!-- 否则使用输入框 -->
            <a-input
              v-else
              v-model="requestParams[config.paramName || fieldName]"
              :placeholder="`请输入${config.paramName || fieldName}`"
              allow-clear
              class="param-input"
            />
          </div>
        </div>
        <a-empty v-else description="无需参数" />
      </div>

      <!-- 请求示例 -->
      <div class="request-example-section">
        <h3>请求示例</h3>
        <a-card class="code-card">
          <div class="code-content">
            <pre><code>{{ getRequestBodyExample() }}</code></pre>
          </div>
        </a-card>
      </div>

      <!-- 调试按钮 -->
      <div class="debug-actions">
        <a-space>
          <a-button
            type="primary"
            :loading="loading"
            @click="handleDebug"
          >
            <template #icon><icon-play-arrow /></template>
            发送请求
          </a-button>
          <a-button @click="handleClear">清空</a-button>
        </a-space>
      </div>

      <!-- 响应结果 -->
      <div class="response-section">
        <h3>
          响应结果
          <span v-if="responseTime > 0" class="response-time">
            {{ responseTime }}ms
          </span>
        </h3>
        <div v-if="responseData" class="response-content">
          <a-card class="response-card">
            <template #extra>
              <a-space>
                <a-tag :color="responseSuccess ? 'green' : 'red'">
                  {{ responseSuccess ? '成功' : '失败' }}
                </a-tag>
                <a-button
                  type="text"
                  size="mini"
                  @click="copyResponse"
                >
                  <template #icon><icon-copy /></template>
                  复制
                </a-button>
              </a-space>
            </template>
            <div class="code-content">
              <pre><code>{{ formatResponse(responseData) }}</code></pre>
            </div>
          </a-card>
        </div>
        <a-empty v-else description="暂无响应数据" />
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconLink,
  IconCopy,
  IconPlayArrow
} from '@arco-design/web-vue/es/icon'
import {
  callCustomApi,
  getCustomApiDocs,
  regenerateDataFormatConfig
} from '@/api/data_format'

const props = defineProps<{
  visible: boolean
  configId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const loading = ref(false)
const regenerating = ref(false)
const apiDocs = ref<any>(null)
const requestParams = ref<Record<string, any>>({})
const responseData = ref<any>(null)
const responseSuccess = ref(true)
const responseTime = ref(0)

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// 加载API文档
async function loadApiDocs() {
  if (!props.configId) return

  try {
    const docs = await getCustomApiDocs(props.configId)
    apiDocs.value = docs

    // 初始化参数 - 从 api.parameterConfig（使用paramName字段作为key）
    if (docs?.api?.parameterConfig) {
      requestParams.value = {}
      Object.entries(docs.api.parameterConfig).forEach(([key, config]) => {
        const paramKey = config.paramName || key
        requestParams.value[paramKey] = ''
      })
    }
  } catch (error: any) {
    Message.error('加载API文档失败')
    console.error(error)
  }
}

// 获取请求体示例
function getRequestBodyExample() {
  const body: Record<string, any> = {}
  Object.keys(requestParams.value).forEach(key => {
    body[key] = requestParams.value[key] || '示例值'
  })
  return JSON.stringify(body, null, 2)
}

// 获取类型颜色
function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    string: 'blue',
    number: 'orange',
    boolean: 'green',
    date: 'purple'
  }
  return colors[type] || 'gray'
}

// 调试API
async function handleDebug() {
  if (!props.configId) {
    Message.warning('缺少配置ID')
    return
  }

  // 验证必填参数（现在所有从 parameterConfig 来的参数都是必填的）
  const paramNames = Object.keys(requestParams.value)
  const missingParams = paramNames.filter(key => !requestParams.value[key])

  if (missingParams.length > 0 && paramNames.length > 0) {
    Message.warning(`请填写参数: ${missingParams.join(', ')}`)
    return
  }

  loading.value = true
  responseData.value = null
  responseTime.value = 0

  const startTime = Date.now()

  try {
    const result = await callCustomApi(props.configId, requestParams.value)
    responseData.value = result
    responseSuccess.value = true
    responseTime.value = Date.now() - startTime
    Message.success(`请求成功 (${responseTime.value}ms)`)
  } catch (error: any) {
    responseTime.value = Date.now() - startTime
    responseData.value = error.response?.data || error.message || '请求失败'
    responseSuccess.value = false
    Message.error(`请求失败 (${responseTime.value}ms)`)
  } finally {
    loading.value = false
  }
}

// 清空参数
function handleClear() {
  Object.keys(requestParams.value).forEach(key => {
    requestParams.value[key] = ''
  })
  responseData.value = null
}

// 复制端点
function copyEndpoint() {
  const endpoint = apiDocs.value?.api?.endpoint
  if (endpoint) {
    navigator.clipboard.writeText(endpoint)
    Message.success('已复制到剪贴板')
  }
}

// 复制响应
function copyResponse() {
  if (responseData.value) {
    navigator.clipboard.writeText(formatResponse(responseData.value))
    Message.success('已复制到剪贴板')
  }
}

// 格式化响应
function formatResponse(data: any) {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

// 重新生成配置
async function handleRegenerate() {
  if (!props.configId) {
    Message.warning('缺少配置ID')
    return
  }

  regenerating.value = true

  try {
    const result = await regenerateDataFormatConfig(props.configId)

    if (result.success) {
      Message.success('重新生成成功')
      // 重新加载API文档
      await loadApiDocs()
      // 清空之前的调试结果
      responseData.value = null
      requestParams.value = {}
    } else {
      Message.error(`重新生成失败: ${result.error || result.validationError || '未知错误'}`)
      // 如果有验证错误，也重新加载API文档（因为可能已经部分更新）
      await loadApiDocs()
    }
  } catch (error: any) {
    console.error('重新生成失败:', error)
    Message.error(`重新生成失败: ${error.message || '网络错误'}`)
  } finally {
    regenerating.value = false
  }
}

function handleClose() {
  emit('update:visible', false)
}

// 监听 visible 变化，加载文档
watch(() => props.visible, (val) => {
  if (val) {
    loadApiDocs()
  }
})
</script>

<style scoped lang="scss">
.api-debug-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-height: 600px;
  overflow-y: auto;
}

h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}

.api-info-section {
  .api-endpoint {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;

    .endpoint-text {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 14px;
      word-break: break-all;
    }
  }
}

.params-section {
  .params-list {
    display: flex;
    flex-direction: column;
    gap: 16px;

    .param-item {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .param-label {
        display: flex;
        align-items: center;
        gap: 8px;

        .param-name {
          font-weight: 500;
          color: #1d2129;
        }
      }

      .param-input {
        margin-left: 0;
      }
    }
  }
}

.request-example-section,
.response-section {
  h3 {
    display: flex;
    align-items: center;
    gap: 8px;

    .response-time {
      font-size: 12px;
      color: #86909c;
      font-weight: 400;
    }
  }

  .code-card,
  .response-card {
    background: #f7f8fa;
    border: 1px solid #e5e6eb;

    .code-content {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      color: #1d2129;
      max-height: 300px;
      overflow: auto;

      pre {
        margin: 0;
        padding: 16px;
      }

      code {
        background: transparent;
      }
    }
  }
}

.debug-actions {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  border-top: 1px solid #e5e6eb;
  border-bottom: 1px solid #e5e6eb;
}
</style>
