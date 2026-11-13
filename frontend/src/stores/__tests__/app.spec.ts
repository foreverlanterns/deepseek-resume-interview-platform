import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { HealthResponse } from '@/types/api'

const { fetchHealth } = vi.hoisted(() => ({ fetchHealth: vi.fn() }))

vi.mock('@/api/health', () => ({ fetchHealth }))

import { useAppStore } from '@/stores/app'

const healthFixture: HealthResponse = {
  app: '智能简历诊断与面试模拟平台',
  version: '0.1.0',
  environment: 'test',
  status: 'ok',
  database: 'ok',
  database_error: null,
  checked_at: '2026-11-13T15:00:00Z',
}

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchHealth.mockReset()
  })

  it('加载健康状态并判断数据库在线', async () => {
    fetchHealth.mockResolvedValue(healthFixture)
    const store = useAppStore()

    await store.checkHealth()

    expect(fetchHealth).toHaveBeenCalledTimes(1)
    expect(store.health?.database).toBe('ok')
    expect(store.databaseOnline).toBe(true)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('连接失败时保留可读错误且不抛出', async () => {
    fetchHealth.mockRejectedValue(new Error('无法连接服务器，请确认后端服务已启动'))
    const store = useAppStore()

    await expect(store.checkHealth()).resolves.toBeUndefined()

    expect(store.health).toBeNull()
    expect(store.error).toContain('无法连接服务器')
    expect(store.databaseOnline).toBe(false)
    expect(store.loading).toBe(false)
  })
})
