<template>
  <a-card class="query-steps">
    <a-steps :current="currentStep" direction="vertical">
      <!-- 自然语言 -->
      <a-step title="自然语言">
        <template #description>
          <div class="step-content">
            <div class="step-text">{{ naturalLanguage }}</div>
          </div>
        </template>
      </a-step>

      <!-- MQL -->
      <a-step title="MQL (指标查询语言)">
        <template #description>
          <div class="step-content">
            <div class="code-block">
              <pre v-if="!editingMql">{{ mql }}</pre>
              <a-textarea
                v-else
                v-model="editedMql"
                :auto-size="{ minRows: 3, maxRows: 10 }"
              />
            </div>
            <div class="step-actions">
              <a-button v-if="!editingMql" size="small" type="text" @click="startEditMql">
                <template #icon><icon-edit /></template>
                编辑
              </a-button>
              <template v-else>
                <a-button size="small" type="primary" @click="saveMql">保存</a-button>
                <a-button size="small" @click="cancelEditMql">取消</a-button>
              </template>
              <a-button size="small" type="text" @click="copyToClipboard(mql)">
                <template #icon><icon-copy /></template>
                复制
              </a-button>
            </div>
          </div>
        </template>
      </a-step>

      <!-- SQL -->
      <a-step title="SQL">
        <template #description>
          <div class="step-content">
            <div class="code-block sql">
              <pre v-if="!editingSql">{{ sql }}</pre>
              <a-textarea
                v-else
                v-model="editedSql"
                :auto-size="{ minRows: 3, maxRows: 10 }"
              />
            </div>
            <div class="step-actions">
              <a-button v-if="!editingSql" size="small" type="text" @click="startEditSql">
                <template #icon><icon-edit /></template>
                编辑
              </a-button>
              <template v-else>
                <a-button size="small" type="primary" @click="saveSql">保存</a-button>
                <a-button size="small" @click="cancelEditSql">取消</a-button>
              </template>
              <a-button size="small" type="text" @click="copyToClipboard(sql)">
                <template #icon><icon-copy /></template>
                复制
              </a-button>
            </div>
          </div>
        </template>
      </a-step>
    </a-steps>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

const props = defineProps<{
  naturalLanguage: string
  mql: string
  sql: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit-mql', mql: string): void
  (e: 'edit-sql', sql: string): void
}>()

const editingMql = ref(false)
const editingSql = ref(false)
const editedMql = ref('')
const editedSql = ref('')

const currentStep = computed(() => {
  if (props.loading) return 1
  if (props.sql) return 3
  if (props.mql) return 2
  return 1
})

function startEditMql() {
  editedMql.value = props.mql
  editingMql.value = true
}

function saveMql() {
  emit('edit-mql', editedMql.value)
  editingMql.value = false
}

function cancelEditMql() {
  editingMql.value = false
}

function startEditSql() {
  editedSql.value = props.sql
  editingSql.value = true
}

function saveSql() {
  emit('edit-sql', editedSql.value)
  editingSql.value = false
}

function cancelEditSql() {
  editingSql.value = false
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    Message.success('已复制到剪贴板')
  } catch {
    Message.error('复制失败')
  }
}
</script>

<style scoped>
.query-steps {
  background: var(--color-bg-1);
}

.step-content {
  margin-top: 8px;
}

.step-text {
  padding: 12px;
  background: var(--color-fill-2);
  border-radius: 4px;
  color: var(--color-text-1);
}

.code-block {
  padding: 12px;
  background: var(--color-fill-1);
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  overflow-x: auto;
}

.code-block pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-block.sql {
  background: #1e1e1e;
  color: #d4d4d4;
}

.step-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
