import { http } from '@/api/http'
import type {
  InterviewCreatePayload,
  InterviewDetail,
  InterviewSummary,
} from '@/types/interview'

export async function fetchInterviews(resumeId?: string): Promise<InterviewSummary[]> {
  const { data } = await http.get<InterviewSummary[]>('/interviews', {
    params: resumeId ? { resume_id: resumeId } : undefined,
  })
  return data
}

export async function createInterview(
  payload: InterviewCreatePayload,
): Promise<InterviewDetail> {
  const { data } = await http.post<InterviewDetail>('/interviews', payload)
  return data
}

export async function fetchInterview(interviewId: string): Promise<InterviewDetail> {
  const { data } = await http.get<InterviewDetail>(`/interviews/${interviewId}`)
  return data
}

export async function submitAnswer(
  interviewId: string,
  questionId: string,
  answer: string,
): Promise<InterviewDetail> {
  const { data } = await http.post<InterviewDetail>(
    `/interviews/${interviewId}/questions/${questionId}/answer`,
    { answer },
  )
  return data
}

export async function finishInterview(interviewId: string): Promise<InterviewDetail> {
  const { data } = await http.post<InterviewDetail>(`/interviews/${interviewId}/finish`)
  return data
}

export async function generateInterviewReport(
  interviewId: string,
  force = false,
): Promise<InterviewDetail> {
  const { data } = await http.post<InterviewDetail>(
    `/interviews/${interviewId}/report`,
    undefined,
    { params: force ? { force: true } : undefined },
  )
  return data
}
