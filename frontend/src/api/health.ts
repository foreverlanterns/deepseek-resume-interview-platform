import { http } from '@/api/http'
import type { HealthResponse } from '@/types/api'

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
  return data
}
