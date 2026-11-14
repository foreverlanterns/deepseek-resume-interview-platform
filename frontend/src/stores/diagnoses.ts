import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  createDiagnosis,
  fetchDiagnoses,
  fetchDiagnosis,
} from '@/api/diagnoses'
import type {
  DiagnosisCreatePayload,
  DiagnosisDetail,
  DiagnosisSummary,
} from '@/types/diagnosis'

function toSummary(detail: DiagnosisDetail): DiagnosisSummary {
  return {
    id: detail.id,
    resume_id: detail.resume_id,
    resume_filename: detail.resume_filename,
    resume_version_no: detail.resume_version_no,
    jd_id: detail.jd_id,
    jd_title: detail.jd_title,
    rubric_version: detail.rubric_version,
    total_score: detail.total_score,
    format_score: detail.format_score,
    completeness_score: detail.completeness_score,
    keyword_score: detail.keyword_score,
    jd_match_score: detail.jd_match_score,
    created_at: detail.created_at,
  }
}

export const useDiagnosisStore = defineStore('diagnoses', () => {
  const history = ref<DiagnosisSummary[]>([])
  const current = ref<DiagnosisDetail | null>(null)
  const loading = ref(false)
  const creating = ref(false)
  const error = ref<string | null>(null)

  async function loadHistory(resumeId?: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      history.value = await fetchDiagnoses(resumeId ? { resume_id: resumeId } : undefined)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '诊断历史加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function create(payload: DiagnosisCreatePayload): Promise<DiagnosisDetail> {
    creating.value = true
    error.value = null
    try {
      const detail = await createDiagnosis(payload)
      current.value = detail
      history.value = [toSummary(detail), ...history.value]
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '诊断失败'
      throw caught
    } finally {
      creating.value = false
    }
  }

  async function select(diagnosisId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      current.value = await fetchDiagnosis(diagnosisId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '诊断详情加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    history.value = []
    current.value = null
    error.value = null
  }

  return { history, current, loading, creating, error, loadHistory, create, select, reset }
})
