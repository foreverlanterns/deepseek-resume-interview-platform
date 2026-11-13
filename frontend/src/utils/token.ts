const TOKEN_KEY = 'resume_platform_access_token'

let unauthorizedHandler: (() => void) | null = null

function getStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function getToken(): string | null {
  return getStorage()?.getItem(TOKEN_KEY) ?? null
}

export function setToken(token: string): void {
  getStorage()?.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  getStorage()?.removeItem(TOKEN_KEY)
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

/** 401 时清除本地凭证并通知认证 store，避免页面仍显示已登录。 */
export function notifyUnauthorized(): void {
  clearToken()
  unauthorizedHandler?.()
}
