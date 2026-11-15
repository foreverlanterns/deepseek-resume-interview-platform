import { http } from '@/api/http'
import type {
  AnalyticsOverview,
  DiagnosisTrendResponse,
  InterviewTrendResponse,
  WeaknessReport,
} from '@/types/analytics'

export async function fetchAnalyticsOverview(
  resumeId?: string,
): Promise<AnalyticsOverview> {
  const { data } = await http.get<AnalyticsOverview>('/analytics/overview', {
    params: resumeId ? { resume_id: resumeId } : undefined,
  })
  return data
}

export async function fetchDiagnosisTrends(params?: {
  resumeId?: string
  jdId?: string
}): Promise<DiagnosisTrendResponse> {
  const { data } = await http.get<DiagnosisTrendResponse>('/analytics/diagnoses', {
    params: {
      ...(params?.resumeId ? { resume_id: params.resumeId } : {}),
      ...(params?.jdId ? { jd_id: params.jdId } : {}),
    },
  })
  return data
}

export async function fetchInterviewTrends(params?: {
  resumeId?: string
  jdId?: string
  interviewType?: string
}): Promise<InterviewTrendResponse> {
  const { data } = await http.get<InterviewTrendResponse>('/analytics/interviews', {
    params: {
      ...(params?.resumeId ? { resume_id: params.resumeId } : {}),
      ...(params?.jdId ? { jd_id: params.jdId } : {}),
      ...(params?.interviewType ? { interview_type: params.interviewType } : {}),
    },
  })
  return data
}

export async function fetchWeaknesses(resumeId?: string): Promise<WeaknessReport> {
  const { data } = await http.get<WeaknessReport>('/analytics/weaknesses', {
    params: resumeId ? { resume_id: resumeId } : undefined,
  })
  return data
}
