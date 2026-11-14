import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { JobDescription, JobDescriptionPayload } from '@/types/jd'

const { createJobDescription, deleteJobDescription, fetchJobDescriptions, updateJobDescription } =
  vi.hoisted(() => ({
    createJobDescription: vi.fn(),
    deleteJobDescription: vi.fn(),
    fetchJobDescriptions: vi.fn(),
    updateJobDescription: vi.fn(),
  }))

vi.mock('@/api/jds', () => ({
  createJobDescription,
  deleteJobDescription,
  fetchJobDescriptions,
  updateJobDescription,
}))

import { useJdStore } from '@/stores/jds'

const jd: JobDescription = {
  id: 'jd-1',
  title: '后端开发工程师',
  company: '某科技公司',
  raw_text: '负责后端开发',
  required_skills: ['Python'],
  preferred_skills: ['Docker'],
  keywords: ['PostgreSQL'],
  responsibilities: ['开发后端服务'],
  qualifications: ['本科及以上'],
  created_at: '2026-11-15T00:00:00Z',
  updated_at: '2026-11-15T00:00:00Z',
}

const payload: JobDescriptionPayload = {
  title: jd.title,
  company: jd.company,
  raw_text: jd.raw_text,
  required_skills: jd.required_skills,
  preferred_skills: jd.preferred_skills,
  keywords: jd.keywords,
  responsibilities: jd.responsibilities,
  qualifications: jd.qualifications,
}

describe('useJdStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('加载岗位列表', async () => {
    fetchJobDescriptions.mockResolvedValue([jd])
    const store = useJdStore()

    await store.load(true)

    expect(store.items).toEqual([jd])
    expect(store.loading).toBe(false)
  })

  it('创建后插入列表首位', async () => {
    createJobDescription.mockResolvedValue(jd)
    const store = useJdStore()

    await store.create(payload)

    expect(createJobDescription).toHaveBeenCalledWith(payload)
    expect(store.items[0].id).toBe('jd-1')
  })

  it('更新后替换对应项', async () => {
    fetchJobDescriptions.mockResolvedValue([jd])
    updateJobDescription.mockResolvedValue({ ...jd, title: '高级后端开发工程师' })
    const store = useJdStore()
    await store.load(true)

    await store.update('jd-1', { ...payload, title: '高级后端开发工程师' })

    expect(store.items[0].title).toBe('高级后端开发工程师')
  })

  it('删除后从列表移除', async () => {
    fetchJobDescriptions.mockResolvedValue([jd])
    deleteJobDescription.mockResolvedValue(undefined)
    const store = useJdStore()
    await store.load(true)

    await store.remove('jd-1')

    expect(store.items).toEqual([])
  })

  it('保存失败时记录错误并抛出', async () => {
    createJobDescription.mockRejectedValue(new Error('至少填写一项岗位要求'))
    const store = useJdStore()

    await expect(store.create(payload)).rejects.toThrow('至少填写一项岗位要求')

    expect(store.error).toBe('至少填写一项岗位要求')
    expect(store.saving).toBe(false)
  })
})
