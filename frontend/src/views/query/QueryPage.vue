<template>
  <div class="query-page">
    <!-- 模型未配置提醒 -->
    <ModelNotConfigured v-if="!settingsStore.isModelConfigured" />

    <!-- 正常问数界面 -->
    <template v-else>
      <!-- 输入区域 -->
      <a-card class="query-input-card">
        <div class="query-input-wrapper">
          <a-textarea
            v-model="queryInput"
            placeholder="请输入您的问题，例如：最近7天每天的销售额是多少？"
            :auto-size="{ minRows: 2, maxRows: 6 }"
            allow-clear
            @keydown.enter.ctrl="handleQuery"
          />
          <div class="query-actions">
            <span class="hint">Ctrl + Enter 发送</span>
            <a-button type="primary" :loading="loading" @click="handleQuery">
              <template #icon><icon-search /></template>
              开始问数
            </a-button>
          </div>
        </div>
      </a-card>

      <!-- 转换步骤展示 -->
      <QuerySteps
        v-if="queryResult"
        :natural-language="queryResult.natural_language"
        :mql="queryResult.mql"
        :sql="queryResult.sql"
        :loading="loading"
        @edit-mql="handleEditMql"
        @edit-sql="handleEditSql"
      />

      <!-- 查询结果 -->
      <a-card v-if="queryResult?.result" class="result-card">
        <template #title>
          <div class="result-header">
            <span>查询结果</span>
            <div class="result-meta">
              <a-tag color="blue">{{ queryResult.result.total_count }} 条记录</a-tag>
              <a-tag color="green">{{ queryResult.result.execution_time }}ms</a-tag>
            </div>
          </div>
        </template>
        <template #extra>
          <a-space>
            <a-radio-group v-model="viewMode" type="button" size="small">
              <a-radio value="table">表格</a-radio>
              <a-radio value="chart">图表</a-radio>
            </a-radio-group>
            <a-dropdown>
              <a-button size="small">
                <template #icon><icon-download /></template>
                导出
              </a-button>
              <template #content>
                <a-doption @click="handleExport('csv')">导出CSV</a-doption>
                <a-doption @click="handleExport('excel')">导出Excel</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </template>

        <!-- 表格视图 -->
        <a-table
          v-if="viewMode === 'table'"
          :columns="tableColumns"
          :data="tableData"
          :pagination="{ pageSize: 20 }"
          :scroll="{ x: '100%' }"
        />

        <!-- 图表视图 -->
        <ChartContainer
          v-else
          :columns="queryResult.result.columns"
          :data="queryResult.result.data"
          :chart-type="chartType"
          @change-type="chartType = $event"
        />
      </a-card>

      <!-- 分析面板 -->
      <a-card v-if="queryResult" class="analysis-card">
        <a-tabs default-active-key="drilldown">
          <a-tab-pane key="drilldown" title="下钻分析">
            <DrillDown
              :query-id="queryResult.query_id"
              :dimensions="availableDimensions"
              @drill="handleDrillDown"
            />
          </a-tab-pane>
          <a-tab-pane key="attribution" title="归因分析">
            <Attribution
              :query-id="queryResult.query_id"
              :metrics="availableMetrics"
              :dimensions="availableDimensions"
              @analyze="handleAttribution"
            />
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useSettingsStore } from '@/stores/settings'
import ModelNotConfigured from '@/components/query/ModelNotConfigured.vue'
import QuerySteps from '@/components/query/QuerySteps.vue'
import ChartContainer from '@/components/common/ChartContainer.vue'
import DrillDown from '@/components/query/DrillDown.vue'
import Attribution from '@/components/query/Attribution.vue'
import type { FullQueryResponse } from '@/api/types'
import { executeFullQuery } from '@/api/query'

const settingsStore = useSettingsStore()

const queryInput = ref('')
const loading = ref(false)
const queryResult = ref<FullQueryResponse | null>(null)
const viewMode = ref<'table' | 'chart'>('table')
const chartType = ref<'line' | 'bar' | 'pie'>('bar')

// 表格列
const tableColumns = computed(() => {
  if (!queryResult.value?.result?.columns) return []
  return queryResult.value.result.columns.map(col => ({
    title: col,
    dataIndex: col
  }))
})

// 表格数据
const tableData = computed(() => {
  if (!queryResult.value?.result) return []
  const { columns, data } = queryResult.value.result
  return data.map((row, index) => {
    const obj: Record<string, any> = { key: index }
    columns.forEach((col, i) => {
      obj[col] = row[i]
    })
    return obj
  })
})

// 可用维度（从结果中提取）
const availableDimensions = computed(() => {
  // TODO: 从语义层获取维度列表
  return ['日期', '地区', '产品类别', '渠道']
})

// 可用指标
const availableMetrics = computed(() => {
  // TODO: 从语义层获取指标列表
  return ['销售额', '订单数', '客单价']
})

// 执行查询
async function handleQuery() {
  if (!queryInput.value.trim()) {
    Message.warning('请输入查询内容')
    return
  }

  loading.value = true
  try {
    const result = await executeFullQuery({
      natural_language: queryInput.value
    })
    queryResult.value = result
    Message.success('查询成功')
  } catch (error) {
    console.error('Query failed:', error)
    Message.error('查询失败，请重试')
  } finally {
    loading.value = false
  }
}

// 编辑MQL
function handleEditMql(mql: string) {
  // TODO: 使用编辑后的MQL重新执行查询
  console.log('Edit MQL:', mql)
}

// 编辑SQL
function handleEditSql(sql: string) {
  // TODO: 使用编辑后的SQL直接执行
  console.log('Edit SQL:', sql)
}

// 导出
function handleExport(format: 'csv' | 'excel') {
  // TODO: 实现导出功能
  Message.info(`导出${format.toUpperCase()}功能开发中...`)
}

// 下钻分析
function handleDrillDown(dimension: string) {
  // TODO: 实现下钻分析
  Message.info(`下钻到维度: ${dimension}`)
}

// 归因分析
function handleAttribution(params: any) {
  // TODO: 实现归因分析
  Message.info('归因分析功能开发中...')
}
</script>

<style scoped>
.query-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.query-input-card {
  background: var(--color-bg-1);
}

.query-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.query-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  color: var(--color-text-3);
  font-size: 12px;
}

.result-card {
  background: var(--color-bg-1);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-meta {
  display: flex;
  gap: 8px;
}

.analysis-card {
  background: var(--color-bg-1);
}
</style>
