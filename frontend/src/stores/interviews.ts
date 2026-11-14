import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  createInterview,
  fetchInterview,
  fetchInterviews,
  finishInterview,
  generateInterviewReport,
  submitAnswer,
} from '@/api/interviews'
import type {
  InterviewCreatePayload,
  InterviewDetail,
  InterviewSummary,
} from '@/types/interview'

function toSummary(detail: InterviewDetail): InterviewSummary {
  return {
    id: detail.id,
    resume_id: detail.resume_id,
    resume_filename: detail.resume_filename,
    resume_version_no: detail.resume_version_no,
    jd_id: detail.jd_id,
    jd_title: detail.jd_title,
    interview_type: detail.interview_type,
    status: detail.status,
    planned_question_count: detail.planned_question_count,
    question_count: detail.question_count,
    answered_count: detail.answered_count,
    total_score: detail.total_score,
    rubric_version: detail.rubric_version,
    created_at: detail.created_at,
    completed_at: detail.completed_at,
  }
}

export const useInterviewStore = defineStore('interviews', () => {
  const items = ref<InterviewSummary[]>([])
  const current = ref<InterviewDetail | null>(null)
  const loading = ref(false)
  const creating = ref(false)
  const answering = ref(false)
  const finishing = ref(false)
  const reporting = ref(false)
  const error = ref<string | null>(null)

  function syncList(detail: InterviewDetail): void {
    const summary = toSummary(detail)
    const index = items.value.findIndex((item) => item.id === detail.id)
    if (index === -1) {
      items.value = [summary, ...items.value]
    } else {
      items.value.splice(index, 1, summary)
    }
  }

  async function load(resumeId?: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      items.value = await fetchInterviews(resumeId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '面试记录加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function create(payload: InterviewCreatePayload): Promise<InterviewDetail> {
    creating.value = true
    error.value = null
    try {
      const detail = await createInterview(payload)
      current.value = detail
      syncList(detail)
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '面试创建失败'
      throw caught
    } finally {
      creating.value = false
    }
  }

  async function select(interviewId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      current.value = await fetchInterview(interviewId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '面试详情加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function answer(
    interviewId: string,
    questionId: string,
    text: string,
  ): Promise<InterviewDetail> {
    answering.value = true
    error.value = null
    try {
      const detail = await submitAnswer(interviewId, questionId, text)
      current.value = detail
      syncList(detail)
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '回答提交失败'
      throw caught
    } finally {
      answering.value = false
    }
  }

  async function finish(interviewId: string): Promise<InterviewDetail> {
    finishing.value = true
    error.value = null
    try {
      const detail = await finishInterview(interviewId)
      current.value = detail
      syncList(detail)
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '结束面试失败'
      throw caught
    } finally {
      finishing.value = false
    }
  }

  async function report(interviewId: string, force = false): Promise<InterviewDetail> {
    reporting.value = true
    error.value = null
    try {
      const detail = await generateInterviewReport(interviewId, force)
      current.value = detail
      syncList(detail)
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '报告生成失败'
      throw caught
    } finally {
      reporting.value = false
    }
  }

  function reset(): void {
    items.value = []
    current.value = null
    error.value = null
  }

  return {
    items,
    current,
    loading,
    creating,
    answering,
    finishing,
    reporting,
    error,
    load,
    create,
    select,
    answer,
    finish,
    report,
    reset,
  }
})
