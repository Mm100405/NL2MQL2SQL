<template>
  <div class="workbook-page">
    <a-page-header title="工作簿" subtitle="创建和管理数据处理工作流">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建工作簿
        </a-button>
      </template>
    </a-page-header>

    <!-- 工作簿列表 -->
    <a-card class="workbook-list">
      <template #title>
        <a-input-search
          v-model="searchText"
          placeholder="搜索工作簿"
          style="width: 300px"
        />
      </template>
      <template #extra>
        <a-radio-group v-model="viewMode" type="button" size="small">
          <a-radio value="card"><icon-apps /></a-radio>
          <a-radio value="list"><icon-list /></a-radio>
        </a-radio-group>
      </template>

      <!-- 卡片视图 -->
      <div v-if="viewMode === 'card'" class="workbook-grid">
        <a-card
          v-for="item in filteredWorkbooks"
          :key="item.id"
          class="workbook-card"
          hoverable
          @click="openWorkbook(item)"
        >
          <template #cover>
            <div class="workbook-cover">
              <icon-file :size="48" />
            </div>
          </template>
          <a-card-meta :title="item.name" :description="item.description">
            <template #avatar>
              <a-avatar :style="{ backgroundColor: item.color }">
                {{ item.name.charAt(0) }}
              </a-avatar>
            </template>
          </a-card-meta>
          <div class="workbook-info">
            <span><icon-clock-circle /> {{ item.updatedAt }}</span>
            <span><icon-user /> {{ item.owner }}</span>
          </div>
          <template #actions>
            <a-button type="text" size="small" @click.stop="editWorkbook(item)">
              <icon-edit />
            </a-button>
            <a-button type="text" size="small" status="danger" @click.stop="deleteWorkbook(item)">
              <icon-delete />
            </a-button>
          </template>
        </a-card>

        <!-- 空状态 -->
        <a-empty v-if="filteredWorkbooks.length === 0" description="暂无工作簿">
          <template #image>
            <icon-file :size="64" />
          </template>
        </a-empty>
      </div>

      <!-- 列表视图 -->
      <a-table
        v-else
        :columns="columns"
        :data="filteredWorkbooks"
        :pagination="{ pageSize: 10 }"
      >
        <template #name="{ record }">
          <a-link @click="openWorkbook(record)">{{ record.name }}</a-link>
        </template>
        <template #status="{ record }">
          <a-tag :color="record.status === 'active' ? 'green' : 'gray'">
            {{ record.status === 'active' ? '运行中' : '已停止' }}
          </a-tag>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="editWorkbook(record)">编辑</a-button>
            <a-button type="text" size="small" status="danger" @click="deleteWorkbook(record)">删除</a-button>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- 新建工作簿弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建工作簿"
      @ok="handleCreate"
      @cancel="showCreateModal = false"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="工作簿名称" required>
          <a-input v-model="createForm.name" placeholder="请输入工作簿名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入描述" :max-length="200" />
        </a-form-item>
        <a-form-item label="颜色标识">
          <a-space>
            <div
              v-for="color in colorOptions"
              :key="color"
              class="color-option"
              :class="{ active: createForm.color === color }"
              :style="{ backgroundColor: color }"
              @click="createForm.color = color"
            />
          </a-space>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface Workbook {
  id: number
  name: string
  description: string
  color: string
  status: 'active' | 'stopped'
  owner: string
  updatedAt: string
}

const searchText = ref('')
const viewMode = ref<'card' | 'list'>('card')
const showCreateModal = ref(false)

const createForm = ref({
  name: '',
  description: '',
  color: '#165DFF'
})

const colorOptions = ['#165DFF', '#0FC6C2', '#722ED1', '#F5319D', '#FF7D00', '#14C9C9']

// 模拟数据
const workbooks = ref<Workbook[]>([
  {
    id: 1,
    name: '销售数据ETL',
    description: '每日销售数据的抽取、转换和加载流程',
    color: '#165DFF',
    status: 'active',
    owner: 'admin',
    updatedAt: '2024-01-15 10:30'
  },
  {
    id: 2,
    name: '用户行为分析',
    description: '用户行为日志的处理和分析流程',
    color: '#0FC6C2',
    status: 'stopped',
    owner: 'analyst',
    updatedAt: '2024-01-14 16:20'
  },
  {
    id: 3,
    name: '财务报表生成',
    description: '月度财务报表的自动化生成流程',
    color: '#722ED1',
    status: 'active',
    owner: 'finance',
    updatedAt: '2024-01-13 09:00'
  }
])

const columns = [
  { title: '名称', dataIndex: 'name', slotName: 'name' },
  { title: '描述', dataIndex: 'description', ellipsis: true },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 100 },
  { title: '负责人', dataIndex: 'owner', width: 100 },
  { title: '更新时间', dataIndex: 'updatedAt', width: 160 },
  { title: '操作', slotName: 'actions', width: 120 }
]

const filteredWorkbooks = computed(() => {
  if (!searchText.value) return workbooks.value
  return workbooks.value.filter(w => 
    w.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
    w.description.toLowerCase().includes(searchText.value.toLowerCase())
  )
})

function openWorkbook(item: Workbook) {
  Message.info(`打开工作簿: ${item.name}`)
}

function editWorkbook(item: Workbook) {
  Message.info(`编辑工作簿: ${item.name}`)
}

function deleteWorkbook(item: Workbook) {
  Message.warning(`删除工作簿: ${item.name}`)
}

function handleCreate() {
  if (!createForm.value.name) {
    Message.error('请输入工作簿名称')
    return
  }
  workbooks.value.push({
    id: Date.now(),
    name: createForm.value.name,
    description: createForm.value.description,
    color: createForm.value.color,
    status: 'stopped',
    owner: 'admin',
    updatedAt: new Date().toLocaleString()
  })
  Message.success('创建成功')
  showCreateModal.value = false
  createForm.value = { name: '', description: '', color: '#165DFF' }
}
</script>

<style scoped>
.workbook-page {
  padding: 0;
}

.workbook-list {
  margin-top: 16px;
}

.workbook-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.workbook-card {
  cursor: pointer;
}

.workbook-cover {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7eb 100%);
  color: #86909c;
}

.workbook-info {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  font-size: 12px;
  color: #86909c;
}

.workbook-info span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.color-option {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.active {
  border-color: #1d2129;
}
</style>
