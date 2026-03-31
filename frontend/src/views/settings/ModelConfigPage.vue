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
          <a-tag :color="getProviderColor(record.provider)">
            {{ getProviderLabel(record.provider) }}
          </a-tag>
        </template>
        <template #status="{ record }">
          <a-space>
            <a-badge :status="record.is_active ? 'success' : 'normal'" />
            <span>{{ record.is_active ? '已启用' : '未启用' }}</span>
            <a-tag v-if="record.is_default" color="arcoblue" size="small">默认</a-tag>
          </a-space>
        </template>
        <template #connectionStatus="{ record }">
          <a-space>
            <a-badge :status="record.connectionStatus?.connected ? 'success' : record.connectionStatus?.loading ? 'processing' : 'normal'" />
            <span v-if="record.connectionStatus?.loading">测试中...</span>
            <span v-else-if="record.connectionStatus?.connected">已连接</span>
            <span v-else>未连接</span>
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
      width="640px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-form-item field="name" label="配置名称">
          <a-input v-model="form.name" placeholder="如：生产环境 GPT-4o" />
        </a-form-item>

        <!-- 供应商选择 -->
        <a-form-item field="provider" label="模型供应商">
          <div v-if="providerGroups.length" class="provider-grid">
            <template v-for="group in providerGroups" :key="group.key">
              <!-- 非"其他"分组：正常展示 -->
              <template v-if="group.key !== 'other'">
                <div class="provider-group-title">{{ group.label }}</div>
                <div class="provider-chips">
                  <div
                    v-for="(cfg, key) in getProvidersByGroup(group.key)"
                    :key="key"
                    class="provider-chip"
                    :class="{ active: form.provider === key }"
                    :style="{ '--chip-color': isValidColor(cfg.color) ? cfg.color : '#6b7280' }"
                    @click="selectProvider(key)"
                  >
                    <span class="chip-dot" />
                    <span class="chip-label">{{ cfg.shortLabel }}</span>
                  </div>
                </div>
              </template>

              <!-- "其他"分组：标题行含搜索框，chips 限流 + 搜索结果 -->
              <template v-else>
                <div class="other-group-header">
                  <span class="provider-group-title">其他</span>
                  <div class="provider-search-box" :class="{ focused: searchFocused }">
                    <input
                      ref="searchInputRef"
                      v-model="providerSearch"
                      placeholder="搜索..."
                      class="search-input"
                      @focus="searchFocused = true"
                      @blur="handleSearchBlur"
                    />
                    <icon-close
                      v-if="providerSearch"
                      class="search-clear"
                      @mousedown.prevent="providerSearch = ''"
                    />
                  </div>
                </div>

                <!-- 搜索结果 -->
                <div v-if="providerSearch" class="provider-chips">
                  <div
                    v-for="(cfg, key) in searchProviders"
                    :key="key"
                    class="provider-chip"
                    :class="{ active: form.provider === key }"
                    :style="{ '--chip-color': cfg.color }"
                    @click="selectProvider(key)"
                  >
                    <span class="chip-dot" />
                    <span class="chip-label">{{ cfg.shortLabel }}</span>
                  </div>
                  <div v-if="Object.keys(searchProviders).length === 0" class="provider-empty">
                    未找到匹配的供应商
                  </div>
                </div>

                <!-- 默认 chips（前10 + 溢出） -->
                <div v-else class="provider-chips">
                  <template v-for="(cfg, key, idx) in otherVisibleProviders" :key="key">
                    <div
                      class="provider-chip"
                      :class="{ active: form.provider === key }"
                      :style="{ '--chip-color': isValidColor(cfg.color) ? cfg.color : '#6b7280' }"
                      @click="selectProvider(key)"
                    >
                      <span class="chip-dot" />
                      <span class="chip-label">{{ cfg.shortLabel }}</span>
                    </div>
                    <div
                      v-if="idx === 9 && otherOverflowCount > 0"
                      class="provider-chip overflow-chip"
                      :class="{ expanded: otherExpanded }"
                      @click="otherExpanded = !otherExpanded"
                    >
                      {{ otherExpanded ? '收起' : `+${otherOverflowCount}` }}
                    </div>
                  </template>
                </div>
              </template>
            </template>
          </div>
          <a-spin v-else style="width: 100%" />
        </a-form-item>

        <!-- 模型名称 -->
        <a-form-item field="model_name" label="模型名称">
          <div class="model-input-row">
            <a-select
              v-if="availableModels.length > 0"
              v-model="form.model_name"
              placeholder="请选择或输入模型名称"
              allow-create
              allow-clear
              :filter-option="true"
              class="model-select"
              :style="{ flex: 1 }"
            >
              <a-option v-for="m in availableModels" :key="m" :value="m">
                <span class="model-option-text">{{ m }}</span>
              </a-option>
            </a-select>
            <a-input v-else v-model="form.model_name" placeholder="请输入模型名称" class="model-select" :style="{ flex: 1 }" />
            <a-button
              type="outline"
              size="small"
              :loading="fetchingModels"
              :disabled="!canFetchModels"
              @click="handleFetchModels"
            >
              <template #icon><icon-sync /></template>
              获取最新
            </a-button>
          </div>
          <div v-if="modelsFromApi" class="models-hint">已从供应商 API 获取最新模型列表</div>
        </a-form-item>

        <!-- API Key -->
        <a-form-item v-if="currentProviderConfig?.needApiKey" field="api_key" label="API Key">
          <a-input-password v-model="form.api_key" placeholder="请输入 API Key" autocomplete="current-password" />
        </a-form-item>

        <!-- API 地址 -->
        <a-form-item v-if="currentProviderConfig?.showApiBase" field="api_base" label="API 地址">
          <a-input
            v-model="form.api_base"
            :placeholder="currentProviderConfig?.apiBase || '请输入 API 地址'"
          />
        </a-form-item>

        <a-form-item field="is_active" label="启用状态">
          <a-switch v-model="form.is_active" />
        </a-form-item>

        <a-collapse :default-active-key="[]">
          <a-collapse-item header="高级参数" key="advanced">
            <a-form-item label="Temperature">
              <a-slider v-model="form.config_params.temperature" :min="0" :max="2" :step="0.1" show-input />
            </a-form-item>
            <a-form-item label="Max Tokens">
              <a-input-number v-model="form.config_params.max_tokens" :min="100" :max="128000" :step="100" />
            </a-form-item>
          </a-collapse-item>
        </a-collapse>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import {
  getModelConfigs,
  createModelConfig,
  updateModelConfig,
  deleteModelConfig,
  testModelConnection,
  activateModelConfig,
  getLLMProviders,
  fetchLLMModels,
  type ModelConfig,
  type ProviderGroup,
  type ProviderConfig,
} from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
import { isValidColor } from '@/utils/sanitize'

const settingsStore = useSettingsStore()

// ─── 动态供应商数据 ──────────────────────────────────────────────────────

const providerGroups = ref<ProviderGroup[]>([])
const providers = ref<Record<string, ProviderConfig>>({})
const providerSearch = ref('')
const searchFocused = ref(false)
const searchInputRef = ref<HTMLInputElement>()
const otherExpanded = ref(false)

const OTHER_SHOW_LIMIT = 10

async function loadProviders() {
  try {
    const data = await getLLMProviders()
    providerGroups.value = data.groups
    providers.value = data.providers
  } catch {
    Message.error('加载供应商列表失败')
  }
}

function getProvidersByGroup(groupKey: string): Record<string, ProviderConfig> {
  const result: Record<string, ProviderConfig> = {}
  for (const [key, cfg] of Object.entries(providers.value)) {
    if (cfg.group === groupKey) result[key] = cfg
  }
  return result
}

// 搜索过滤：按 label / shortLabel 匹配
const searchProviders = computed(() => {
  const q = providerSearch.value.trim().toLowerCase()
  if (!q) return {}
  const result: Record<string, ProviderConfig> = {}
  for (const [key, cfg] of Object.entries(providers.value)) {
    if (
      cfg.label.toLowerCase().includes(q) ||
      cfg.shortLabel.toLowerCase().includes(q)
    ) {
      result[key] = cfg
    }
  }
  return result
})

// "其他"分组：前 N 个（或展开后全部）
const otherAllProviders = computed(() => getProvidersByGroup('other'))
const otherVisibleProviders = computed(() => {
  if (otherExpanded.value) return otherAllProviders.value
  const entries = Object.entries(otherAllProviders.value)
  if (entries.length <= OTHER_SHOW_LIMIT) return otherAllProviders.value
  return Object.fromEntries(entries.slice(0, OTHER_SHOW_LIMIT))
})
const otherOverflowCount = computed(() => {
  const total = Object.keys(otherAllProviders.value).length
  return Math.max(0, total - OTHER_SHOW_LIMIT)
})

function handleSearchBlur() {
  searchFocused.value = false
  // 延迟清空，避免点击搜索结果时 chips 消失
  setTimeout(() => {
    if (!searchFocused.value) providerSearch.value = ''
  }, 200)
}

// ─── 模型列表（动态） ────────────────────────────────────────────────────

const dynamicModels = ref<string[]>([])
const modelsFromApi = ref(false)
const fetchingModels = ref(false)

const availableModels = computed(() => {
  const popular = currentProviderConfig.value?.popularModels || []
  if (dynamicModels.value.length > 0) {
    // API 获取的模型在前，热门模型去重追加在后
    const apiSet = new Set(dynamicModels.value)
    const extra = popular.filter(m => !apiSet.has(m))
    return [...dynamicModels.value, ...extra]
  }
  return popular
})

const currentProviderConfig = computed(() => providers.value[form.provider])

const canFetchModels = computed(() => {
  const cfg = currentProviderConfig.value
  // 需要 api_base 或 provider 有默认 apiBase
  return cfg && (form.api_base || cfg.apiBase) && !form.provider?.startsWith('custom')
})

async function handleFetchModels() {
  const cfg = currentProviderConfig.value
  if (!cfg) return
  fetchingModels.value = true
  try {
    const result = await fetchLLMModels({
      provider: form.provider,
      api_key: form.api_key || undefined,
      api_base: form.api_base || undefined,
    })
    dynamicModels.value = result.models
    modelsFromApi.value = !result.fallback
    if (result.fallback) {
      Message.warning('无法连接供应商 API，已显示推荐模型')
    }
    // 自动选中第一个
    if (result.models.length > 0 && !result.models.includes(form.model_name)) {
      form.model_name = result.models[0]!
    }
  } catch {
    Message.error('获取模型列表失败')
  } finally {
    fetchingModels.value = false
  }
}

// ─── 组件状态 ────────────────────────────────────────────────────────────

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()

interface ExtendedModelConfig extends ModelConfig {
  connectionStatus?: {
    loading?: boolean
    connected?: boolean
    lastTested?: string
  }
}

const modelConfigs = ref<ExtendedModelConfig[]>([])

const form = reactive({
  name: '',
  provider: '',
  model_name: '',
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
  provider: [{ required: true, message: '请选择模型供应商' }],
  model_name: [{ required: true, message: '请输入模型名称' }]
}

const columns = [
  { title: '配置名称', dataIndex: 'name' },
  { title: '提供商', slotName: 'provider' },
  { title: '模型', dataIndex: 'model_name' },
  { title: '连接状态', slotName: 'connectionStatus', width: 120 },
  { title: '状态', slotName: 'status' },
  { title: '操作', slotName: 'actions', width: 280 }
]

// ─── 方法 ────────────────────────────────────────────────────────────────

function getProviderLabel(provider: string) {
  return providers.value[provider]?.label || provider
}

function getProviderColor(provider: string) {
  return providers.value[provider]?.color || 'gray'
}

function selectProvider(key: string) {
  form.provider = key
  const cfg = providers.value[key]
  dynamicModels.value = []
  modelsFromApi.value = false
  if (cfg && cfg.popularModels.length > 0) {
    form.model_name = cfg.popularModels[0]!
  } else {
    form.model_name = ''
  }
  form.api_base = cfg?.showApiBase ? cfg.apiBase || '' : ''
}

async function fetchConfigs() {
  loading.value = true
  try {
    const configs = await getModelConfigs()
    modelConfigs.value = configs.map(config => ({
      ...config,
      connectionStatus: { connected: false, loading: false }
    }))
    settingsStore.setModelConfigs(modelConfigs.value as ModelConfig[])
    setTimeout(() => { testDefaultConnection() }, 100)
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
  dynamicModels.value = []
  modelsFromApi.value = false
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
  const firstProvider = Object.keys(providers.value)[0] || ''
  const firstCfg = providers.value[firstProvider]
  Object.assign(form, {
    name: '',
    provider: firstProvider,
    model_name: firstCfg?.popularModels?.[0] || '',
    api_key: '',
    api_base: firstCfg?.showApiBase ? firstCfg?.apiBase || '' : '',
    is_active: true,
    config_params: { temperature: 0.7, max_tokens: 4096 }
  })
  dynamicModels.value = []
  modelsFromApi.value = false
  formRef.value?.resetFields()
}

async function testDefaultConnection() {
  const defaultConfig = modelConfigs.value.find(config => config.is_default)
  if (defaultConfig) {
    await testSingleConnection(defaultConfig)
  }
}

async function testSingleConnection(config: ExtendedModelConfig) {
  config.connectionStatus = { ...config.connectionStatus, loading: true, connected: false }
  try {
    const result = await testModelConnection(config.id)
    config.connectionStatus = { ...config.connectionStatus, loading: false, connected: result.success }
  } catch {
    config.connectionStatus = { ...config.connectionStatus, loading: false, connected: false }
  }
}

async function handleTest(record: ExtendedModelConfig) {
  record.connectionStatus = { ...record.connectionStatus, loading: true, connected: false }
  try {
    const result = await testModelConnection(record.id)
    record.connectionStatus = { ...record.connectionStatus, loading: false, connected: result.success }
    if (result.success) {
      Message.success('连接测试成功')
    } else {
      Message.error(`连接测试失败: ${result.message}`)
    }
  } catch {
    record.connectionStatus = { ...record.connectionStatus, loading: false, connected: false }
    Message.error('连接测试失败')
  }
}

async function handleSetDefault(record: ModelConfig) {
  try {
    await activateModelConfig(record.id)
    Message.success('设置成功')
    fetchConfigs()
  } catch {
    Message.error('设置失败')
  }
}

async function handleDelete(id: string) {
  try {
    await deleteModelConfig(id)
    Message.success('删除成功')
    fetchConfigs()
  } catch {
    Message.error('删除失败')
  }
}

onMounted(() => {
  loadProviders()
  fetchConfigs()
})
</script>

<style scoped>
.model-config-page {
  height: 100%;
}

/* ── 供应商选择网格 ── */
.provider-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.provider-group-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.provider-group-title:first-child {
  margin-top: 0;
}

/* "其他"分组：标题行 + 搜索框 */
.other-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.other-group-header .provider-group-title {
  flex-shrink: 0;
  margin-top: 0;
}

.provider-empty {
  padding: 12px 0;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-3);
}

/* 溢出提示 chip */
.overflow-chip {
  background: var(--color-fill-2);
  border-color: var(--color-border-2);
  color: var(--color-text-2);
  cursor: pointer;
}

.overflow-chip:hover {
  border-color: var(--color-text-3);
  background: var(--color-fill-3);
  transform: none;
}

.overflow-chip.expanded {
  background: var(--color-fill-3);
  border-color: var(--color-text-3);
}

/* 内联搜索框 */
.provider-search-box {
  position: relative;
  width: 120px;
  height: 24px;
  border-radius: 12px;
  border: 1px solid var(--color-border-2);
  background: var(--color-bg-2);
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.provider-search-box:hover {
  border-color: var(--color-border-3);
}

.provider-search-box.focused {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 0 0 2px rgba(var(--primary-6), 0.1);
}

.search-input {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  padding: 0 10px;
  font-size: 12px;
  color: var(--color-text-1);
}

.search-input::placeholder {
  color: var(--color-text-4);
}

.search-clear {
  position: absolute;
  right: 6px;
  font-size: 10px;
  color: var(--color-text-3);
  cursor: pointer;
}

.search-clear:hover {
  color: var(--color-text-1);
}

.provider-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 18px;
  border: 1.5px solid var(--color-border-2);
  background: var(--color-bg-2);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.provider-chip:hover {
  border-color: var(--chip-color);
  background: color-mix(in srgb, var(--chip-color) 6%, var(--color-bg-2));
  transform: translateY(-1px);
}

.provider-chip.active {
  border-color: var(--chip-color);
  background: color-mix(in srgb, var(--chip-color) 12%, var(--color-bg-2));
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--chip-color) 20%, transparent);
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--chip-color);
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.provider-chip.active .chip-dot {
  opacity: 1;
  box-shadow: 0 0 6px var(--chip-color);
}

.chip-label {
  font-size: 13px;
  color: var(--color-text-1);
  font-weight: 400;
  white-space: nowrap;
}

.provider-chip.active .chip-label {
  font-weight: 600;
  color: var(--chip-color);
}

/* ── 模型选择 ── */
.model-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.model-select :deep(.arco-select-view-single) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
}

.model-option-text {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
}

.models-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-3);
}
</style>
