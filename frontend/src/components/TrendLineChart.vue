<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ECharts } from 'echarts/core'

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

interface TrendSeries {
  name: string
  data: number[]
  color?: string
}

const props = withDefaults(
  defineProps<{
    labels: string[]
    series: TrendSeries[]
    height?: number
  }>(),
  { height: 320 },
)

const chartRef = ref<HTMLDivElement>()
let chart: ECharts | null = null

function render(): void {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value: unknown) => `${Number(value).toFixed(1)} 分`,
      },
      legend: {
        top: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { color: '#475569', fontSize: 11 },
      },
      grid: { left: 42, right: 20, top: 46, bottom: 32 },
      xAxis: {
        type: 'category',
        data: props.labels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisTick: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: '#eef2f7' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
      },
      series: props.series.map((item) => ({
        type: 'line',
        name: item.name,
        data: item.data,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: item.color },
        itemStyle: { color: item.color },
        emphasis: { focus: 'series' },
      })),
    },
    true,
  )
}

function resize(): void {
  chart?.resize()
}

onMounted(() => {
  void nextTick(render)
  window.addEventListener('resize', resize)
})

watch(
  () => [props.labels, props.series],
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
  <div ref="chartRef" class="trend-chart" :style="{ height: `${height}px` }"></div>
</template>

<style scoped>
.trend-chart {
  width: 100%;
}
</style>
