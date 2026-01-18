<template>
  <div class="history-page">
    <a-card title="查询历史">
      <template #extra>
        <a-input-search
          v-model="searchText"
          placeholder="搜索查询内容"
          style="width: 240px"
          allow-clear
        />
      </template>

      <a-table
        :columns="columns"
        :data="filteredHistory"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
      >
        <template #natural_language="{ record }">
          <a-typography-paragraph
            :ellipsis="{ rows: 2 }"
            style="margin: 0"
          >
            {{ record.natural_language }}
          </a-typography-paragraph>
        </template>
        <template #status="{ record }">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>
        <template #execution_time="{ record }">
          {{ record.execution_time }}ms
        </template>
        <template #created_at="{ record }">
          {{ formatDate(record.created_at) }}
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="handleView(record)">
              <template #icon><icon-eye /></template>
            </a-button>
            <a-button type="text" size="small" @click="handleRerun(record)">
              <template #icon><icon-refresh /></template>
            </a-button>
            <a-popconfirm content="确定删除此记录？" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">
                <template #icon><icon-delete /></template>
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getQueryHistory, deleteQueryHistory } from '@/api/query'
import type { QueryHistory } from '@/api/types'

const router = useRouter()

const loading = ref(false)
const searchText = ref('')
const historyList = ref<QueryHistory[]>([])
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: '查询内容', slotName: 'natural_language', width: 300 },
  { title: '状态', slotName: 'status', width: 100 },
  { title: '结果数', dataIndex: 'result_count', width: 100 },
  { title: '耗时', slotName: 'execution_time', width: 100 },
  { title: '查询时间', slotName: 'created_at', width: 180 },
  { title: '操作', slotName: 'actions', width: 150, fixed: 'right' }
]

const filteredHistory = computed(() => {
  if (!searchText.value) return historyList.value
  return historyList.value.filter(item =>
    item.natural_language.toLowerCase().includes(searchText.value.toLowerCase())
  )
})

async function fetchHistory() {
  loading.value = true
  try {
    const res = await getQueryHistory({
      page: pagination.value.current,
      page_size: pagination.value.pageSize
    })
    historyList.value = res.items
    pagination.value.total = res.total
  } catch (error) {
    console.error('Failed to fetch history:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.value.current = page
  fetchHistory()
}

function handleView(record: QueryHistory) {
  // TODO: 打开详情弹窗或跳转
  Message.info('查看详情功能开发中...')
}

function handleRerun(record: QueryHistory) {
  router.push({
    name: 'Query',
    query: { q: record.natural_language }
  })
}

async function handleDelete(id: string) {
  try {
    await deleteQueryHistory(id)
    Message.success('删除成功')
    fetchHistory()
  } catch (error) {
    Message.error('删除失败')
  }
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    success: 'green',
    failed: 'red',
    timeout: 'orange'
  }
  return colors[status] || 'gray'
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    success: '成功',
    failed: '失败',
    timeout: '超时'
  }
  return texts[status] || status
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-page {
  height: 100%;
}
</style>
