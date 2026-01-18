<template>
  <div class="datasource-list">
    <a-card title="数据源管理">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><icon-plus /></template>
          新增数据源
        </a-button>
      </template>

      <a-table :columns="columns" :data="dataSources" :loading="loading">
        <template #type="{ record }">
          <a-tag>{{ record.type.toUpperCase() }}</a-tag>
        </template>
        <template #status="{ record }">
          <a-badge :status="getStatusBadge(record.status)" :text="getStatusText(record.status)" />
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="handleTest(record)">
              测试连接
            </a-button>
            <a-button type="text" size="small" @click="handleSync(record)">
              同步表
            </a-button>
            <a-button type="text" size="small" @click="handleEdit(record)">
              <template #icon><icon-edit /></template>
            </a-button>
            <a-popconfirm content="确定删除此数据源？" @ok="handleDelete(record.id)">
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
            <a-option value="sqlite">SQLite</a-option>
            <a-option value="clickhouse">ClickHouse</a-option>
          </a-select>
        </a-form-item>
        <template v-if="form.type !== 'sqlite'">
          <a-form-item field="connection_config.host" label="主机地址">
            <a-input v-model="form.connection_config.host" placeholder="localhost" />
          </a-form-item>
          <a-form-item field="connection_config.port" label="端口">
            <a-input-number v-model="form.connection_config.port" :placeholder="getDefaultPort()" />
          </a-form-item>
          <a-form-item field="connection_config.username" label="用户名">
            <a-input v-model="form.connection_config.username" placeholder="请输入用户名" />
          </a-form-item>
          <a-form-item field="connection_config.password" label="密码">
            <a-input-password v-model="form.connection_config.password" placeholder="请输入密码" />
          </a-form-item>
        </template>
        <a-form-item field="connection_config.database" label="数据库名">
          <a-input
            v-model="form.connection_config.database"
            :placeholder="form.type === 'sqlite' ? '数据库文件路径' : '数据库名称'"
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
import {
  getDataSources,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  testDataSourceConnection,
  syncDatasetFromSource
} from '@/api/semantic'
import type { DataSource } from '@/api/types'

const loading = ref(false)
const submitting = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const dataSources = ref<DataSource[]>([])

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
  { title: '名称', dataIndex: 'name' },
  { title: '类型', slotName: 'type' },
  { title: '数据库', dataIndex: 'connection_config.database' },
  { title: '状态', slotName: 'status' },
  { title: '操作', slotName: 'actions', width: 280 }
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
    inactive: 'default',
    error: 'error'
  }
  return badges[status] || 'default'
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
  Object.assign(form, {
    name: record.name,
    type: record.type,
    connection_config: { ...record.connection_config, password: '' }
  })
  modalVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
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

async function handleSync(record: DataSource) {
  try {
    const datasets = await syncDatasetFromSource(record.id)
    Message.success(`同步成功，发现 ${datasets.length} 个表`)
  } catch (error) {
    Message.error('同步失败')
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
</style>
