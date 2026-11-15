export interface LatestScore {
  id: string
  total_score: number
  created_at: string
  resume_filename: string
  jd_title: string | null
}

export interface AnalyticsOverview {
  resume_count: number
  diagnosis_count: number
  interview_count: number
  completed_interview_count: number
  latest_diagnosis: LatestScore | null
  latest_interview: LatestScore | null
}

export interface DiagnosisPoint {
  id: string
  created_at: string
  resume_version_no: number
  total_score: number
  format_score: number
  completeness_score: number
  keyword_score: number
  jd_match_score: number
}

export interface DiagnosisTrendGroup {
  resume_id: string
  resume_filename: string
  jd_id: string
  jd_title: string
  rubric_version: string
  points: DiagnosisPoint[]
  average_total: number
  best_total: number
  improvement: number
}

export interface DiagnosisTrendResponse {
  groups: DiagnosisTrendGroup[]
}

export interface InterviewPoint {
  id: string
  created_at: string
  resume_version_no: number
  total_score: number
  question_count: number
  answered_count: number
  dimension_scores: Record<string, number>
}

export interface InterviewTrendGroup {
  resume_id: string
  resume_filename: string
  jd_id: string | null
  jd_title: string | null
  interview_type: string
  rubric_version: string
  points: InterviewPoint[]
  average_total: number
  best_total: number
  improvement: number
  dimension_changes: Record<string, number>
}

export interface InterviewTrendResponse {
  groups: InterviewTrendGroup[]
}

export interface KeywordGap {
  keyword: string
  count: number
}

export interface RequirementGap {
  requirement: string
  count: number
}

export interface DimensionAverage {
  key: string
  label: string
  average: number
  sample_count: number
}

export interface WeaknessReport {
  missing_keywords: KeywordGap[]
  missing_requirements: RequirementGap[]
  interview_dimensions: DimensionAverage[]
  lowest_dimension: string | null
}
