import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  AnalyticsOverview,
  DiagnosisTrendResponse,
  InterviewTrendResponse,
  WeaknessReport,
} from '@/types/analytics'

const {
  fetchAnalyticsOverview,
  fetchDiagnosisTrends,
  fetchInterviewTrends,
  fetchWeaknesses,
} = vi.hoisted(() => ({
  fetchAnalyticsOverview: vi.fn(),
  fetchDiagnosisTrends: vi.fn(),
  fetchInterviewTrends: vi.fn(),
  fetchWeaknesses: vi.fn(),
}))

vi.mock('@/api/analytics', () => ({
  fetchAnalyticsOverview,
  fetchDiagnosisTrends,
  fetchInterviewTrends,
  fetchWeaknesses,
}))

import { useAnalyticsStore } from '@/stores/analytics'

const overview: AnalyticsOverview = {
  resume_count: 1,
  diagnosis_count: 2,
  interview_count: 2,
  completed_interview_count: 1,
  latest_diagnosis: {
    id: 'diag-2',
    total_score: 72,
    created_at: '2026-11-05T00:00:00Z',
    resume_filename: 'resume.pdf',
    jd_title: '后端开发工程师',
  },
  latest_interview: null,
}

const diagnosisData: DiagnosisTrendResponse = {
  groups: [
    {
      resume_id: 'resume-1',
      resume_filename: 'resume.pdf',
      jd_id: 'jd-1',
      jd_title: '后端开发工程师',
      rubric_version: 'rubric_v1',
      points: [
        {
          id: 'diag-1',
          created_at: '2026-11-01T00:00:00Z',
          resume_version_no: 1,
          total_score: 60,
          format_score: 80,
          completeness_score: 80,
          keyword_score: 60,
          jd_match_score: 50,
        },
        {
          id: 'diag-2',
          created_at: '2026-11-05T00:00:00Z',
          resume_version_no: 2,
          total_score: 72,
          format_score: 80,
          completeness_score: 80,
          keyword_score: 70,
          jd_match_score: 65,
        },
      ],
      average_total: 66,
      best_total: 72,
      improvement: 12,
    },
  ],
}

const interviewData: InterviewTrendResponse = {
  groups: [
    {
      resume_id: 'resume-1',
      resume_filename: 'resume.pdf',
      jd_id: 'jd-1',
      jd_title: '后端开发工程师',
      interview_type: 'mixed',
      rubric_version: 'interview_rubric_v1',
      points: [
        {
          id: 'interview-1',
          created_at: '2026-11-06T00:00:00Z',
          resume_version_no: 2,
          total_score: 74,
          question_count: 3,
          answered_count: 3,
          dimension_scores: { relevance: 80, evidence: 60 },
        },
      ],
      average_total: 74,
      best_total: 74,
      improvement: 0,
      dimension_changes: {},
    },
  ],
}

const weaknesses: WeaknessReport = {
  missing_keywords: [{ keyword: 'Docker', count: 2 }],
  missing_requirements: [{ requirement: 'Docker', count: 2 }],
  interview_dimensions: [
    { key: 'relevance', label: '相关性', average: 80, sample_count: 1 },
    { key: 'evidence', label: '证据', average: 60, sample_count: 1 },
  ],
  lowest_dimension: 'evidence',
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('analytics store', () => {
  it('并行加载概览、趋势与弱项', async () => {
    fetchAnalyticsOverview.mockResolvedValue(overview)
    fetchDiagnosisTrends.mockResolvedValue(diagnosisData)
    fetchInterviewTrends.mockResolvedValue(interviewData)
    fetchWeaknesses.mockResolvedValue(weaknesses)
    const store = useAnalyticsStore()

    await store.load('resume-1')

    expect(fetchAnalyticsOverview).toHaveBeenCalledWith('resume-1')
    expect(fetchDiagnosisTrends).toHaveBeenCalledWith({ resumeId: 'resume-1' })
    expect(fetchInterviewTrends).toHaveBeenCalledWith({ resumeId: 'resume-1' })
    expect(fetchWeaknesses).toHaveBeenCalledWith('resume-1')
    expect(store.overview?.diagnosis_count).toBe(2)
    expect(store.diagnosisGroups[0].improvement).toBe(12)
    expect(store.interviewGroups[0].points[0].total_score).toBe(74)
    expect(store.weaknesses?.lowest_dimension).toBe('evidence')
    expect(store.loading).toBe(false)
  })

  it('加载失败时记录错误并抛出', async () => {
    fetchAnalyticsOverview.mockRejectedValue(new Error('统计服务不可用'))
    fetchDiagnosisTrends.mockResolvedValue({ groups: [] })
    fetchInterviewTrends.mockResolvedValue({ groups: [] })
    fetchWeaknesses.mockResolvedValue({
      missing_keywords: [],
      missing_requirements: [],
      interview_dimensions: [],
      lowest_dimension: null,
    })
    const store = useAnalyticsStore()

    await expect(store.load()).rejects.toThrow('统计服务不可用')
    expect(store.error).toBe('统计服务不可用')
    expect(store.loading).toBe(false)
  })
})
