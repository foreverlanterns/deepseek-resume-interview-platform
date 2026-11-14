import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchResumeVersion,
  fetchResumeVersions,
  parseResume,
  saveResumeCorrection,
} from '@/api/resumeVersions'
import type {
  ParsedResume,
  ResumeVersionDetail,
  ResumeVersionSummary,
} from '@/types/resumeVersion'

function toSummary(version: ResumeVersionDetail): ResumeVersionSummary {
  return {
    version_no: version.version_no,
    status: version.status,
    model_name: version.model_name,
    prompt_version: version.prompt_version,
    parser_version: version.parser_version,
    base_version_no: version.base_version_no,
    has_corrections: version.has_corrections,
    created_at: version.created_at,
  }
}

export const useResumeVersionStore = defineStore('resumeVersions', () => {
  const versions = ref<ResumeVersionSummary[]>([])
  const current = ref<ResumeVersionDetail | null>(null)
  const loading = ref(false)
  const parsing = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  function mergeVersion(version: ResumeVersionDetail): void {
    const summary = toSummary(version)
    versions.value = [
      summary,
      ...versions.value.filter((item) => item.version_no !== summary.version_no),
    ]
    current.value = version
  }

  async function loadVersions(resumeId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      versions.value = await fetchResumeVersions(resumeId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '版本列表加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function selectVersion(resumeId: string, versionNo: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      current.value = await fetchResumeVersion(resumeId, versionNo)
    } catch (caught) {
      current.value = null
      error.value = caught instanceof Error ? caught.message : '版本详情加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function parse(resumeId: string): Promise<ResumeVersionDetail> {
    parsing.value = true
    error.value = null
    try {
      const version = await parseResume(resumeId)
      mergeVersion(version)
      return version
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '结构化解析失败'
      throw caught
    } finally {
      parsing.value = false
    }
  }

  async function saveCorrection(
    resumeId: string,
    baseVersionNo: number,
    data: ParsedResume,
  ): Promise<ResumeVersionDetail> {
    saving.value = true
    error.value = null
    try {
      const version = await saveResumeCorrection(resumeId, baseVersionNo, data)
      mergeVersion(version)
      return version
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '校正保存失败'
      throw caught
    } finally {
      saving.value = false
    }
  }

  function reset(): void {
    versions.value = []
    current.value = null
    error.value = null
  }

  return {
    versions,
    current,
    loading,
    parsing,
    saving,
    error,
    loadVersions,
    selectVersion,
    parse,
    saveCorrection,
    reset,
  }
})
