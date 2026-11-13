import { http } from '@/api/http'
import type { ResumeDetail, ResumeSummary } from '@/types/resume'

export async function fetchResumes(): Promise<ResumeSummary[]> {
  const { data } = await http.get<ResumeSummary[]>('/resumes')
  return data
}

export async function uploadResume(file: File): Promise<ResumeDetail> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await http.post<ResumeDetail>('/resumes/upload', formData)
  return data
}

export async function fetchResume(resumeId: string): Promise<ResumeDetail> {
  const { data } = await http.get<ResumeDetail>(`/resumes/${resumeId}`)
  return data
}

export async function deleteResume(resumeId: string): Promise<void> {
  await http.delete(`/resumes/${resumeId}`)
}
