export type DatabaseStatus = 'ok' | 'unavailable'
export type ServiceStatus = 'ok' | 'degraded'

export interface HealthResponse {
  app: string
  version: string
  environment: string
  status: ServiceStatus
  database: DatabaseStatus
  database_error: string | null
  checked_at: string
}
