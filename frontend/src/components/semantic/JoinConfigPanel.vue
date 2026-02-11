<template>
  <div class="join-config-panel">
    <a-form :model="formData" layout="vertical" size="small">
      <!-- JOIN类型 -->
      <a-form-item label="连接类型">
        <a-select v-model="formData.joinType" @change="emitUpdate">
          <a-option value="INNER">
            <div class="join-option">
              <span class="join-icon">⚡</span>
              <div>
                <div class="join-type">INNER JOIN</div>
                <div class="join-desc">只返回匹配的记录</div>
              </div>
            </div>
          </a-option>
          <a-option value="LEFT">
            <div class="join-option">
              <span class="join-icon">⬅️</span>
              <div>
                <div class="join-type">LEFT JOIN</div>
                <div class="join-desc">返回左表所有记录</div>
              </div>
            </div>
          </a-option>
          <a-option value="RIGHT">
            <div class="join-option">
              <span class="join-icon">➡️</span>
              <div>
                <div class="join-type">RIGHT JOIN</div>
                <div class="join-desc">返回右表所有记录</div>
              </div>
            </div>
          </a-option>
          <a-option value="FULL">
            <div class="join-option">
              <span class="join-icon">↔️</span>
              <div>
                <div class="join-type">FULL OUTER JOIN</div>
                <div class="join-desc">返回两表所有记录</div>
              </div>
            </div>
          </a-option>
          <a-option value="CROSS">
            <div class="join-option">
              <span class="join-icon">✖️</span>
              <div>
                <div class="join-type">CROSS JOIN</div>
                <div class="join-desc">笛卡尔积</div>
              </div>
            </div>
          </a-option>
        </a-select>
      </a-form-item>

      <!-- JOIN条件 -->
      <a-form-item label="连接条件">
        <div class="conditions-list">
          <div 
            v-for="(cond, idx) in formData.conditions" 
            :key="idx"
            class="condition-item"
          >
            <a-select 
              :model-value="cond.left_column" 
              placeholder="左表字段"
              size="small"
              @change="(val: string) => handleLeftColumnChange(val, cond)"
            >
              <a-option 
                v-for="col in leftColumns" 
                :key="col.value" 
                :value="col.value"
              >
                {{ col.label }}
              </a-option>
            </a-select>
            
            <a-select 
              v-model="cond.operator" 
              size="small"
              style="width: 80px"
              @change="emitUpdate"
            >
              <a-option value="=">=</a-option>
              <a-option value="!=">!=</a-option>
              <a-option value=">">></a-option>
              <a-option value="<"><</a-option>
              <a-option value=">=">>=</a-option>
              <a-option value="<="><=</a-option>
            </a-select>
            
            <a-select 
              :model-value="cond.right_column" 
              placeholder="右表字段"
              size="small"
              @change="(val: string) => handleRightColumnChange(val, cond)"
            >
              <a-option 
                v-for="col in rightColumns" 
                :key="col.value" 
                :value="col.value"
              >
                {{ col.label }}
              </a-option>
            </a-select>
            
            <a-button 
              type="text" 
              size="mini" 
              status="danger"
              @click="removeCondition(idx)"
            >
              <icon-delete />
            </a-button>
          </div>
        </div>
        
        <a-button 
          size="small" 
          type="dashed" 
          long
          @click="addCondition"
        >
          <template #icon><icon-plus /></template>
          添加条件
        </a-button>
      </a-form-item>

      <!-- WHERE筛选条件 -->
      <a-form-item>
        <template #label>
          <div style="display: flex; justify-content: space-between; width: 100%">
            <span>筛选条件 (WHERE)</span>
            <a-switch 
              v-model="showFilters" 
              size="small"
              :checked-text="'开启'"
              :unchecked-text="'关闭'"
            />
          </div>
        </template>
        
        <div v-if="showFilters" class="filters-section">
          <div 
            v-for="(filter, idx) in formData.filters" 
            :key="idx"
            class="filter-item"
          >
            <a-select 
              :model-value="filter.column" 
              placeholder="字段"
              size="small"
              @change="(val: string) => handleFilterColumnChange(val, filter)"
            >
              <a-option 
                v-for="col in allColumns" 
                :key="col.value" 
                :value="col.value"
              >
                {{ col.label }}
              </a-option>
            </a-select>
            
            <a-select 
              v-model="filter.operator" 
              size="small"
              style="width: 100px"
              @change="emitUpdate"
            >
              <a-option value="=">=</a-option>
              <a-option value="!=">!=</a-option>
              <a-option value=">">></a-option>
              <a-option value="<"><</a-option>
              <a-option value=">=">>=</a-option>
              <a-option value="<="><=</a-option>
              <a-option value="LIKE">LIKE</a-option>
              <a-option value="IN">IN</a-option>
              <a-option value="IS NULL">IS NULL</a-option>
              <a-option value="IS NOT NULL">IS NOT NULL</a-option>
            </a-select>
            
            <a-input 
              v-if="!['IS NULL', 'IS NOT NULL'].includes(filter.operator)"
              v-model="filter.value" 
              placeholder="值"
              size="small"
              @change="emitUpdate"
            />
            
            <a-button 
              type="text" 
              size="mini" 
              status="danger"
              @click="removeFilter(idx)"
            >
              <icon-delete />
            </a-button>
          </div>
          
          <a-button 
            size="small" 
            type="dashed" 
            long
            @click="addFilter"
          >
            <template #icon><icon-plus /></template>
            添加筛选
          </a-button>
        </div>
      </a-form-item>

      <!-- SQL预览 -->
      <a-form-item label="SQL预览">
        <div class="sql-preview">
          <pre>{{ sqlPreview }}</pre>
        </div>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export interface JoinCondition {
  left_column: string
  operator: string
  right_column: string
}

export interface FilterCondition {
  column: string
  operator: string
  value: string
}

export interface JoinConfig {
  joinType: string
  conditions: JoinCondition[]
  filters?: FilterCondition[]
}

interface ColumnOption {
  label: string
  value: string
}

interface Props {
  config: JoinConfig
  leftTableAlias: string
  rightTableAlias: string
  leftColumns: ColumnOption[]
  rightColumns: ColumnOption[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update', config: JoinConfig): void
}>()

const formData = ref<JoinConfig>({
  joinType: 'INNER',
  conditions: [],
  filters: []
})

// 从 't0.sub_type_id' 中提取 'sub_type_id'
function extractColumnName(columnWithAlias: string): string {
  if (!columnWithAlias) return ''
  const parts = columnWithAlias.split('.')
  return parts.length > 1 ? (parts[1] || '') : columnWithAlias
}

// 辅助函数，处理 change 事件
function handleLeftColumnChange(val: string, cond: any) {
  // 创建新的 conditions 数组，确保响应式更新
  const newConditions = [...formData.value.conditions]
  const index = newConditions.indexOf(cond)
  if (index >= 0) {
    newConditions[index] = {
      ...cond,
      left_column: extractColumnName(val)
    }
    formData.value.conditions = newConditions
  }
  emitUpdate()
}

function handleRightColumnChange(val: string, cond: any) {
  // 创建新的 conditions 数组，确保响应式更新
  const newConditions = [...formData.value.conditions]
  const index = newConditions.indexOf(cond)
  if (index >= 0) {
    newConditions[index] = {
      ...cond,
      right_column: extractColumnName(val)
    }
    formData.value.conditions = newConditions
  }
  emitUpdate()
}

function handleFilterColumnChange(val: string, filter: any) {
  // 创建新的 filters 数组，确保响应式更新
  const newFilters = [...(formData.value.filters || [])]
  const index = newFilters.indexOf(filter)
  if (index >= 0) {
    newFilters[index] = {
      ...filter,
      column: extractColumnName(val)
    }
    formData.value.filters = newFilters
  }
  emitUpdate()
}

const showFilters = ref(false)

watch(() => props.config, (val) => {
  if (val) {
    formData.value = {
      joinType: val.joinType || 'INNER',
      conditions: val.conditions || [],
      filters: val.filters || []
    }
    showFilters.value = (val.filters?.length || 0) > 0
  }
}, { immediate: true, deep: true })

const allColumns = computed(() => {
  return [...props.leftColumns, ...props.rightColumns]
})

const sqlPreview = computed(() => {
  const { joinType, conditions, filters } = formData.value
  
  let sql = `${joinType} JOIN ${props.rightTableAlias}\n`
  
  if (conditions.length > 0) {
    const onClause = conditions
      .map(c => `${c.left_column} ${c.operator} ${c.right_column}`)
      .join(' AND ')
    sql += `  ON ${onClause}`
  }
  
  if (showFilters.value && filters && filters.length > 0) {
    const whereClause = filters
      .map(f => {
        if (['IS NULL', 'IS NOT NULL'].includes(f.operator)) {
          return `${f.column} ${f.operator}`
        }
        return `${f.column} ${f.operator} '${f.value}'`
      })
      .join(' AND ')
    sql += `\nWHERE ${whereClause}`
  }
  
  return sql
})

function addCondition() {
  formData.value.conditions.push({
    left_column: '',
    operator: '=',
    right_column: ''
  })
}

function removeCondition(index: number) {
  formData.value.conditions.splice(index, 1)
  emitUpdate()
}

function addFilter() {
  if (!formData.value.filters) {
    formData.value.filters = []
  }
  formData.value.filters.push({
    column: '',
    operator: '=',
    value: ''
  })
}

function removeFilter(index: number) {
  formData.value.filters?.splice(index, 1)
  emitUpdate()
}

function emitUpdate() {
  emit('update', formData.value)
}
</script>

<style scoped>
.join-config-panel {
  padding: 8px 0;
}

.join-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.join-icon {
  font-size: 20px;
  min-width: 24px;
}

.join-type {
  font-weight: 500;
  color: #1d2129;
}

.join-desc {
  font-size: 12px;
  color: #86909c;
  margin-top: 2px;
}

.conditions-list,
.filters-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.condition-item,
.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #f7f8fa;
  border-radius: 6px;
}

.condition-item > :deep(.arco-select),
.filter-item > :deep(.arco-select) {
  flex: 1;
}

.condition-item > :deep(.arco-input-wrapper),
.filter-item > :deep(.arco-input-wrapper) {
  flex: 1;
}

.sql-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}

.sql-preview pre {
  margin: 0;
  white-space: pre-wrap;
}
</style>
