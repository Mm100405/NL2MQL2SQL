<template>
  <div class="consolidation-page">
    <a-page-header title="数据整合" subtitle="配置数据合并、清洗和转换规则">
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          新建整合规则
        </a-button>
      </template>
    </a-page-header>

    <!-- 整合规则列表 -->
    <a-card class="rule-list">
      <a-tabs default-active-key="merge">
        <a-tab-pane key="merge" title="数据合并">
          <div class="rule-grid">
            <a-card v-for="rule in mergeRules" :key="rule.id" class="rule-card" hoverable>
              <div class="rule-header">
                <a-tag :color="rule.enabled ? 'green' : 'gray'">
                  {{ rule.enabled ? '已启用' : '已禁用' }}
                </a-tag>
                <a-dropdown>
                  <a-button type="text" size="small"><icon-more /></a-button>
                  <template #content>
                    <a-doption @click="editRule(rule)">编辑</a-doption>
                    <a-doption @click="toggleRule(rule)">
                      {{ rule.enabled ? '禁用' : '启用' }}
                    </a-doption>
                    <a-doption class="danger" @click="deleteRule(rule)">删除</a-doption>
                  </template>
                </a-dropdown>
              </div>
              <div class="rule-title">{{ rule.name }}</div>
              <div class="rule-desc">{{ rule.description }}</div>
              <div class="rule-meta">
                <div class="meta-item">
                  <icon-storage /> {{ rule.sourceTables.length }} 个源表
                </div>
                <div class="meta-item">
                  <icon-arrow-right /> {{ rule.targetTable }}
                </div>
              </div>
              <div class="rule-stats">
                <span>合并策略: {{ rule.strategy }}</span>
                <span>|</span>
                <span>执行次数: {{ rule.execCount }}</span>
              </div>
            </a-card>
          </div>
        </a-tab-pane>

        <a-tab-pane key="clean" title="数据清洗">
          <a-table :columns="cleanColumns" :data="cleanRules" :pagination="false">
            <template #type="{ record }">
              <a-tag :color="getCleanTypeColor(record.type)">
                {{ record.type }}
              </a-tag>
            </template>
            <template #condition="{ record }">
              <code class="condition-code">{{ record.condition }}</code>
            </template>
            <template #enabled="{ record }">
              <a-switch v-model="record.enabled" size="small" />
            </template>
            <template #actions="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="editCleanRule(record)">编辑</a-button>
                <a-button type="text" size="small" status="danger" @click="deleteCleanRule(record)">删除</a-button>
              </a-space>
            </template>
          </a-table>
          <div class="add-rule-btn">
            <a-button type="dashed" long @click="showCleanModal = true">
              <template #icon><icon-plus /></template>
              添加清洗规则
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="transform" title="数据转换">
          <div class="transform-list">
            <a-collapse :default-active-key="['1']">
              <a-collapse-item v-for="item in transformRules" :key="item.id" :header="item.name">
                <template #extra>
                  <a-tag :color="item.enabled ? 'arcoblue' : 'gray'" @click.stop>
                    {{ item.enabled ? '已启用' : '已禁用' }}
                  </a-tag>
                </template>
                <div class="transform-content">
                  <div class="transform-section">
                    <div class="section-title">输入字段</div>
                    <div class="field-list">
                      <a-tag v-for="field in item.inputFields" :key="field">{{ field }}</a-tag>
                    </div>
                  </div>
                  <div class="transform-arrow">
                    <icon-arrow-right :size="24" />
                  </div>
                  <div class="transform-section">
                    <div class="section-title">转换逻辑</div>
                    <pre class="transform-logic">{{ item.logic }}</pre>
                  </div>
                  <div class="transform-arrow">
                    <icon-arrow-right :size="24" />
                  </div>
                  <div class="transform-section">
                    <div class="section-title">输出字段</div>
                    <div class="field-list">
                      <a-tag v-for="field in item.outputFields" :key="field" color="green">{{ field }}</a-tag>
                    </div>
                  </div>
                </div>
                <div class="transform-actions">
                  <a-button type="text" size="small" @click="editTransform(item)">编辑</a-button>
                  <a-button type="text" size="small" @click="testTransform(item)">测试</a-button>
                  <a-button type="text" size="small" status="danger" @click="deleteTransform(item)">删除</a-button>
                </div>
              </a-collapse-item>
            </a-collapse>
            <div class="add-rule-btn">
              <a-button type="dashed" long @click="showTransformModal = true">
                <template #icon><icon-plus /></template>
                添加转换规则
              </a-button>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 新建合并规则弹窗 -->
    <a-modal
      v-model:visible="showCreateModal"
      title="新建数据合并规则"
      width="640px"
      @ok="handleCreate"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="规则名称" required>
          <a-input v-model="createForm.name" placeholder="请输入规则名称" />
        </a-form-item>
        <a-form-item label="源数据表" required>
          <a-select v-model="createForm.sourceTables" placeholder="请选择源表" multiple>
            <a-option value="orders">orders</a-option>
            <a-option value="order_items">order_items</a-option>
            <a-option value="users">users</a-option>
            <a-option value="products">products</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标表" required>
          <a-input v-model="createForm.targetTable" placeholder="请输入目标表名" />
        </a-form-item>
        <a-form-item label="合并策略" required>
          <a-radio-group v-model="createForm.strategy">
            <a-radio value="union">UNION (去重合并)</a-radio>
            <a-radio value="union_all">UNION ALL (保留重复)</a-radio>
            <a-radio value="join">JOIN (关联合并)</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="createForm.description" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'

interface MergeRule {
  id: number
  name: string
  description: string
  sourceTables: string[]
  targetTable: string
  strategy: string
  enabled: boolean
  execCount: number
}

interface CleanRule {
  id: number
  name: string
  type: string
  field: string
  condition: string
  enabled: boolean
}

interface TransformRule {
  id: number
  name: string
  inputFields: string[]
  outputFields: string[]
  logic: string
  enabled: boolean
}

const showCreateModal = ref(false)
const showCleanModal = ref(false)
const showTransformModal = ref(false)

const createForm = ref({
  name: '',
  sourceTables: [] as string[],
  targetTable: '',
  strategy: 'union',
  description: ''
})

const mergeRules = ref<MergeRule[]>([
  {
    id: 1,
    name: '订单宽表合并',
    description: '合并订单主表和明细表生成订单宽表',
    sourceTables: ['orders', 'order_items'],
    targetTable: 'dwd_order_wide',
    strategy: 'JOIN',
    enabled: true,
    execCount: 156
  },
  {
    id: 2,
    name: '用户行为日志合并',
    description: '合并多个来源的用户行为日志',
    sourceTables: ['log_web', 'log_app', 'log_mini'],
    targetTable: 'ods_user_behavior',
    strategy: 'UNION ALL',
    enabled: true,
    execCount: 89
  }
])

const cleanRules = ref<CleanRule[]>([
  { id: 1, name: '空值过滤', type: '过滤', field: 'user_id', condition: 'user_id IS NOT NULL', enabled: true },
  { id: 2, name: '去重', type: '去重', field: 'order_id', condition: 'ROW_NUMBER() = 1', enabled: true },
  { id: 3, name: '格式校验', type: '校验', field: 'phone', condition: "phone REGEXP '^1[3-9]\\d{9}$'", enabled: false },
  { id: 4, name: '异常值处理', type: '替换', field: 'amount', condition: 'amount < 0 THEN 0', enabled: true }
])

const transformRules = ref<TransformRule[]>([
  {
    id: 1,
    name: '日期格式转换',
    inputFields: ['create_time'],
    outputFields: ['create_date', 'create_hour'],
    logic: "DATE(create_time) AS create_date,\nHOUR(create_time) AS create_hour",
    enabled: true
  },
  {
    id: 2,
    name: '金额单位转换',
    inputFields: ['amount_cent'],
    outputFields: ['amount_yuan'],
    logic: "amount_cent / 100.0 AS amount_yuan",
    enabled: true
  },
  {
    id: 3,
    name: '用户等级映射',
    inputFields: ['user_level'],
    outputFields: ['level_name'],
    logic: "CASE user_level\n  WHEN 1 THEN '普通'\n  WHEN 2 THEN '银卡'\n  WHEN 3 THEN '金卡'\n  ELSE '未知'\nEND AS level_name",
    enabled: true
  }
])

const cleanColumns = [
  { title: '规则名称', dataIndex: 'name' },
  { title: '类型', slotName: 'type', width: 80 },
  { title: '字段', dataIndex: 'field', width: 120 },
  { title: '条件', slotName: 'condition' },
  { title: '启用', slotName: 'enabled', width: 80 },
  { title: '操作', slotName: 'actions', width: 120 }
]

function getCleanTypeColor(type: string) {
  const colors: Record<string, string> = {
    '过滤': 'blue',
    '去重': 'green',
    '校验': 'orange',
    '替换': 'purple'
  }
  return colors[type] || 'gray'
}

function editRule(rule: MergeRule) {
  Message.info(`编辑规则: ${rule.name}`)
}

function toggleRule(rule: MergeRule) {
  rule.enabled = !rule.enabled
  Message.success(rule.enabled ? '规则已启用' : '规则已禁用')
}

function deleteRule(rule: MergeRule) {
  Message.warning(`删除规则: ${rule.name}`)
}

function editCleanRule(rule: CleanRule) {
  Message.info(`编辑清洗规则: ${rule.name}`)
}

function deleteCleanRule(rule: CleanRule) {
  Message.warning(`删除清洗规则: ${rule.name}`)
}

function editTransform(rule: TransformRule) {
  Message.info(`编辑转换规则: ${rule.name}`)
}

function testTransform(rule: TransformRule) {
  Message.info(`测试转换规则: ${rule.name}`)
}

function deleteTransform(rule: TransformRule) {
  Message.warning(`删除转换规则: ${rule.name}`)
}

function handleCreate() {
  if (!createForm.value.name || createForm.value.sourceTables.length === 0 || !createForm.value.targetTable) {
    Message.error('请填写必填项')
    return
  }
  mergeRules.value.push({
    id: Date.now(),
    name: createForm.value.name,
    description: createForm.value.description,
    sourceTables: createForm.value.sourceTables,
    targetTable: createForm.value.targetTable,
    strategy: createForm.value.strategy.toUpperCase(),
    enabled: false,
    execCount: 0
  })
  Message.success('创建成功')
  showCreateModal.value = false
}
</script>

<style scoped>
.consolidation-page {
  padding: 0;
}

.rule-list {
  margin-top: 16px;
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.rule-card {
  padding: 16px;
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.rule-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.rule-desc {
  font-size: 13px;
  color: #86909c;
  margin-bottom: 12px;
}

.rule-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #4e5969;
}

.rule-stats {
  font-size: 12px;
  color: #86909c;
  display: flex;
  gap: 8px;
}

.condition-code {
  background: #f2f3f5;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.add-rule-btn {
  margin-top: 16px;
}

.transform-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 0;
}

.transform-section {
  flex: 1;
}

.section-title {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}

.field-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.transform-arrow {
  display: flex;
  align-items: center;
  color: #c9cdd4;
  padding-top: 20px;
}

.transform-logic {
  background: #f7f8fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  margin: 0;
  white-space: pre-wrap;
}

.transform-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}

:deep(.danger) {
  color: #f53f3f !important;
}
</style>
