export type InterviewType = 'mixed' | 'resume' | 'jd' | 'behavioral'
export type InterviewStatus = 'ready' | 'in_progress' | 'completed'
export type QuestionSource = 'resume' | 'jd' | 'behavioral'
export type EvaluationKey =
  | 'relevance'
  | 'correctness'
  | 'structure'
  | 'evidence'
  | 'expression'

export interface EvaluationDimension {
  key: EvaluationKey
  label: string
  score: number
  comment: string
}

export interface AnswerEvaluation {
  dimensions: EvaluationDimension[]
  overall_score: number
  summary: string
  strengths: string[]
  weaknesses: string[]
}

export interface InterviewQuestion {
  id: string
  order_index: number
  source: QuestionSource
  source_ref: string
  question: string
  intent: string
  follow_up_level: number
  parent_question_id: string | null
  answer: string | null
  answered_at: string | null
  evaluation: AnswerEvaluation | null
  score: number | null
}

export interface ReportQuestionNote {
  order_index: number
  question: string
  comment: string
}

export interface InterviewReport {
  overview: string
  strengths: string[]
  weaknesses: string[]
  improvements: string[]
  question_notes: ReportQuestionNote[]
}

export interface InterviewSummary {
  id: string
  resume_id: string
  resume_filename: string
  resume_version_no: number
  jd_id: string | null
  jd_title: string | null
  interview_type: InterviewType
  status: InterviewStatus
  planned_question_count: number
  question_count: number
  answered_count: number
  total_score: number | null
  rubric_version: string
  created_at: string
  completed_at: string | null
}

export interface InterviewDetail extends InterviewSummary {
  questions: InterviewQuestion[]
  current_question_id: string | null
  dimension_scores: Record<string, number>
  report: InterviewReport | null
  summary: string | null
  model_name: string | null
  prompt_version: string | null
}

export interface InterviewCreatePayload {
  resume_id: string
  resume_version_no: number
  jd_id?: string | null
  interview_type: InterviewType
  question_count: number
}
