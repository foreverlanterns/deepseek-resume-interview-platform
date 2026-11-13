import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { User } from '@/types/auth'

const { fetchMe, loginRequest, registerRequest } = vi.hoisted(() => ({
  fetchMe: vi.fn(),
  loginRequest: vi.fn(),
  registerRequest: vi.fn(),
}))

const { getToken, setToken, clearToken, setUnauthorizedHandler, unauthorizedRef } = vi.hoisted(
  () => {
    const unauthorizedRef: { current: (() => void) | null } = { current: null }
    return {
      getToken: vi.fn(),
      setToken: vi.fn(),
      clearToken: vi.fn(),
      setUnauthorizedHandler: vi.fn((handler: (() => void) | null) => {
        unauthorizedRef.current = handler
      }),
      unauthorizedRef,
    }
  },
)

vi.mock('@/api/auth', () => ({
  fetchMe,
  login: loginRequest,
  register: registerRequest,
}))

vi.mock('@/utils/token', () => ({
  getToken,
  setToken,
  clearToken,
  setUnauthorizedHandler,
}))

import { useAuthStore } from '@/stores/auth'

const user: User = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'student@example.com',
  display_name: '小明',
  is_active: true,
  created_at: '2026-11-13T19:00:00Z',
}

const tokenResponse = {
  access_token: 'token-123',
  token_type: 'bearer' as const,
  expires_in: 3600,
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    getToken.mockReturnValue(null)
  })

  it('登录后保存 token 并加载当前用户', async () => {
    loginRequest.mockResolvedValue(tokenResponse)
    fetchMe.mockResolvedValue(user)
    const store = useAuthStore()

    await store.login({ email: 'student@example.com', password: 'StrongPass123' })

    expect(loginRequest).toHaveBeenCalledWith({
      email: 'student@example.com',
      password: 'StrongPass123',
    })
    expect(setToken).toHaveBeenCalledWith('token-123')
    expect(store.isAuthenticated).toBe(true)
    expect(store.displayName).toBe('小明')
  })

  it('登录失败时清空会话并抛出可读错误', async () => {
    loginRequest.mockRejectedValue(new Error('邮箱或密码错误'))
    const store = useAuthStore()

    await expect(
      store.login({ email: 'student@example.com', password: 'wrong-password' }),
    ).rejects.toThrow('邮箱或密码错误')

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(clearToken).toHaveBeenCalled()
  })

  it('注册成功后自动登录', async () => {
    registerRequest.mockResolvedValue(user)
    loginRequest.mockResolvedValue(tokenResponse)
    fetchMe.mockResolvedValue(user)
    const store = useAuthStore()

    await store.register({
      email: 'student@example.com',
      password: 'StrongPass123',
      display_name: '小明',
    })

    expect(registerRequest).toHaveBeenCalledWith({
      email: 'student@example.com',
      password: 'StrongPass123',
      display_name: '小明',
    })
    expect(loginRequest).toHaveBeenCalledWith({
      email: 'student@example.com',
      password: 'StrongPass123',
    })
    expect(store.isAuthenticated).toBe(true)
  })

  it('本地有 token 时恢复用户会话', async () => {
    getToken.mockReturnValue('stored-token')
    fetchMe.mockResolvedValue(user)
    const store = useAuthStore()

    expect(store.isAuthenticated).toBe(false)
    await store.restore()

    expect(fetchMe).toHaveBeenCalledTimes(1)
    expect(store.user).toEqual(user)
    expect(store.isAuthenticated).toBe(true)
  })

  it('恢复会话失败时清除失效 token', async () => {
    getToken.mockReturnValue('expired-token')
    fetchMe.mockRejectedValue(new Error('登录已过期'))
    const store = useAuthStore()

    await store.restore()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(clearToken).toHaveBeenCalled()
  })

  it('退出登录清空用户与 token', async () => {
    loginRequest.mockResolvedValue(tokenResponse)
    fetchMe.mockResolvedValue(user)
    const store = useAuthStore()
    await store.login({ email: 'student@example.com', password: 'StrongPass123' })

    store.logout()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(clearToken).toHaveBeenCalled()
  })

  it('收到全局 401 通知时立即清空登录状态', async () => {
    loginRequest.mockResolvedValue(tokenResponse)
    fetchMe.mockResolvedValue(user)
    const store = useAuthStore()
    await store.login({ email: 'student@example.com', password: 'StrongPass123' })
    expect(store.isAuthenticated).toBe(true)

    unauthorizedRef.current?.()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })
})
