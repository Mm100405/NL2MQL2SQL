<template>
  <div class="lineage-page">
    <a-card title="血缘关系">
      <template #extra>
        <a-space>
          <a-select v-model="entityType" placeholder="选择类型" style="width: 120px">
            <a-option value="metric">指标</a-option>
            <a-option value="dataset">数据集</a-option>
          </a-select>
          <a-select
            v-model="selectedEntity"
            placeholder="选择实体"
            style="width: 200px"
            allow-search
          >
            <a-option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</a-option>
          </a-select>
          <a-button type="primary" @click="fetchLineage">
            <template #icon><icon-search /></template>
            查询血缘
          </a-button>
        </a-space>
      </template>

      <div v-if="!lineageData" class="empty-state">
        <a-empty description="选择实体后查询血缘关系" />
      </div>
      
      <div v-else class="lineage-container">
        <div ref="graphRef" class="lineage-graph"></div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import * as echarts from 'echarts'
import { getMetrics, getDatasets, getMetricLineage, getDatasetLineage } from '@/api/semantic'
import type { Metric, Dataset } from '@/api/types'

const route = useRoute()
const graphRef = ref<HTMLElement>()
const entityType = ref('metric')
const selectedEntity = ref('')
const entities = ref<(Metric | Dataset)[]>([])
const lineageData = ref<any>(null)
let chartInstance: echarts.ECharts | null = null

// 从路由参数初始化
onMounted(async () => {
  if (route.query.type) {
    entityType.value = route.query.type as string
  }
  await fetchEntities()
  if (route.query.id) {
    selectedEntity.value = route.query.id as string
    fetchLineage()
  }
})

watch(entityType, () => {
  selectedEntity.value = ''
  lineageData.value = null
  fetchEntities()
})

async function fetchEntities() {
  try {
    if (entityType.value === 'metric') {
      entities.value = await getMetrics()
    } else {
      entities.value = await getDatasets()
    }
  } catch (error) {
    console.error('Failed to fetch entities:', error)
  }
}

async function fetchLineage() {
  if (!selectedEntity.value) {
    Message.warning('请先选择实体')
    return
  }

  try {
    if (entityType.value === 'metric') {
      lineageData.value = await getMetricLineage(selectedEntity.value)
    } else {
      lineageData.value = await getDatasetLineage(selectedEntity.value)
    }
    await nextTick()
    renderGraph()
  } catch (error) {
    Message.error('获取血缘失败')
  }
}

function renderGraph() {
  if (!graphRef.value || !lineageData.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(graphRef.value)
  }

  // 模拟血缘数据（实际应从API返回）
  const nodes = [
    { name: '数据源', category: 0 },
    { name: '数据集', category: 1 },
    { name: '指标', category: 2 }
  ]
  
  const links = [
    { source: '数据源', target: '数据集' },
    { source: '数据集', target: '指标' }
  ]

  const option: echarts.EChartsOption = {
    tooltip: {},
    legend: {
      data: ['数据源', '数据集', '指标']
    },
    series: [{
      type: 'graph',
      layout: 'force',
      symbolSize: 50,
      roam: true,
      label: {
        show: true
      },
      edgeSymbol: ['circle', 'arrow'],
      edgeSymbolSize: [4, 10],
      data: nodes.map(n => ({
        ...n,
        symbolSize: 60,
        itemStyle: {
          color: ['#5470c6', '#91cc75', '#fac858'][n.category]
        }
      })),
      links: links,
      lineStyle: {
        opacity: 0.9,
        width: 2,
        curveness: 0
      },
      force: {
        repulsion: 200
      }
    }]
  }

  chartInstance.setOption(option)
}

// 窗口大小变化时重新渲染
window.addEventListener('resize', () => {
  chartInstance?.resize()
})
</script>

<style scoped>
.lineage-page {
  height: 100%;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.lineage-container {
  width: 100%;
  height: 500px;
}

.lineage-graph {
  width: 100%;
  height: 100%;
}
</style>
