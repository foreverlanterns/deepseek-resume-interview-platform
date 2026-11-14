export type DimensionKey = 'format' | 'completeness' | 'keyword' | 'jd_match'
export type CheckStatus = 'pass' | 'partial' | 'fail'
export type Verdict = 'met' | 'partial' | 'missing'
export type SuggestionStatus = 'supported' | 'needs_user_input' | 'needs_review'

export interface DimensionCheck {
  name: string
  label: string
  status: CheckStatus
  score: number
  max_score: number
  message: string
}

export interface KeywordHit {
  keyword: string
  source: 'required' | 'preferred' | 'keyword'
  weight: number
  matched: boolean
}

export interface KeywordReport {
  score: number
  matched_count: number
  total_count: number
  matched_weight: number
  total_weight: number
  hits: KeywordHit[]
}

export interface RequirementMatch {
  requirement: string
  source: 'required' | 'preferred'
  weight: number
  verdict: Verdict
  evidence: string | null
  reason: string
}

export interface JdMatchReport {
  score: number
  matched_count: number
  partial_count: number
  missing_count: number
  total: number
  matches: RequirementMatch[]
}

export interface Suggestion {
  dimension: DimensionKey
  original_text: string
  issue: string
  suggestion: string
  rewritten_example: string
  reason: string
  fact_status: SuggestionStatus
  missing_facts: string[]
  original_text_verified: boolean
}

export interface DiagnosisSummary {
  id: string
  resume_id: string
  resume_filename: string
  resume_version_no: number
  jd_id: string
  jd_title: string
  rubric_version: string
  total_score: number
  format_score: number
  completeness_score: number
  keyword_score: number
  jd_match_score: number
  created_at: string
}

export interface DiagnosisDetail extends DiagnosisSummary {
  weights: Record<string, number>
  format_details: DimensionCheck[]
  completeness_details: DimensionCheck[]
  keyword_details: KeywordReport
  jd_match_details: JdMatchReport
  suggestions: Suggestion[]
  summary: string
  model_name: string | null
  prompt_version: string | null
}

export interface DiagnosisCreatePayload {
  resume_id: string
  resume_version_no: number
  jd_id: string
}
