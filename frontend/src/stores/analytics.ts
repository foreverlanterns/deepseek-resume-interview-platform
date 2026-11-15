import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchAnalyticsOverview,
  fetchDiagnosisTrends,
  fetchInterviewTrends,
  fetchWeaknesses,
} from '@/api/analytics'
import type {
  AnalyticsOverview,
  DiagnosisTrendGroup,
  InterviewTrendGroup,
  WeaknessReport,
} from '@/types/analytics'

export const useAnalyticsStore = defineStore('analytics', () => {
  const overview = ref<AnalyticsOverview | null>(null)
  const diagnosisGroups = ref<DiagnosisTrendGroup[]>([])
  const interviewGroups = ref<InterviewTrendGroup[]>([])
  const weaknesses = ref<WeaknessReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(resumeId?: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [overviewData, diagnosisData, interviewData, weaknessData] = await Promise.all([
        fetchAnalyticsOverview(resumeId),
        fetchDiagnosisTrends({ resumeId }),
        fetchInterviewTrends({ resumeId }),
        fetchWeaknesses(resumeId),
      ])
      overview.value = overviewData
      diagnosisGroups.value = diagnosisData.groups
      interviewGroups.value = interviewData.groups
      weaknesses.value = weaknessData
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '成长数据加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    overview.value = null
    diagnosisGroups.value = []
    interviewGroups.value = []
    weaknesses.value = null
    error.value = null
  }

  return {
    overview,
    diagnosisGroups,
    interviewGroups,
    weaknesses,
    loading,
    error,
    load,
    reset,
  }
})
