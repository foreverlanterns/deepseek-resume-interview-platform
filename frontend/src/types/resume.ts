export type ResumeStatus = 'uploaded' | 'extracting' | 'extracted' | 'needs_ocr' | 'failed'

export interface ResumeSummary {
  id: string
  original_filename: string
  status: ResumeStatus
  text_length: number
  page_count: number | null
  created_at: string
}

export interface ResumeDetail extends ResumeSummary {
  mime_type: string
  file_size: number
  sha256: string
  text_preview: string
  error_message: string | null
}
