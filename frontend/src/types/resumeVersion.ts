export interface BasicInfo {
  name: string | null
  phone: string | null
  email: string | null
  location: string | null
  headline: string | null
  source_text: string | null
}

export interface EducationItem {
  school: string
  degree: string | null
  major: string | null
  start_date: string | null
  end_date: string | null
  details: string[]
  source_text: string | null
}

export interface WorkItem {
  company: string
  title: string | null
  start_date: string | null
  end_date: string | null
  location: string | null
  highlights: string[]
  source_text: string | null
}

export interface ProjectItem {
  name: string
  role: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
  highlights: string[]
  tech_stack: string[]
  source_text: string | null
}

export interface SkillGroup {
  category: string
  items: string[]
  source_text: string | null
}

export interface CertificateItem {
  name: string
  issuer: string | null
  date: string | null
  source_text: string | null
}

export interface AwardItem {
  name: string
  date: string | null
  description: string | null
  source_text: string | null
}

export interface LanguageItem {
  name: string
  level: string | null
}

export interface ParsedResume {
  basic_info: BasicInfo
  summary: string | null
  education: EducationItem[]
  work_experience: WorkItem[]
  projects: ProjectItem[]
  skills: SkillGroup[]
  certificates: CertificateItem[]
  awards: AwardItem[]
  languages: LanguageItem[]
}

export type ResumeVersionStatus = 'parsed' | 'corrected' | 'failed'

export interface ResumeVersionSummary {
  version_no: number
  status: ResumeVersionStatus
  model_name: string | null
  prompt_version: string | null
  parser_version: string | null
  base_version_no: number | null
  has_corrections: boolean
  created_at: string
}

export interface ResumeVersionDetail extends ResumeVersionSummary {
  parsed_data: ParsedResume | null
  corrected_data: ParsedResume | null
  effective_data: ParsedResume | null
  error_message: string | null
}

export interface BasicInfoForm {
  name: string
  phone: string
  email: string
  location: string
  headline: string
  source_text: string
}

export interface EducationForm {
  school: string
  degree: string
  major: string
  start_date: string
  end_date: string
  details: string[]
  source_text: string
}

export interface WorkForm {
  company: string
  title: string
  start_date: string
  end_date: string
  location: string
  highlights: string[]
  source_text: string
}

export interface ProjectForm {
  name: string
  role: string
  start_date: string
  end_date: string
  description: string
  highlights: string[]
  tech_stack: string[]
  source_text: string
}

export interface SkillForm {
  category: string
  items: string[]
  source_text: string
}

export interface CertificateForm {
  name: string
  issuer: string
  date: string
  source_text: string
}

export interface AwardForm {
  name: string
  date: string
  description: string
  source_text: string
}

export interface LanguageForm {
  name: string
  level: string
}

export interface ParsedResumeForm {
  basic_info: BasicInfoForm
  summary: string
  education: EducationForm[]
  work_experience: WorkForm[]
  projects: ProjectForm[]
  skills: SkillForm[]
  certificates: CertificateForm[]
  awards: AwardForm[]
  languages: LanguageForm[]
}
