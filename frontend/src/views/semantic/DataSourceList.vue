<template>
  <div class="datasource-list">
    <a-card title="数据源管理">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><IconPlus /></template>
          新增数据源
        </a-button>
      </template>

      <a-table
        :columns="columns"
        :data="dataSources"
        :loading="loading"
        :scroll="{ x: 1200 }"
        :bordered="false"
        :stripe="true"
      >
        <template #type="{ record }">
          <a-tag>{{ record.type.toUpperCase() }}</a-tag>
        </template>
        <template #status="{ record }">
          <a-badge :status="getStatusBadge(record.status)" :text="getStatusText(record.status)" />
        </template>
        <template #actions="{ record }">
          <a-space :size="4">
            <a-button type="text" size="small" @click="handleTest(record)">
              测试连接
            </a-button>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><IconEdit /></template>
              编辑
            </a-button>
            <a-popconfirm content="确定删除此数据源？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
                <template #icon><IconDelete /></template>
                删除
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑数据源' : '新增数据源'"
      :ok-loading="submitting"
      @ok="handleSubmit"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-form-item field="name" label="数据源名称">
          <a-input v-model="form.name" placeholder="请输入数据源名称" />
        </a-form-item>
        <a-form-item field="type" label="数据库类型">
          <a-select v-model="form.type" placeholder="请选择数据库类型">
            <a-option value="postgresql">PostgreSQL</a-option>
            <a-option value="mysql">MySQL</a-option>
            <a-option value="clickhouse">ClickHouse</a-option>
          </a-select>
        </a-form-item>
        <template v-if="true">
          <a-form-item field="connection_config.host" label="主机地址">
            <a-input v-model="form.connection_config.host" placeholder="localhost" />
          </a-form-item>
          <a-form-item field="connection_config.port" label="端口">
            <a-input-number v-model="form.connection_config.port" :placeholder="getDefaultPort()" />
          </a-form-item>
          <a-form-item field="connection_config.username" label="用户名">
            <a-input v-model="form.connection_config.username" placeholder="请输入用户名" autocomplete="username" />
          </a-form-item>
          <a-form-item field="connection_config.password" label="密码">
            <a-space direction="vertical" :style="{ width: '100%' }">
              <a-input-password
                v-model="form.connection_config.password"
                placeholder="请输入密码"
                autocomplete="current-password"
                @input="handlePasswordInput"
              />
              <a-button type="outline" size="small" :loading="testing" @click="handleTestConnection">
                <template #icon><IconThunderbolt /></template>
                测试连接
              </a-button>
            </a-space>
          </a-form-item>
        </template>
        <a-form-item field="connection_config.database" label="数据库名">
          <a-input
            v-model="form.connection_config.database"
            placeholder="数据库名称"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import { IconThunderbolt, IconPlus, IconEdit, IconDelete } from '@arco-design/web-vue/es/icon'
import {
  getDataSources,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  testDataSourceConnection,
  testConnectionConfig
} from '@/api/semantic'
import type { DataSource } from '@/api/types'

const loading = ref(false)
const submitting = ref(false)
const testing = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const dataSources = ref<DataSource[]>([])
const passwordChanged = ref(false) // 标记密码是否被修改

const form = reactive({
  name: '',
  type: 'postgresql' as string,
  connection_config: {
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: ''
  }
})

const rules = {
  name: [{ required: true, message: '请输入数据源名称' }],
  type: [{ required: true, message: '请选择数据库类型' }],
  'connection_config.database': [{ required: true, message: '请输入数据库名' }]
}

const columns = [
  { title: '名称', dataIndex: 'name', width: 200, ellipsis: true },
  { title: '类型', slotName: 'type', width: 120, align: 'center' },
  { title: '数据库', dataIndex: 'connection_config.database', width: 160, ellipsis: true },
  { title: '状态', slotName: 'status', width: 160, align: 'center' },
  { title: '主机地址', dataIndex: 'connection_config.host', width: 120, ellipsis: true },
  { title: '操作', slotName: 'actions', width: 200, fixed: 'right', align: 'center' }
]

function getDefaultPort() {
  const ports: Record<string, string> = {
    postgresql: '5432',
    mysql: '3306',
    clickhouse: '8123'
  }
  return ports[form.type] || ''
}

function getStatusBadge(status: string) {
  const badges: Record<string, any> = {
    active: 'success',
    inactive: 'normal',
    error: 'danger'
  }
  return badges[status] || 'normal'
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    active: '正常',
    inactive: '未连接',
    error: '错误'
  }
  return texts[status] || status
}

async function fetchDataSources() {
  loading.value = true
  try {
    dataSources.value = await getDataSources()
  } catch (error) {
    console.error('Failed to fetch data sources:', error)
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  isEdit.value = false
  resetForm()
  modalVisible.value = true
}

function handleEdit(record: DataSource) {
  isEdit.value = true
  editingId.value = record.id
  passwordChanged.value = false // 重置密码修改标记
  Object.assign(form, {
    name: record.name,
    type: record.type,
    connection_config: { ...record.connection_config, password: '******' }
  })
  modalVisible.value = true
}

function handlePasswordInput(value: string) {
  // 标记密码已被修改（只要用户输入过内容，就算修改）
  if (value !== '******') {
    passwordChanged.value = true
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      // 编辑模式：如果密码未修改（仍然是 "******"），保持为 "******"
      // 后端会识别 "******" 并保留原密码
      await updateDataSource(editingId.value, form)
      Message.success('更新成功')
    } else {
      await createDataSource(form)
      Message.success('创建成功')
    }
    modalVisible.value = false
    fetchDataSources()
  } catch (error) {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  passwordChanged.value = false // 重置密码修改标记
  Object.assign(form, {
    name: '',
    type: 'postgresql',
    connection_config: {
      host: 'localhost',
      port: 5432,
      database: '',
      username: '',
      password: ''
    }
  })
}

async function handleTest(record: DataSource) {
  try {
    const result = await testDataSourceConnection(record.id)
    if (result.success) {
      Message.success('连接测试成功')
    } else {
      Message.error(`连接测试失败: ${result.message}`)
    }
  } catch (error) {
    Message.error('连接测试失败')
  }
}

async function handleTestConnection() {
  // 编辑模式下，如果密码未修改，使用数据库中的原密码进行测试
  if (isEdit.value && !passwordChanged.value) {
    // 使用现有的数据源ID测试连接（后端会使用数据库中的密码）
    testing.value = true
    try {
      const result = await testDataSourceConnection(editingId.value)
      if (result.success) {
        Message.success('连接测试成功')
      } else {
        Message.error(`连接测试失败: ${result.message}`)
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || '连接测试失败'
      Message.error(errorMsg)
    } finally {
      testing.value = false
    }
    return
  }

  // 新建模式或密码已修改的情况：使用表单中的配置测试
  const testConfig = { ...form.connection_config }

  // 验证必填字段
  if (!testConfig.host || !testConfig.port || !testConfig.username || !testConfig.database) {
    Message.warning('请先填写完整的连接信息')
    return
  }

  if (!testConfig.password) {
    Message.warning('请输入密码')
    return
  }

  testing.value = true
  try {
    const testData = {
      type: form.type,
      connection_config: testConfig
    }
    const result = await testConnectionConfig(testData)
    if (result.success) {
      Message.success('连接测试成功')
    } else {
      Message.error(`连接测试失败: ${result.message}`)
    }
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '连接测试失败'
    Message.error(errorMsg)
  } finally {
    testing.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteDataSource(id)
    Message.success('删除成功')
    fetchDataSources()
  } catch (error) {
    Message.error('删除失败')
  }
}

onMounted(() => {
  fetchDataSources()
})
</script>

<style scoped>
.datasource-list {
  height: 100%;
}

.datasource-list :deep(.arco-table) {
  overflow: visible;
  table-layout: fixed;
}

.datasource-list :deep(.arco-table-container) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* 固定操作列样式 - 兼容多种 Arco Design 版本 */
.datasource-list :deep(.arco-table-th-fixed-right),
.datasource-list :deep(.arco-table-td-fixed-right),
.datasource-list :deep(.arco-table-th-fixed-last),
.datasource-list :deep(.arco-table-td-fixed-last) {
  position: sticky !important;
  right: 0 !important;
  background: #fff !important;
  z-index: 10 !important;
  box-shadow: -6px 0 12px -4px rgba(0, 0, 0, 0.08) !important;
}

.datasource-list :deep(.arco-table-tr:hover .arco-table-td-fixed-right),
.datasource-list :deep(.arco-table-tr:hover .arco-table-td-fixed-last) {
  background: #f2f3f5 !important;
}

/* 添加分隔线 */
.datasource-list :deep(.arco-table-th-fixed-right)::before,
.datasource-list :deep(.arco-table-td-fixed-right)::before,
.datasource-list :deep(.arco-table-th-fixed-last)::before,
.datasource-list :deep(.arco-table-td-fixed-last)::before {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 1px !important;
  background: #e5e6eb !important;
}

/* 确保表格单元格内容不溢出 */
.datasource-list :deep(.arco-table-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
