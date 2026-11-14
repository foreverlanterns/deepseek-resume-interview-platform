import type {
  ParsedResume,
  ParsedResumeForm,
} from '@/types/resumeVersion'

function text(value: string | null | undefined): string {
  return value ?? ''
}

function nullable(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function cleanList(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean)
}

export function toParsedResumeForm(data: ParsedResume): ParsedResumeForm {
  return {
    basic_info: {
      name: text(data.basic_info.name),
      phone: text(data.basic_info.phone),
      email: text(data.basic_info.email),
      location: text(data.basic_info.location),
      headline: text(data.basic_info.headline),
      source_text: text(data.basic_info.source_text),
    },
    summary: text(data.summary),
    education: data.education.map((item) => ({
      school: text(item.school),
      degree: text(item.degree),
      major: text(item.major),
      start_date: text(item.start_date),
      end_date: text(item.end_date),
      details: [...item.details],
      source_text: text(item.source_text),
    })),
    work_experience: data.work_experience.map((item) => ({
      company: text(item.company),
      title: text(item.title),
      start_date: text(item.start_date),
      end_date: text(item.end_date),
      location: text(item.location),
      highlights: [...item.highlights],
      source_text: text(item.source_text),
    })),
    projects: data.projects.map((item) => ({
      name: text(item.name),
      role: text(item.role),
      start_date: text(item.start_date),
      end_date: text(item.end_date),
      description: text(item.description),
      highlights: [...item.highlights],
      tech_stack: [...item.tech_stack],
      source_text: text(item.source_text),
    })),
    skills: data.skills.map((item) => ({
      category: text(item.category),
      items: [...item.items],
      source_text: text(item.source_text),
    })),
    certificates: data.certificates.map((item) => ({
      name: text(item.name),
      issuer: text(item.issuer),
      date: text(item.date),
      source_text: text(item.source_text),
    })),
    awards: data.awards.map((item) => ({
      name: text(item.name),
      date: text(item.date),
      description: text(item.description),
      source_text: text(item.source_text),
    })),
    languages: data.languages.map((item) => ({
      name: text(item.name),
      level: text(item.level),
    })),
  }
}

export function toParsedResumePayload(form: ParsedResumeForm): ParsedResume {
  return {
    basic_info: {
      name: nullable(form.basic_info.name),
      phone: nullable(form.basic_info.phone),
      email: nullable(form.basic_info.email),
      location: nullable(form.basic_info.location),
      headline: nullable(form.basic_info.headline),
      source_text: nullable(form.basic_info.source_text),
    },
    summary: nullable(form.summary),
    education: form.education.map((item) => ({
      school: item.school.trim(),
      degree: nullable(item.degree),
      major: nullable(item.major),
      start_date: nullable(item.start_date),
      end_date: nullable(item.end_date),
      details: cleanList(item.details),
      source_text: nullable(item.source_text),
    })),
    work_experience: form.work_experience.map((item) => ({
      company: item.company.trim(),
      title: nullable(item.title),
      start_date: nullable(item.start_date),
      end_date: nullable(item.end_date),
      location: nullable(item.location),
      highlights: cleanList(item.highlights),
      source_text: nullable(item.source_text),
    })),
    projects: form.projects.map((item) => ({
      name: item.name.trim(),
      role: nullable(item.role),
      start_date: nullable(item.start_date),
      end_date: nullable(item.end_date),
      description: nullable(item.description),
      highlights: cleanList(item.highlights),
      tech_stack: cleanList(item.tech_stack),
      source_text: nullable(item.source_text),
    })),
    skills: form.skills.map((item) => ({
      category: item.category.trim(),
      items: cleanList(item.items),
      source_text: nullable(item.source_text),
    })),
    certificates: form.certificates.map((item) => ({
      name: item.name.trim(),
      issuer: nullable(item.issuer),
      date: nullable(item.date),
      source_text: nullable(item.source_text),
    })),
    awards: form.awards.map((item) => ({
      name: item.name.trim(),
      date: nullable(item.date),
      description: nullable(item.description),
      source_text: nullable(item.source_text),
    })),
    languages: form.languages.map((item) => ({
      name: item.name.trim(),
      level: nullable(item.level),
    })),
  }
}

export function createEmptyParsedResumeForm(): ParsedResumeForm {
  return {
    basic_info: {
      name: '',
      phone: '',
      email: '',
      location: '',
      headline: '',
      source_text: '',
    },
    summary: '',
    education: [],
    work_experience: [],
    projects: [],
    skills: [],
    certificates: [],
    awards: [],
    languages: [],
  }
}
