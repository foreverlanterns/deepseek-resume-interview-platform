import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { fetchHealth } from '@/api/health'
import type { HealthResponse } from '@/types/api'

export const useAppStore = defineStore('app', () => {
  const health = ref<HealthResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const databaseOnline = computed(() => health.value?.database === 'ok')
  const checked = computed(() => health.value !== null || error.value !== null)

  async function checkHealth(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      health.value = await fetchHealth()
    } catch (caught) {
      health.value = null
      error.value = caught instanceof Error ? caught.message : '健康检查失败'
    } finally {
      loading.value = false
    }
  }

  return { health, loading, error, databaseOnline, checked, checkHealth }
})
