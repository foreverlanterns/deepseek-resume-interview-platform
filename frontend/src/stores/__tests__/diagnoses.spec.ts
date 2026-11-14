import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DiagnosisDetail, DiagnosisSummary } from '@/types/diagnosis'

const { createDiagnosis, fetchDiagnoses, fetchDiagnosis } = vi.hoisted(() => ({
  createDiagnosis: vi.fn(),
  fetchDiagnoses: vi.fn(),
  fetchDiagnosis: vi.fn(),
}))

vi.mock('@/api/diagnoses', () => ({
  createDiagnosis,
  fetchDiagnoses,
  fetchDiagnosis,
}))

import { useDiagnosisStore } from '@/stores/diagnoses'

const summary: DiagnosisSummary = {
  id: 'diag-1',
  resume_id: 'resume-1',
  resume_filename: 'resume.pdf',
  resume_version_no: 1,
  jd_id: 'jd-1',
  jd_title: '后端开发工程师',
  rubric_version: 'rubric_v1',
  total_score: 71.75,
  format_score: 100,
  completeness_score: 100,
  keyword_score: 67,
  jd_match_score: 50,
  created_at: '2026-11-15T00:00:00Z',
}

const detail: DiagnosisDetail = {
  ...summary,
  weights: { format: 0.15, completeness: 0.2, keyword: 0.25, jd_match: 0.4 },
  format_details: [],
  completeness_details: [],
  keyword_details: {
    score: 67,
    matched_count: 2,
    total_count: 3,
    matched_weight: 4,
    total_weight: 6,
    hits: [],
  },
  jd_match_details: {
    score: 50,
    matched_count: 1,
    partial_count: 1,
    missing_count: 1,
    total: 3,
    matches: [],
  },
  suggestions: [],
  summary: '总分 71.75',
  model_name: 'fake-model',
  prompt_version: 'diagnosis_prompt_v1',
}

describe('useDiagnosisStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('加载诊断历史', async () => {
    fetchDiagnoses.mockResolvedValue([summary])
    const store = useDiagnosisStore()

    await store.loadHistory('resume-1')

    expect(fetchDiagnoses).toHaveBeenCalledWith({ resume_id: 'resume-1' })
    expect(store.history).toEqual([summary])
  })

  it('创建诊断后设置当前结果并插入历史', async () => {
    createDiagnosis.mockResolvedValue(detail)
    const store = useDiagnosisStore()

    await store.create({
      resume_id: 'resume-1',
      resume_version_no: 1,
      jd_id: 'jd-1',
    })

    expect(store.current?.total_score).toBe(71.75)
    expect(store.history[0].id).toBe('diag-1')
    expect(store.creating).toBe(false)
  })

  it('选择历史诊断加载详情', async () => {
    fetchDiagnosis.mockResolvedValue(detail)
    const store = useDiagnosisStore()

    await store.select('diag-1')

    expect(store.current?.jd_title).toBe('后端开发工程师')
  })

  it('诊断失败时记录错误并抛出', async () => {
    createDiagnosis.mockRejectedValue(new Error('DeepSeek API Key 未配置'))
    const store = useDiagnosisStore()

    await expect(
      store.create({ resume_id: 'resume-1', resume_version_no: 1, jd_id: 'jd-1' }),
    ).rejects.toThrow('API Key')

    expect(store.error).toBe('DeepSeek API Key 未配置')
    expect(store.creating).toBe(false)
  })
})
