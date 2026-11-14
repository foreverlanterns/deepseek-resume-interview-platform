import { http } from '@/api/http'
import type { JobDescription, JobDescriptionPayload } from '@/types/jd'

export async function fetchJobDescriptions(): Promise<JobDescription[]> {
  const { data } = await http.get<JobDescription[]>('/jds')
  return data
}

export async function createJobDescription(
  payload: JobDescriptionPayload,
): Promise<JobDescription> {
  const { data } = await http.post<JobDescription>('/jds', payload)
  return data
}

export async function updateJobDescription(
  jdId: string,
  payload: JobDescriptionPayload,
): Promise<JobDescription> {
  const { data } = await http.put<JobDescription>(`/jds/${jdId}`, payload)
  return data
}

export async function deleteJobDescription(jdId: string): Promise<void> {
  await http.delete(`/jds/${jdId}`)
}
