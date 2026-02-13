<template>
  <a-modal 
    :visible="visible" 
    title="选择查询字段" 
    width="600px"
    @ok="handleConfirm"
    @cancel="handleCancel"
  >
    <div class="column-select">
      <div class="header-actions">
        <a-space>
          <a-button size="small" @click="selectAll">全选</a-button>
          <a-button size="small" @click="selectNone">清空</a-button>
          <a-button size="small" @click="selectPrimaryKeys">仅主键</a-button>
        </a-space>
        <a-input-search 
          v-model="searchText" 
          placeholder="搜索字段..." 
          size="small"
          style="width: 200px"
        />
      </div>
      
      <div class="column-list">
        <a-checkbox-group v-model="selectedColumns" direction="vertical">
          <div 
            v-for="col in filteredColumns" 
            :key="col.name"
            class="column-item"
          >
            <a-checkbox :value="col.name">
              <div class="column-content">
                <div class="column-left">
                  <KeyIcon v-if="col.is_pk" />
                  <span class="column-name">{{ col.name }}</span>
                </div>
                <div class="column-right">
                  <a-tag size="small" :color="getTypeColor(col.type)">{{ col.type }}</a-tag>
                  <span v-if="col.comment" class="column-comment">{{ col.comment }}</span>
                </div>
              </div>
            </a-checkbox>
          </div>
        </a-checkbox-group>
      </div>

      <div class="footer-info">
        已选择 {{ selectedColumns.length }} / {{ columns.length }} 个字段
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from 'vue'

// Key 图标组件 (主键图标)
const KeyIcon = {
  render() {
    return h('svg', {
      viewBox: '0 0 1024 1024',
      version: '1.1',
      xmlns: 'http://www.w3.org/2000/svg',
      width: '1em',
      height: '1em',
      fill: 'currentColor',
      class: 'pk-icon'
    }, [
      h('path', {
        d: 'M823.8 349.8c-22.4-53.2-61.4-97.4-112.8-126.4-51.4-29-110.6-41.2-169.4-35-58.8 6.2-114.2 30.6-158.4 69.6-44.2 39-76.4 90.8-92 148.4-15.6 57.6-13.8 118.6 5.2 175.2L104 778.2V928h148l20-20v-84h84l20-20v-84h84l20-20v-84h84l28.2-28.2c56.6 19 117.6 20.8 175.2 5.2 57.6-15.6 109.4-47.8 148.4-92 39-44.2 63.4-99.6 69.6-158.4 6.2-58.8-6-118-35-169.4zM672 480c-26.5 0-48-21.5-48-48s21.5-48 48-48 48 21.5 48 48-21.5 48-48 48z'
      })
    ])
  }
}

export interface Column {
  name: string
  type: string
  is_pk?: boolean
  nullable?: boolean
  comment?: string
}

interface Props {
  visible: boolean
  columns: Column[]
  defaultSelected?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  defaultSelected: () => []
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'confirm', selectedColumns: string[]): void
}>()

const searchText = ref('')
const selectedColumns = ref<string[]>([])

watch(() => props.visible, (val) => {
  if (val) {
    // 默认全选或使用提供的默认值
    selectedColumns.value = props.defaultSelected.length > 0 
      ? [...props.defaultSelected]
      : props.columns.map(c => c.name)
  }
})

const filteredColumns = computed(() => {
  if (!searchText.value) return props.columns
  const text = searchText.value.toLowerCase()
  return props.columns.filter(col => 
    col.name.toLowerCase().includes(text) || 
    col.type.toLowerCase().includes(text) ||
    col.comment?.toLowerCase().includes(text)
  )
})

function selectAll() {
  selectedColumns.value = props.columns.map(c => c.name)
}

function selectNone() {
  selectedColumns.value = []
}

function selectPrimaryKeys() {
  selectedColumns.value = props.columns.filter(c => c.is_pk).map(c => c.name)
}

function getTypeColor(type: string): string {
  const t = type.toLowerCase()
  if (t.includes('int') || t.includes('number') || t.includes('decimal') || t.includes('float')) {
    return 'blue'
  }
  if (t.includes('char') || t.includes('text') || t.includes('string')) {
    return 'green'
  }
  if (t.includes('date') || t.includes('time')) {
    return 'orange'
  }
  if (t.includes('bool')) {
    return 'purple'
  }
  return 'gray'
}

function handleConfirm() {
  emit('confirm', selectedColumns.value)
  emit('update:visible', false)
}

function handleCancel() {
  emit('update:visible', false)
}
</script>

<style scoped>
.column-select {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e6eb;
}

.column-list {
  max-height: 450px;
  overflow-y: auto;
  padding: 8px 0;
}

.column-item {
  padding: 4px 0;
  border-bottom: 1px solid #f2f3f5;
}

.column-item:last-child {
  border-bottom: none;
}

.column-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.column-item:hover .column-content {
  background: #f7f8fa;
}

.column-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.pk-icon {
  color: #ff7d00;
  font-size: 14px;
}

.column-name {
  font-size: 14px;
  font-weight: 500;
  color: #1d2129;
}

.column-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-comment {
  font-size: 12px;
  color: #86909c;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.footer-info {
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
  text-align: center;
  font-size: 13px;
  color: #4e5969;
}

:deep(.arco-checkbox-group) {
  width: 100%;
}

:deep(.arco-checkbox) {
  width: 100%;
  margin-right: 0 !important;
}
</style>
