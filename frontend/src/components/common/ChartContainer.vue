<template>
  <div class="chart-container">
    <div class="chart-toolbar">
      <a-radio-group v-model="currentType" type="button" size="small">
        <a-radio value="bar">柱状图</a-radio>
        <a-radio value="line">折线图</a-radio>
        <a-radio value="pie">饼图</a-radio>
      </a-radio-group>
    </div>
    <div ref="chartRef" class="chart-wrapper"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  columns: string[]
  data: any[][]
  chartType?: 'line' | 'bar' | 'pie'
}>()

const emit = defineEmits<{
  (e: 'change-type', type: 'line' | 'bar' | 'pie'): void
}>()

const chartRef = ref<HTMLElement>()
const currentType = ref(props.chartType || 'bar')
let chartInstance: echarts.ECharts | null = null

// 监听类型变化
watch(currentType, (newType) => {
  emit('change-type', newType)
  updateChart()
})

// 监听数据变化
watch(() => [props.columns, props.data], () => {
  updateChart()
}, { deep: true })

function updateChart() {
  if (!chartInstance || !props.columns.length || !props.data.length) return

  const xAxisData = props.data.map(row => row[0])
  const seriesData = props.columns.slice(1).map((col, index) => ({
    name: col,
    type: currentType.value,
    data: props.data.map(row => row[index + 1])
  }))

  let option: echarts.EChartsOption

  if (currentType.value === 'pie') {
    // 饼图取第一个数值列
    option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [{
        type: 'pie',
        radius: '50%',
        data: props.data.map(row => ({
          name: row[0],
          value: row[1]
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    }
  } else {
    option = {
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        data: props.columns.slice(1)
      },
      xAxis: {
        type: 'category',
        data: xAxisData
      },
      yAxis: {
        type: 'value'
      },
      series: seriesData
    }
  }

  chartInstance.setOption(option, true)
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()

  // 响应窗口大小变化
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  chartInstance?.resize()
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.chart-container {
  width: 100%;
}

.chart-toolbar {
  margin-bottom: 16px;
}

.chart-wrapper {
  width: 100%;
  height: 400px;
}
</style>
