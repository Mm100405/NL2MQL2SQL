<template>
  <div class="table-node" :class="{ selected: selected }">
    <!-- 隐藏的连接点用于渲染连线 - 动态左右两侧 -->
    <!-- 左侧连接点作为 target（接收连接）- 在字段区域内均匀分布 -->
    <Handle
      v-for="handle in leftHandles"
      :key="handle.id"
      :id="handle.id"
      type="target"
      :position="Position.Left"
      class="invisible-handle"
      :style="handle.style"
    />
    <!-- 右侧连接点作为 source（发出连接）- 在字段区域内均匀分布 -->
    <Handle
      v-for="handle in rightHandles"
      :key="handle.id"
      :id="handle.id"
      type="source"
      :position="Position.Right"
      class="invisible-handle"
      :style="handle.style"
    />
    
    <div class="table-header">
      <icon-storage class="table-icon" />
      <span class="table-name">{{ data.label }}</span>
      <span class="table-alias">({{ data.alias }})</span>
      <a-space :size="4">
        <a-button 
          type="text" 
          size="mini" 
          class="edit-btn"
          @click.stop="showEditModal = true"
        >
          <icon-edit />
        </a-button>
        <a-button 
          type="text" 
          size="mini" 
          class="delete-btn"
          @click.stop="handleDelete"
        >
          <icon-delete />
        </a-button>
      </a-space>
    </div>
    <div class="table-columns-wrapper" ref="columnsWrapper" @scroll="checkScroll" @wheel.stop>
      <div class="table-columns">
        <div
          v-for="col in visibleColumns"
          :key="col.name"
          class="column-item"
          :class="{ 
            'is-pk': col.is_pk,
            'is-connecting': connectingColumn && connectingColumn.nodeId === data.alias && connectingColumn.columnName === col.name
          }"
          @click="handleColumnClick(col)"
        >
          <icon-key v-if="col.is_pk" class="pk-icon" />
          <span class="column-name">{{ col.name }}</span>
          <span class="column-type">{{ col.type }}</span>
        </div>
      </div>
    </div>
    <div v-if="showScrollHint" class="scroll-hint">
      <icon-down :style="{ fontSize: '12px' }" />
    </div>
    <div v-if="hiddenCount > 0" class="column-more">
      +{{ hiddenCount }} 个字段未选择
    </div>

    <!-- 编辑字段弹窗 -->
    <a-modal 
      v-model:visible="showEditModal" 
      title="编辑字段选择" 
      width="500px"
      @ok="handleSaveColumns"
    >
      <div class="column-edit-list">
        <a-checkbox-group v-model="selectedColumnNames" direction="vertical">
          <a-checkbox 
            v-for="col in allColumns" 
            :key="col.name" 
            :value="col.name"
            class="column-checkbox"
          >
            <div class="column-info">
              <icon-key v-if="col.is_pk" class="pk-icon" />
              <span class="col-name">{{ col.name }}</span>
              <span class="col-type">{{ col.type }}</span>
            </div>
          </a-checkbox>
        </a-checkbox-group>
      </div>
      <div class="select-actions">
        <a-button size="small" @click="selectAll">全选</a-button>
        <a-button size="small" @click="selectNone">清空</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, nextTick } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import type { NodeProps } from '@vue-flow/core'
import { IconDelete } from '@arco-design/web-vue/es/icon'

interface Column {
  name: string
  type: string
  is_pk?: boolean
  nullable?: boolean
  selected?: boolean
}

interface TableNodeData {
  label: string
  alias: string
  datasetId: string
  columns: Column[]
  selectedColumns?: string[]
  leftHandles?: number
  rightHandles?: number
}

const props = defineProps<NodeProps<TableNodeData>>()

const emit = defineEmits<{
  (e: 'update-columns', payload: { alias: string; selectedColumns: string[] }): void
  (e: 'column-click', payload: { nodeId: string; columnName: string; columnData: Column }): void
  (e: 'delete-node', nodeId: string): void
}>()

// 注入连接状态
const connectingColumn = inject<any>('connectingColumn', null)

const showEditModal = ref(false)
const selectedColumnNames = ref<string[]>(props.data.selectedColumns || props.data.columns.map(c => c.name))
const columnsWrapper = ref<HTMLElement | null>(null)
const showScrollHint = ref(false)

const allColumns = computed(() => props.data.columns || [])

const visibleColumns = computed(() => {
  return allColumns.value.filter(col => selectedColumnNames.value.includes(col.name))
})

const hiddenCount = computed(() => {
  return allColumns.value.length - visibleColumns.value.length
})

// 左右连接点配置 - 在表头下方的字段列表区域内均匀分布
// 使用 marginTop 调整垂直位置，配合 Position.Left/Right 使用
const leftHandles = computed(() => {
  const count = props.data.leftHandles || 0
  if (count === 0) return []
  const positions = []
  const startOffset = 60 // 表头高度约50px + 间距
  const spacing = 40 // 每个连接点之间的间距
  for (let i = 0; i < count; i++) {
    const offsetPx = startOffset + i * spacing
    positions.push({
      id: `${props.data.alias}-left-${i}`,
      style: { marginTop: `${offsetPx}px` }
    })
  }
  return positions
})

const rightHandles = computed(() => {
  const count = props.data.rightHandles || 0
  if (count === 0) return []
  const positions = []
  const startOffset = 60
  const spacing = 40
  for (let i = 0; i < count; i++) {
    const offsetPx = startOffset + i * spacing
    positions.push({
      id: `${props.data.alias}-right-${i}`,
      style: { marginTop: `${offsetPx}px` }
    })
  }
  return positions
})

function selectAll() {
  selectedColumnNames.value = allColumns.value.map(c => c.name)
}

function selectNone() {
  selectedColumnNames.value = []
}

function handleSaveColumns() {
  emit('update-columns', {
    alias: props.data.alias,
    selectedColumns: selectedColumnNames.value
  })
  showEditModal.value = false
}

function handleColumnClick(col: Column) {
  emit('column-click', {
    nodeId: props.data.alias,
    columnName: col.name,
    columnData: col
  })
}

function handleDelete() {
  emit('delete-node', props.data.alias)
}

function checkScroll() {
  if (!columnsWrapper.value) return
  const { scrollTop, scrollHeight, clientHeight } = columnsWrapper.value
  showScrollHint.value = scrollTop + clientHeight < scrollHeight - 5
}

onMounted(() => {
  nextTick(() => {
    checkScroll()
  })
})
</script>

<style scoped>
.table-node {
  background: #fff;
  border: 2px solid #e5e6eb;
  border-radius: 8px;
  width: 240px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  user-select: none;
  display: inline-block;
  position: relative;
}

/* 隐藏的连接点 - 用于渲染连线但不显示 */
.invisible-handle {
  opacity: 0 !important;
  pointer-events: auto !important;
  width: 12px !important;
  height: 12px !important;
  z-index: 100 !important;
  border: none !important;
  background: transparent !important;
  /* 确保不干扰 Vue Flow 的默认定位 */
  position: absolute !important;
}

.table-node:hover {
  border-color: #165dff;
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.15);
}

.table-node.selected {
  border-color: #165dff;
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.2);
}

.table-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #165dff 0%, #4080ff 100%);
  color: #fff;
  border-radius: 6px 6px 0 0;
  font-weight: 500;
}

.edit-btn {
  color: #fff !important;
  opacity: 0.8;
  padding: 2px 4px !important;
  height: auto !important;
}

.edit-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.2) !important;
}

.delete-btn {
  color: #fff !important;
  opacity: 0.8;
  padding: 2px 4px !important;
  height: auto !important;
}

.delete-btn:hover {
  opacity: 1;
  background: rgba(255, 77, 79, 0.3) !important;
}

.table-icon {
  font-size: 14px;
  pointer-events: none;
}

.table-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}

.table-alias {
  font-size: 12px;
  opacity: 0.8;
  pointer-events: none;
}

.table-columns-wrapper {
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: #c9cdd4 #f2f3f5;
}

.table-columns-wrapper::-webkit-scrollbar {
  width: 4px;
}

.table-columns-wrapper::-webkit-scrollbar-track {
  background: transparent;
}

.table-columns-wrapper::-webkit-scrollbar-thumb {
  background: rgba(201, 205, 212, 0.6);
  border-radius: 2px;
}

.table-columns-wrapper::-webkit-scrollbar-thumb:hover {
  background: rgba(169, 174, 184, 0.8);
}

.table-columns {
  padding: 4px 0;
  min-width: 100%;
}

.scroll-hint {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 6px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0.9) 40%, rgba(255,255,255,1) 100%);
  color: #165dff;
  pointer-events: none;
  animation: bounce 1.5s ease-in-out infinite;
  z-index: 10;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

.column-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  padding-right: 16px;
  border-bottom: 1px solid #f2f3f5;
  position: relative;
  transition: background 0.15s;
  height: 36px;
  user-select: none;
  cursor: pointer;
  white-space: nowrap;
}

.column-item:hover {
  background: #e8f3ff;
}

.column-item:last-child {
  border-bottom: none;
}

.column-item.is-pk {
  background: #fff8e6;
}

.column-item.is-pk:hover {
  background: #fff4d9;
}

.column-item.is-connecting {
  background: #d4eaff;
  box-shadow: inset 0 0 0 2px #165dff;
}

.pk-icon {
  color: #ff7d00;
  font-size: 12px;
  pointer-events: none;
}

.column-name {
  flex: 1;
  font-size: 13px;
  color: #1d2129;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}

.column-type {
  font-size: 11px;
  color: #86909c;
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
  pointer-events: none;
}

.column-more {
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  color: #86909c;
  background: #f7f8fa;
  border-top: 1px solid #f2f3f5;
}

.column-edit-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 12px 0;
}

.column-checkbox {
  width: 100%;
  padding: 8px 0;
  border-bottom: 1px solid #f2f3f5;
}

.column-info {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.col-name {
  flex: 1;
  font-size: 13px;
}

.col-type {
  font-size: 11px;
  color: #86909c;
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.select-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}

</style>
