import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { InterviewDetail, InterviewSummary } from '@/types/interview'

const {
  createInterview,
  fetchInterview,
  fetchInterviews,
  finishInterview,
  generateInterviewReport,
  submitAnswer,
} = vi.hoisted(() => ({
  createInterview: vi.fn(),
  fetchInterview: vi.fn(),
  fetchInterviews: vi.fn(),
  finishInterview: vi.fn(),
  generateInterviewReport: vi.fn(),
  submitAnswer: vi.fn(),
}))

vi.mock('@/api/interviews', () => ({
  createInterview,
  fetchInterview,
  fetchInterviews,
  finishInterview,
  generateInterviewReport,
  submitAnswer,
}))

import { useInterviewStore } from '@/stores/interviews'

const summary: InterviewSummary = {
  id: 'interview-1',
  resume_id: 'resume-1',
  resume_filename: 'resume.pdf',
  resume_version_no: 1,
  jd_id: 'jd-1',
  jd_title: '后端开发工程师',
  interview_type: 'mixed',
  status: 'ready',
  planned_question_count: 3,
  question_count: 3,
  answered_count: 0,
  total_score: null,
  rubric_version: 'interview_rubric_v1',
  created_at: '2026-11-15T00:00:00Z',
  completed_at: null,
}

const detail: InterviewDetail = {
  ...summary,
  questions: [
    {
      id: 'question-1',
      order_index: 1,
      source: 'resume',
      source_ref: '某科技公司',
      question: '请介绍你在某科技公司的后端项目。',
      intent: '验证项目深度',
      follow_up_level: 0,
      parent_question_id: null,
      answer: null,
      answered_at: null,
      evaluation: null,
      score: null,
    },
    {
      id: 'question-2',
      order_index: 2,
      source: 'jd',
      source_ref: 'Docker',
      question: '你如何设计镜像与部署流程？',
      intent: '验证容器化实践',
      follow_up_level: 0,
      parent_question_id: null,
      answer: null,
      answered_at: null,
      evaluation: null,
      score: null,
    },
  ],
  current_question_id: 'question-1',
  dimension_scores: {},
  report: null,
  summary: null,
  model_name: 'fake-model',
  prompt_version: 'interview_plan_v1',
}

const answered: InterviewDetail = {
  ...detail,
  status: 'in_progress',
  answered_count: 1,
  current_question_id: 'question-2',
  questions: [
    {
      ...detail.questions[0],
      answer: '我负责后端接口设计。',
      answered_at: '2026-11-15T00:10:00Z',
      score: 74,
      evaluation: {
        dimensions: [
          { key: 'relevance', label: '相关性', score: 80, comment: '正面回答' },
          { key: 'correctness', label: '专业正确性', score: 70, comment: '基本正确' },
          { key: 'structure', label: '结构', score: 75, comment: '结构清晰' },
          { key: 'evidence', label: '证据', score: 60, comment: '缺少数据' },
          { key: 'expression', label: '表达', score: 85, comment: '表达流畅' },
        ],
        overall_score: 74,
        summary: '回答完整。',
        strengths: ['职责清晰'],
        weaknesses: ['缺少指标'],
      },
    },
    detail.questions[1],
  ],
}

const completed: InterviewDetail = {
  ...answered,
  status: 'completed',
  answered_count: 2,
  total_score: 74,
  current_question_id: null,
  completed_at: '2026-11-15T00:20:00Z',
  dimension_scores: { relevance: 80, correctness: 70, structure: 75, evidence: 60, expression: 85 },
}

const withReport: InterviewDetail = {
  ...completed,
  report: {
    overview: '整体不错。',
    strengths: ['表达清晰'],
    weaknesses: ['缺少数据'],
    improvements: ['准备量化结果'],
    question_notes: [{ order_index: 1, question: '第一题', comment: '结构清晰' }],
  },
  prompt_version: 'interview_report_v1',
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('interview store', () => {
  it('加载面试历史', async () => {
    fetchInterviews.mockResolvedValue([summary])
    const store = useInterviewStore()

    await store.load('resume-1')

    expect(fetchInterviews).toHaveBeenCalledWith('resume-1')
    expect(store.items).toHaveLength(1)
    expect(store.items[0].status).toBe('ready')
  })

  it('创建面试后写入列表并选中详情', async () => {
    createInterview.mockResolvedValue(detail)
    const store = useInterviewStore()

    const created = await store.create({
      resume_id: 'resume-1',
      resume_version_no: 1,
      jd_id: 'jd-1',
      interview_type: 'mixed',
      question_count: 3,
    })

    expect(created.id).toBe('interview-1')
    expect(store.current?.current_question_id).toBe('question-1')
    expect(store.items).toHaveLength(1)
    expect(store.creating).toBe(false)
  })

  it('提交回答后同步当前详情与列表进度', async () => {
    submitAnswer.mockResolvedValue(answered)
    const store = useInterviewStore()
    store.current = detail
    store.items = [summary]

    await store.answer('interview-1', 'question-1', '我负责后端接口设计。')

    expect(submitAnswer).toHaveBeenCalledWith(
      'interview-1',
      'question-1',
      '我负责后端接口设计。',
    )
    expect(store.current?.answered_count).toBe(1)
    expect(store.items[0].answered_count).toBe(1)
    expect(store.items[0].status).toBe('in_progress')
    expect(store.answering).toBe(false)
  })

  it('结束面试并生成报告', async () => {
    finishInterview.mockResolvedValue(completed)
    generateInterviewReport.mockResolvedValue(withReport)
    const store = useInterviewStore()
    store.current = answered
    store.items = [summary]

    await store.finish('interview-1')
    expect(store.current?.status).toBe('completed')
    expect(store.items[0].total_score).toBe(74)

    await store.report('interview-1', false)
    expect(generateInterviewReport).toHaveBeenCalledWith('interview-1', false)
    expect(store.current?.report?.overview).toBe('整体不错。')
    expect(store.reporting).toBe(false)
  })

  it('接口失败时记录错误并抛出', async () => {
    fetchInterview.mockRejectedValue(new Error('面试记录不存在'))
    const store = useInterviewStore()

    await expect(store.select('missing')).rejects.toThrow('面试记录不存在')
    expect(store.error).toBe('面试记录不存在')
    expect(store.loading).toBe(false)
  })
})
