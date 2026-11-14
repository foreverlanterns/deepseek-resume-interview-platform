import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  ParsedResume,
  ResumeVersionDetail,
  ResumeVersionSummary,
} from '@/types/resumeVersion'

const { fetchResumeVersion, fetchResumeVersions, parseResume, saveResumeCorrection } = vi.hoisted(
  () => ({
    fetchResumeVersion: vi.fn(),
    fetchResumeVersions: vi.fn(),
    parseResume: vi.fn(),
    saveResumeCorrection: vi.fn(),
  }),
)

vi.mock('@/api/resumeVersions', () => ({
  fetchResumeVersion,
  fetchResumeVersions,
  parseResume,
  saveResumeCorrection,
}))

import { useResumeVersionStore } from '@/stores/resumeVersions'

const parsed: ParsedResume = {
  basic_info: {
    name: '张三',
    phone: null,
    email: 'zhang@example.com',
    location: null,
    headline: null,
    source_text: null,
  },
  summary: null,
  education: [],
  work_experience: [],
  projects: [],
  skills: [],
  certificates: [],
  awards: [],
  languages: [],
}

const summary: ResumeVersionSummary = {
  version_no: 1,
  status: 'parsed',
  model_name: 'deepseek-flash',
  prompt_version: 'resume_parse_prompt_v1',
  parser_version: 'resume_parser_v1',
  base_version_no: null,
  has_corrections: false,
  created_at: '2026-11-14T14:00:00Z',
}

const detail: ResumeVersionDetail = {
  ...summary,
  parsed_data: parsed,
  corrected_data: null,
  effective_data: parsed,
  error_message: null,
}

const correctedDetail: ResumeVersionDetail = {
  ...summary,
  version_no: 2,
  status: 'corrected',
  base_version_no: 1,
  has_corrections: true,
  parsed_data: parsed,
  corrected_data: { ...parsed, summary: '校正后的摘要' },
  effective_data: { ...parsed, summary: '校正后的摘要' },
  error_message: null,
}

describe('useResumeVersionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('加载版本列表并选中版本', async () => {
    fetchResumeVersions.mockResolvedValue([summary])
    fetchResumeVersion.mockResolvedValue(detail)
    const store = useResumeVersionStore()

    await store.loadVersions('resume-1')
    await store.selectVersion('resume-1', 1)

    expect(store.versions).toEqual([summary])
    expect(store.current?.effective_data?.basic_info.name).toBe('张三')
    expect(store.loading).toBe(false)
  })

  it('解析成功后把新版本放到列表首位', async () => {
    fetchResumeVersions.mockResolvedValue([summary])
    parseResume.mockResolvedValue({ ...detail, version_no: 2 })
    const store = useResumeVersionStore()
    await store.loadVersions('resume-1')

    await store.parse('resume-1')

    expect(store.versions.map((item) => item.version_no)).toEqual([2, 1])
    expect(store.current?.version_no).toBe(2)
    expect(store.parsing).toBe(false)
  })

  it('保存校正后生成新版本', async () => {
    fetchResumeVersions.mockResolvedValue([summary])
    saveResumeCorrection.mockResolvedValue(correctedDetail)
    const store = useResumeVersionStore()
    await store.loadVersions('resume-1')

    await store.saveCorrection('resume-1', 1, parsed)

    expect(saveResumeCorrection).toHaveBeenCalledWith('resume-1', 1, parsed)
    expect(store.versions[0].version_no).toBe(2)
    expect(store.current?.effective_data?.summary).toBe('校正后的摘要')
    expect(store.saving).toBe(false)
  })

  it('解析失败时保留可读错误并抛出', async () => {
    parseResume.mockRejectedValue(new Error('DeepSeek API Key 未配置'))
    const store = useResumeVersionStore()

    await expect(store.parse('resume-1')).rejects.toThrow('DeepSeek API Key 未配置')

    expect(store.error).toBe('DeepSeek API Key 未配置')
    expect(store.current).toBeNull()
    expect(store.parsing).toBe(false)
  })

  it('重置后清空版本与当前选择', async () => {
    fetchResumeVersions.mockResolvedValue([summary])
    fetchResumeVersion.mockResolvedValue(detail)
    const store = useResumeVersionStore()
    await store.loadVersions('resume-1')
    await store.selectVersion('resume-1', 1)

    store.reset()

    expect(store.versions).toEqual([])
    expect(store.current).toBeNull()
  })
})
