import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ResumeDetail, ResumeSummary } from '@/types/resume'

const { fetchResumes, uploadResume, deleteResume } = vi.hoisted(() => ({
  fetchResumes: vi.fn(),
  uploadResume: vi.fn(),
  deleteResume: vi.fn(),
}))

vi.mock('@/api/resumes', () => ({
  fetchResumes,
  uploadResume,
  deleteResume,
}))

import { useResumeStore } from '@/stores/resumes'

const summary: ResumeSummary = {
  id: '11111111-1111-1111-1111-111111111111',
  original_filename: 'resume.pdf',
  status: 'extracted',
  text_length: 320,
  page_count: 1,
  created_at: '2026-11-14T04:00:00Z',
}

const detail: ResumeDetail = {
  ...summary,
  mime_type: 'application/pdf',
  file_size: 2048,
  sha256: 'a'.repeat(64),
  text_preview: 'Zhang San\nPython FastAPI',
  error_message: null,
}

const file = { name: 'resume.pdf', size: 2048 } as unknown as File

describe('useResumeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('加载当前用户的简历列表', async () => {
    fetchResumes.mockResolvedValue([summary])
    const store = useResumeStore()

    await store.load(true)

    expect(fetchResumes).toHaveBeenCalledTimes(1)
    expect(store.items).toEqual([summary])
    expect(store.initialized).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('上传成功后把新简历放到列表首位', async () => {
    uploadResume.mockResolvedValue(detail)
    const store = useResumeStore()
    store.items = [{ ...summary, id: 'older', original_filename: 'older.pdf' }]

    const result = await store.upload(file)

    expect(result).toEqual(detail)
    expect(store.items.map((item) => item.id)).toEqual([detail.id, 'older'])
    expect(store.uploading).toBe(false)
  })

  it('删除成功后从列表移除', async () => {
    fetchResumes.mockResolvedValue([summary])
    deleteResume.mockResolvedValue(undefined)
    const store = useResumeStore()
    await store.load(true)

    await store.remove(summary.id)

    expect(deleteResume).toHaveBeenCalledWith(summary.id)
    expect(store.items).toEqual([])
  })

  it('列表加载失败时保留可读错误', async () => {
    fetchResumes.mockRejectedValue(new Error('无法连接服务器'))
    const store = useResumeStore()

    await store.load(true)

    expect(store.items).toEqual([])
    expect(store.error).toBe('无法连接服务器')
    expect(store.loading).toBe(false)
  })

  it('上传失败时抛出错误并记录', async () => {
    uploadResume.mockRejectedValue(new Error('仅支持 PDF 和 DOCX 文件'))
    const store = useResumeStore()

    await expect(store.upload(file)).rejects.toThrow('仅支持 PDF 和 DOCX 文件')

    expect(store.error).toBe('仅支持 PDF 和 DOCX 文件')
    expect(store.uploading).toBe(false)
  })
})
