import { http } from '@/api/http'
import type {
  ParsedResume,
  ResumeVersionDetail,
  ResumeVersionSummary,
} from '@/types/resumeVersion'

export async function parseResume(resumeId: string): Promise<ResumeVersionDetail> {
  const { data } = await http.post<ResumeVersionDetail>(`/resumes/${resumeId}/parse`)
  return data
}

export async function fetchResumeVersions(resumeId: string): Promise<ResumeVersionSummary[]> {
  const { data } = await http.get<ResumeVersionSummary[]>(`/resumes/${resumeId}/versions`)
  return data
}

export async function fetchResumeVersion(
  resumeId: string,
  versionNo: number,
): Promise<ResumeVersionDetail> {
  const { data } = await http.get<ResumeVersionDetail>(
    `/resumes/${resumeId}/versions/${versionNo}`,
  )
  return data
}

export async function saveResumeCorrection(
  resumeId: string,
  versionNo: number,
  data: ParsedResume,
): Promise<ResumeVersionDetail> {
  const response = await http.post<ResumeVersionDetail>(
    `/resumes/${resumeId}/versions/${versionNo}/corrections`,
    { data },
  )
  return response.data
}
