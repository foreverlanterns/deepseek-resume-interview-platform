import { http, LONG_REQUEST_TIMEOUT_MS } from '@/api/http'
import type {
  DiagnosisCreatePayload,
  DiagnosisDetail,
  DiagnosisSummary,
} from '@/types/diagnosis'

export async function createDiagnosis(
  payload: DiagnosisCreatePayload,
): Promise<DiagnosisDetail> {
  const { data } = await http.post<DiagnosisDetail>('/diagnoses', payload, {
    timeout: LONG_REQUEST_TIMEOUT_MS,
  })
  return data
}

export async function fetchDiagnoses(params?: {
  resume_id?: string
  jd_id?: string
}): Promise<DiagnosisSummary[]> {
  const { data } = await http.get<DiagnosisSummary[]>('/diagnoses', { params })
  return data
}

export async function fetchDiagnosis(diagnosisId: string): Promise<DiagnosisDetail> {
  const { data } = await http.get<DiagnosisDetail>(`/diagnoses/${diagnosisId}`)
  return data
}
