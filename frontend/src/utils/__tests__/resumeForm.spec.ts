import { describe, expect, it } from 'vitest'

import type { ParsedResume } from '@/types/resumeVersion'
import {
  createEmptyParsedResumeForm,
  toParsedResumeForm,
  toParsedResumePayload,
} from '@/utils/resumeForm'

const parsed: ParsedResume = {
  basic_info: {
    name: '张三',
    phone: null,
    email: 'zhang@example.com',
    location: null,
    headline: null,
    source_text: '张三 zhang@example.com',
  },
  summary: null,
  education: [
    {
      school: '某某大学',
      degree: '本科',
      major: null,
      start_date: '2020.09',
      end_date: null,
      details: ['主修数据库'],
      source_text: null,
    },
  ],
  work_experience: [],
  projects: [],
  skills: [{ category: '编程语言', items: ['Python', 'FastAPI'], source_text: null }],
  certificates: [],
  awards: [],
  languages: [{ name: '英语', level: 'CET-6' }],
}

describe('resumeForm', () => {
  it('把 null 转为空字符串，保留列表', () => {
    const form = toParsedResumeForm(parsed)

    expect(form.basic_info.phone).toBe('')
    expect(form.summary).toBe('')
    expect(form.education[0].degree).toBe('本科')
    expect(form.skills[0].items).toEqual(['Python', 'FastAPI'])
  })

  it('保存时把空字符串转为 null 并清理空行', () => {
    const form = toParsedResumeForm(parsed)
    form.basic_info.phone = '  '
    form.education[0].details = ['  主修数据库  ', '  ', '']
    form.skills[0].items = ['Python', ' ']

    const payload = toParsedResumePayload(form)

    expect(payload.basic_info.phone).toBeNull()
    expect(payload.education[0].details).toEqual(['主修数据库'])
    expect(payload.skills[0].items).toEqual(['Python'])
  })

  it('空表单结构完整', () => {
    const form = createEmptyParsedResumeForm()

    expect(form.basic_info.name).toBe('')
    expect(form.education).toEqual([])
    expect(form.languages).toEqual([])
  })
})
