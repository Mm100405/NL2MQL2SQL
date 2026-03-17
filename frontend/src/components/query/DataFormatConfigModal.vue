<template>
  <a-modal
    v-model:visible="visible"
    title="配置输出格式"
    @ok="handleSave"
    @cancel="handleClose"
    width="700px"
  >
    <div class="config-form">
      <!-- 目标格式示例 -->
      <div class="form-section">
        <div class="section-header">
          <span class="section-title">目标格式示例</span>
          <span class="section-hint">输入期望返回的JSON数据结构</span>
        </div>
        <div class="json-editor-wrapper" :class="{ 'has-error': formatError, 'is-valid': isFormatValid }">
          <a-textarea
            v-model="targetFormat"
            placeholder="请输入期望的JSON返回格式示例..."
            :style="{ fontFamily: 'monospace' }"
            allow-clear
            @input="handleInputChange"
          />
          <div class="json-validation-icon" v-if="targetFormat.trim()">
            <a-icon v-if="isFormatValid" type="check-circle" class="success-icon" />
            <a-icon v-else type="close-circle" class="error-icon" />
          </div>
        </div>
        <div class="format-hint" v-if="formatError">
          <a-icon type="exclamation-circle" />
          {{ formatError }}
        </div>
        <div class="button-row">
          <a-button type="outline" size="small" @click="fillExample">
            <template #icon><a-icon type="copy" /></template>
            填入完整示例
          </a-button>
          <a-button type="outline" size="small" @click="handleValidateClick">
            <template #icon><a-icon type="check-circle" /></template>
            JSON校验
          </a-button>
        </div>
      </div>

      <!-- API所需参数 -->
      <div class="form-section">
        <div class="section-header">
          <span class="section-title">API所需参数</span>
          <span class="section-hint">输入参数名称后点击添加，多个参数将从视图的可过滤字段中自动筛选</span>
        </div>
        <div class="param-input-row">
          <a-input
            v-model="currentParam"
            placeholder="输入参数名称，如：问题大类"
            @press-enter="addParam"
          />
          <a-button type="primary" @click="addParam">
            <template #icon><a-icon type="plus" /></template>
            添加
          </a-button>
        </div>
        <div class="param-tags" v-if="apiParameters.length > 0">
          <div class="param-tag-item" v-for="(param, index) in apiParameters" :key="index">
            <a-tag color="blue" closable @close="removeParam(index)">
              {{ param }}
            </a-tag>
          </div>
        </div>
        <div class="param-empty" v-else>
          <a-icon type="info-circle" />
          暂无参数，请在上方输入参数名称后点击添加
        </div>
      </div>
    </div>

    <template #footer>
      <a-space>
        <a-button @click="handleClose">取消</a-button>
        <a-button type="primary" @click="handleSave">
          保存
        </a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

const props = defineProps<{
  visible: boolean
  initialConfig?: {
    targetFormat: any
    apiParameters: string[]
  }
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'save', config: { targetFormat: any, apiParameters: string[] }): void
}>()

// 可见性双向绑定
const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// 表单数据
const targetFormat = ref('')
const apiParameters = ref<string[]>([])
const currentParam = ref('')

// 格式校验
const formatError = ref<string | null>(null)
const isFormatValid = ref(false)

// 纯JSON示例（不含注释）
const jsonExample = computed(() => {
  return [
    '[',
    '  {',
    '    "id": "1",',
    '    "街道名称": "XX街道",',
    '    "问题大类": "安全隐患",',
    '    "问题小类": "消防通道占用",',
    '    "问题数量": 15',
    '  },',
    '  {',
    '    "id": "2",',
    '    "街道名称": "YY街道",',
    '    "问题大类": "环境脏乱",',
    '    "问题小类": "垃圾堆放",',
    '    "问题数量": 8',
    '  }',
    ']'
  ].join('\n')
})

// 监听弹窗显示，加载已有配置
watch(() => props.visible, (val) => {
  if (val) {
    // 打开时加载已有配置
    if (props.initialConfig) {
      // targetFormat 可能是对象，需要转为JSON字符串
      const format = props.initialConfig.targetFormat
      if (format && typeof format === 'object') {
        targetFormat.value = JSON.stringify(format, null, 2)
      } else {
        targetFormat.value = format || ''
      }
      apiParameters.value = [...(props.initialConfig.apiParameters || [])]
    }
    formatError.value = null
    isFormatValid.value = false
    currentParam.value = ''
    // 如果已有内容，立即进行验证
    if (targetFormat.value.trim()) {
      validateFormat()
    }
  }
})

// 添加参数
function addParam() {
  const param = currentParam.value.trim()
  if (!param) {
    Message.warning('请输入参数名称')
    return
  }
  if (apiParameters.value.includes(param)) {
    Message.warning('该参数已存在')
    return
  }
  apiParameters.value.push(param)
  currentParam.value = ''
}

// 删除参数
function removeParam(index: number) {
  apiParameters.value.splice(index, 1)
}

// 验证JSON格式
function validateFormat(): boolean {
  const content = targetFormat.value.trim()
  
  if (!content) {
    formatError.value = null
    isFormatValid.value = false
    return true // 允许为空
  }

  try {
    const parsed = JSON.parse(content)
    if (!Array.isArray(parsed)) {
      formatError.value = '目标格式必须是数组，请确保最外层为方括号 []'
      isFormatValid.value = false
      return false
    }
    formatError.value = null
    isFormatValid.value = true
    return true
  } catch (e: any) {
    const errorMsg = e.message || 'JSON格式错误'
    if (errorMsg.includes('Unexpected token')) {
      formatError.value = 'JSON语法错误：使用了非法字符或符号'
    } else if (errorMsg.includes('Expected')) {
      formatError.value = 'JSON语法错误：缺少必要的符号（如逗号、引号、大括号等）'
    } else if (errorMsg.includes('Unterminated')) {
      formatError.value = 'JSON语法错误：字符串或括号未闭合'
    } else {
      formatError.value = 'JSON格式错误，请检查语法'
    }
    isFormatValid.value = false
    return false
  }
}

// 处理输入变化
function handleInputChange() {
  validateFormat()
}

// 填入示例
function fillExample() {
  targetFormat.value = jsonExample.value
  validateFormat()
  Message.success('已填入示例')
}

// 手动触发校验
function handleValidateClick() {
  const content = targetFormat.value.trim()
  if (!content) {
    Message.warning('请先输入JSON内容')
    return
  }
  const isValid = validateFormat()
  if (isValid) {
    Message.success('JSON格式校验通过')
  } else {
    Message.error('JSON格式校验失败')
  }
}

// 保存配置
function handleSave() {
  // 验证JSON格式
  if (targetFormat.value.trim() && !validateFormat()) {
    Message.warning('请修正JSON格式错误')
    return
  }

  // 解析目标格式
  let parsedFormat = null
  if (targetFormat.value.trim()) {
    try {
      parsedFormat = JSON.parse(targetFormat.value)
    } catch (e) {
      Message.warning('JSON格式错误')
      return
    }
  }

  // emit配置数据
  emit('save', {
    targetFormat: parsedFormat,
    apiParameters: [...apiParameters.value]
  })

  Message.success('配置已保存')
  emit('update:visible', false)
}

// 关闭弹窗
function handleClose() {
  emit('update:visible', false)
}
</script>

<style scoped>
.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-weight: 500;
  color: var(--color-text-1);
}

.section-hint {
  font-size: 12px;
  color: var(--color-text-3);
}

.json-editor-wrapper {
  height: 200px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  position: relative;
  transition: border-color 0.2s;
}

.json-editor-wrapper.has-error {
  border-color: var(--color-danger);
}

.json-editor-wrapper.is-valid {
  border-color: var(--color-success);
}

.json-editor-wrapper :deep(.arco-textarea) {
  height: 200px;
  min-height: 100%;
  max-height: 100%;
  border: none;
  border-radius: 0;
  resize: none;
  padding: 8px;
}

.json-editor-wrapper :deep(.arco-textarea:focus) {
  box-shadow: none;
}

.json-validation-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

.json-validation-icon .success-icon {
  color: var(--color-success);
  font-size: 20px;
}

.json-validation-icon .error-icon {
  color: var(--color-danger);
  font-size: 20px;
}

.button-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.button-row :deep(.arco-btn) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
}

.param-input-row {
  display: flex;
  gap: 8px;
}

.param-input-row .arco-input {
  flex: 1;
}

.param-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.param-tag-item {
  display: flex;
  align-items: center;
}

.param-empty {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-3);
  padding: 8px 0;
}

.format-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-danger);
  background: var(--color-danger-light-1);
  padding: 6px 8px;
  border-radius: 4px;
  border-left: 3px solid var(--color-danger);
  margin-top: 4px;
}
</style>
