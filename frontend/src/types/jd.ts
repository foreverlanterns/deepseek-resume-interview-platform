export interface JobDescription {
  id: string
  title: string
  company: string | null
  raw_text: string
  required_skills: string[]
  preferred_skills: string[]
  keywords: string[]
  responsibilities: string[]
  qualifications: string[]
  created_at: string
  updated_at: string
}

export interface JobDescriptionPayload {
  title: string
  company?: string | null
  raw_text: string
  required_skills: string[]
  preferred_skills: string[]
  keywords: string[]
  responsibilities: string[]
  qualifications: string[]
}
