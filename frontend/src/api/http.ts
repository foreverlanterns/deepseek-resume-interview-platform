import axios, { type AxiosInstance } from 'axios'

import { getToken, notifyUnauthorized } from '@/utils/token'

/** 模型类接口的等待上限，略低于 Nginx 的 180 秒。 */
export const LONG_REQUEST_TIMEOUT_MS = 170_000

/** 文件上传允许更长的传输时间。 */
export const UPLOAD_REQUEST_TIMEOUT_MS = 120_000

export interface ApiErrorOptions {
  status?: number | null
  code?: string
  details?: unknown
}

/** 前端统一错误类型：页面只需要读取 message 与 status。 */
export class ApiError extends Error {
  readonly status: number | null
  readonly code: string
  readonly details: unknown

  constructor(message: string, options: ApiErrorOptions = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status ?? null
    this.code = options.code ?? 'unknown_error'
    this.details = options.details
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** 兼容 FastAPI 的 detail 字符串与 422 校验错误数组。 */
export function extractErrorMessage(data: unknown, fallback = '请求失败，请稍后重试'): string {
  if (typeof data === 'string' && data.trim()) {
    return data
  }
  if (isRecord(data)) {
    const detail = data.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!isRecord(item)) {
            return ''
          }
          const location = Array.isArray(item.loc) ? item.loc.join('.') : ''
          const message = typeof item.msg === 'string' ? item.msg : ''
          return location && message ? `${location}: ${message}` : message
        })
        .filter((message) => message.length > 0)
      if (messages.length > 0) {
        return messages.join('；')
      }
    }
    if (typeof data.message === 'string' && data.message.trim()) {
      return data.message
    }
  }
  return fallback
}

/** 把 axios 异常归一为 ApiError，避免页面各写一套判断。 */
export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return new ApiError('请求超时，请稍后重试', { code: 'timeout' })
      }
      return new ApiError('无法连接服务器，请确认后端服务已启动', { code: 'network_error' })
    }
    const { status, data } = error.response
    return new ApiError(extractErrorMessage(data, `请求失败（HTTP ${status}）`), {
      status,
      code: 'http_error',
      details: data,
    })
  }
  if (error instanceof Error) {
    return new ApiError(error.message || '未知错误', { code: 'client_error' })
  }
  return new ApiError('未知错误', { code: 'unknown_error' })
}

export function createHttpClient(
  baseURL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30_000,
  })

  instance.interceptors.request.use((config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        notifyUnauthorized()
      }
      return Promise.reject(normalizeApiError(error))
    },
  )

  return instance
}

export const http = createHttpClient()
