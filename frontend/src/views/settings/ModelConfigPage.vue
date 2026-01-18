<template>
  <div class="model-config-page">
    <a-card title="模型配置">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><icon-plus /></template>
          新增配置
        </a-button>
      </template>

      <a-table :columns="columns" :data="modelConfigs" :loading="loading">
        <template #provider="{ record }">
          <a-tag>{{ getProviderLabel(record.provider) }}</a-tag>
        </template>
        <template #status="{ record }">
          <a-space>
            <a-badge :status="record.is_active ? 'success' : 'default'" />
            <span>{{ record.is_active ? '已启用' : '未启用' }}</span>
            <a-tag v-if="record.is_default" color="arcoblue" size="small">默认</a-tag>
          </a-space>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="handleTest(record)">
              测试连接
            </a-button>
            <a-button
              v-if="!record.is_default"
              type="text"
              size="small"
              @click="handleSetDefault(record)"
            >
              设为默认
            </a-button>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
            </a-button>
            <a-popconfirm content="确定删除此配置？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
                <template #icon><icon-delete /></template>
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑模型配置' : '新增模型配置'"
      :ok-loading="submitting"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-form-item field="name" label="配置名称">
          <a-input v-model="form.name" placeholder="请输入配置名称" />
        </a-form-item>
        <a-form-item field="provider" label="模型提供商">
          <a-select v-model="form.provider" placeholder="请选择模型提供商">
            <a-option value="openai">OpenAI</a-option>
            <a-option value="ollama">Ollama (本地)</a-option>
            <a-option value="azure">Azure OpenAI</a-option>
            <a-option value="custom">自定义API</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="model_name" label="模型名称">
          <a-select v-if="form.provider === 'openai'" v-model="form.model_name" placeholder="请选择模型">
            <a-option value="gpt-4">GPT-4</a-option>
            <a-option value="gpt-4-turbo">GPT-4 Turbo</a-option>
            <a-option value="gpt-3.5-turbo">GPT-3.5 Turbo</a-option>
          </a-select>
          <a-input v-else v-model="form.model_name" placeholder="请输入模型名称，如 llama3" />
        </a-form-item>
        <a-form-item v-if="form.provider !== 'ollama'" field="api_key" label="API Key">
          <a-input-password v-model="form.api_key" placeholder="请输入API Key" />
        </a-form-item>
        <a-form-item field="api_base" label="API地址">
          <a-input
            v-model="form.api_base"
            :placeholder="getApiBasePlaceholder()"
          />
        </a-form-item>
        <a-form-item field="is_active" label="启用状态">
          <a-switch v-model="form.is_active" />
        </a-form-item>
        
        <a-collapse :default-active-key="[]">
          <a-collapse-item header="高级参数" key="advanced">
            <a-form-item label="Temperature">
              <a-slider
                v-model="form.config_params.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                show-input
              />
            </a-form-item>
            <a-form-item label="Max Tokens">
              <a-input-number
                v-model="form.config_params.max_tokens"
                :min="100"
                :max="128000"
                :step="100"
              />
            </a-form-item>
          </a-collapse-item>
        </a-collapse>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import {
  getModelConfigs,
  createModelConfig,
  updateModelConfig,
  deleteModelConfig,
  testModelConnection,
  activateModelConfig,
  type ModelConfig
} from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const modelConfigs = ref<ModelConfig[]>([])

const form = reactive({
  name: '',
  provider: 'openai' as string,
  model_name: 'gpt-3.5-turbo',
  api_key: '',
  api_base: '',
  is_active: true,
  config_params: {
    temperature: 0.7,
    max_tokens: 4096
  }
})

const rules = {
  name: [{ required: true, message: '请输入配置名称' }],
  provider: [{ required: true, message: '请选择模型提供商' }],
  model_name: [{ required: true, message: '请输入模型名称' }]
}

const columns = [
  { title: '配置名称', dataIndex: 'name' },
  { title: '提供商', slotName: 'provider' },
  { title: '模型', dataIndex: 'model_name' },
  { title: '状态', slotName: 'status' },
  { title: '操作', slotName: 'actions', width: 280 }
]

function getProviderLabel(provider: string) {
  const labels: Record<string, string> = {
    openai: 'OpenAI',
    ollama: 'Ollama',
    azure: 'Azure OpenAI',
    custom: '自定义'
  }
  return labels[provider] || provider
}

function getApiBasePlaceholder() {
  const placeholders: Record<string, string> = {
    openai: '默认: https://api.openai.com/v1',
    ollama: '默认: http://localhost:11434',
    azure: 'https://{resource}.openai.azure.com',
    custom: '请输入API地址'
  }
  return placeholders[form.provider] || ''
}

async function fetchConfigs() {
  loading.value = true
  try {
    modelConfigs.value = await getModelConfigs()
    settingsStore.setModelConfigs(modelConfigs.value)
  } catch (error) {
    console.error('Failed to fetch configs:', error)
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  isEdit.value = false
  resetForm()
  modalVisible.value = true
}

function handleEdit(record: ModelConfig) {
  isEdit.value = true
  editingId.value = record.id
  Object.assign(form, {
    name: record.name,
    provider: record.provider,
    model_name: record.model_name,
    api_key: '',
    api_base: record.api_base || '',
    is_active: record.is_active,
    config_params: record.config_params || { temperature: 0.7, max_tokens: 4096 }
  })
  modalVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (valid) return

  submitting.value = true
  try {
    const data = { ...form }
    if (!data.api_key) delete (data as any).api_key
    
    if (isEdit.value) {
      await updateModelConfig(editingId.value, data)
      Message.success('更新成功')
    } else {
      await createModelConfig(data)
      Message.success('创建成功')
    }
    modalVisible.value = false
    fetchConfigs()
  } catch (error) {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  modalVisible.value = false
  resetForm()
}

function resetForm() {
  Object.assign(form, {
    name: '',
    provider: 'openai',
    model_name: 'gpt-3.5-turbo',
    api_key: '',
    api_base: '',
    is_active: true,
    config_params: { temperature: 0.7, max_tokens: 4096 }
  })
  formRef.value?.resetFields()
}

async function handleTest(record: ModelConfig) {
  try {
    const result = await testModelConnection(record.id)
    if (result.success) {
      Message.success('连接测试成功')
    } else {
      Message.error(`连接测试失败: ${result.message}`)
    }
  } catch (error) {
    Message.error('连接测试失败')
  }
}

async function handleSetDefault(record: ModelConfig) {
  try {
    await activateModelConfig(record.id)
    Message.success('设置成功')
    fetchConfigs()
  } catch (error) {
    Message.error('设置失败')
  }
}

async function handleDelete(id: string) {
  try {
    await deleteModelConfig(id)
    Message.success('删除成功')
    fetchConfigs()
  } catch (error) {
    Message.error('删除失败')
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped>
.model-config-page {
  height: 100%;
}
</style>
