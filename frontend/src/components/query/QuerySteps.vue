<template>
  <div class="analysis-process">
    <div class="process-header" @click="expanded = !expanded">
      <icon-bulb />
      <span>分析过程</span>
      <icon-up v-if="expanded" />
      <icon-down v-else />
    </div>

    <div v-if="expanded" class="process-content">
      <div v-for="(step, index) in steps" :key="index" class="process-step">
        <div class="step-line" :class="{ last: index === steps.length - 1 }">
          <div class="step-dot">
            <icon-check-circle-fill v-if="step.status === 'success'" />
            <icon-loading v-else-if="step.status === 'loading'" />
            <div v-else class="dot-inner"></div>
          </div>
        </div>
        <div class="step-main">
          <div class="step-title">{{ step.title }}</div>
          <div class="step-body">
            <!-- MQL生成阶段的MQL展示 -->
            <div v-if="step.title.includes('MQL生成') && step.extra?.mql" class="mql-section">
              <div class="content-text">
                <div v-for="(line, lIdx) in step.content.split('\n')" :key="lIdx" class="content-line">
                  {{ line }}
                </div>
              </div>
              <div class="mql-code-wrapper">
                <div class="mql-code-header">
                  <icon-copy class="copy-btn" @click="copyToClipboard(JSON.stringify(step.extra.mql, null, 2))" />
                </div>
                <pre class="mql-code">{{ JSON.stringify(step.extra.mql, null, 2) }}</pre>
              </div>
            </div>
            <!-- 执行阶段的SQL展示 -->
            <div v-else-if="step.title.includes('执行阶段') && step.extra?.sql" class="sql-section">
              <div class="content-text">
                <div v-for="(line, lIdx) in step.content.split('\n')" :key="lIdx" class="content-line">
                  {{ line }}
                </div>
              </div>
              <div class="sql-code-wrapper">
                <div class="sql-code-header">
                  <icon-copy class="copy-btn" @click="copyToClipboard(step.extra.sql)" />
                </div>
                <pre class="sql-code">{{ step.extra.sql }}</pre>
              </div>
            </div>
            <!-- 解释阶段的洞察展示 -->
            <div v-else-if="step.title.includes('解释阶段') && step.extra?.insights && step.extra.insights.length > 0" class="insights-section">
              <div class="content-text">
                <div v-for="(line, lIdx) in step.content.split('\n')" :key="lIdx" class="content-line">
                  {{ line }}
                </div>
              </div>
              <div v-if="step.extra.summary" class="content-line" style="margin-top: 12px; color: var(--color-text-1); font-weight: 500;">
                {{ step.extra.summary }}
              </div>
              <div class="insights-list">
                <div v-for="(insight, iIdx) in step.extra.insights" :key="iIdx" class="insight-item">
                  <icon-check-circle class="insight-icon" />
                  <span>{{ insight }}</span>
                </div>
              </div>
            </div>
            <!-- 默认内容展示 -->
            <div v-else class="content-text">
              <div v-for="(line, lIdx) in step.content.split('\n')" :key="lIdx" class="content-line">
                {{ line }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { AnalysisStep } from '@/api/types'

const props = defineProps<{
  steps: AnalysisStep[]
}>()

const expanded = ref(true)

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
.analysis-process {
  margin: 16px 0;
  border-radius: 8px;
}

.process-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  color: var(--color-text-2);
  font-size: 13px;
  width: fit-content;
  background: var(--color-fill-1);
  border-radius: 20px;
}

.process-content {
  margin-top: 16px;
  padding-left: 8px;
}

.process-step {
  display: flex;
  gap: 16px;
}

.step-line {
  position: relative;
  width: 20px;
  display: flex;
  justify-content: center;
}

.step-line::before {
  content: '';
  position: absolute;
  top: 20px;
  bottom: 0;
  width: 1px;
  background: var(--color-border);
}

.step-line.last::before {
  display: none;
}

.step-dot {
  position: relative;
  z-index: 1;
  width: 16px;
  height: 16px;
  background: var(--color-bg-1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #165dff;
  font-size: 16px;
}

.dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
}

.step-main {
  padding-bottom: 24px;
  flex: 1;
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-1);
  margin-bottom: 8px;
}

.step-body {
  color: var(--color-text-2);
  font-size: 13px;
  line-height: 1.6;
}

.content-line {
  margin-bottom: 4px;
}

.mql-code-wrapper {
  margin-top: 12px;
  background: #f8f9fb;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  position: relative;
  max-width: 600px;
}

.mql-code-header {
  display: flex;
  justify-content: flex-end;
  padding: 8px;
}

.copy-btn {
  cursor: pointer;
  color: var(--color-text-3);
}

.copy-btn:hover {
  color: #165dff;
}

.mql-code {
  margin: 0;
  padding: 0 16px 16px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #4e5969;
  overflow-x: auto;
  white-space: pre-wrap;
}

.mql-expand {
  display: flex;
  justify-content: center;
  padding: 4px;
  border-top: 1px solid #e5e6eb;
  cursor: pointer;
  color: #165dff;
}

.sql-code-wrapper {
  margin-top: 12px;
  background: #f8f9fb;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  position: relative;
  max-width: 600px;
}

.sql-code-header {
  display: flex;
  justify-content: flex-end;
  padding: 8px;
}

.sql-code {
  margin: 0;
  padding: 0 16px 16px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #4e5969;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.insights-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f5ff;
  border-radius: 6px;
  color: var(--color-text-2);
  font-size: 13px;
}

.insight-icon {
  color: #165dff;
  font-size: 14px;
  margin-top: 2px;
}

.tags-section {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-label {
  font-size: 12px;
  color: var(--color-text-3);
}
</style>
