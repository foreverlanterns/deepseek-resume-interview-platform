<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ECharts } from 'echarts/core'

echarts.use([RadarChart, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  scores: {
    format: number
    completeness: number
    keyword: number
    jd_match: number
  }
}>()

const chartRef = ref<HTMLDivElement>()
let chart: ECharts | null = null

function render(): void {
  if (!chartRef.value) {
    return
  }
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  chart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '格式', max: 100 },
        { name: '完整度', max: 100 },
        { name: '关键词', max: 100 },
        { name: 'JD 匹配', max: 100 },
      ],
      radius: '64%',
      splitNumber: 4,
      axisName: { color: '#475569', fontSize: 11 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['#f8fafc', '#ffffff'] } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 4,
        data: [
          {
            value: [
              props.scores.format,
              props.scores.completeness,
              props.scores.keyword,
              props.scores.jd_match,
            ],
            name: '当前得分',
          },
        ],
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' },
        areaStyle: { color: 'rgba(37, 99, 235, 0.16)' },
      },
    ],
  })
}

function resize(): void {
  chart?.resize()
}

onMounted(() => {
  void nextTick(render)
  window.addEventListener('resize', resize)
})

watch(
  () => props.scores,
  () => render(),
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="chartRef" class="radar-chart"></div>
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 320px;
}
</style>
