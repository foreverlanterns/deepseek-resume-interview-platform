import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  deleteResume,
  fetchResumes,
  uploadResume,
} from '@/api/resumes'
import type { ResumeDetail, ResumeSummary } from '@/types/resume'

export const useResumeStore = defineStore('resumes', () => {
  const items = ref<ResumeSummary[]>([])
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)

  async function load(force = false): Promise<void> {
    if (initialized.value && !force) {
      return
    }
    loading.value = true
    error.value = null
    try {
      items.value = await fetchResumes()
      initialized.value = true
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '简历列表加载失败'
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File): Promise<ResumeDetail> {
    uploading.value = true
    error.value = null
    try {
      const detail = await uploadResume(file)
      items.value = [detail, ...items.value.filter((item) => item.id !== detail.id)]
      initialized.value = true
      return detail
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '简历上传失败'
      throw caught
    } finally {
      uploading.value = false
    }
  }

  async function remove(resumeId: string): Promise<void> {
    error.value = null
    try {
      await deleteResume(resumeId)
      items.value = items.value.filter((item) => item.id !== resumeId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '删除简历失败'
      throw caught
    }
  }

  function reset(): void {
    items.value = []
    error.value = null
    initialized.value = false
  }

  return { items, loading, uploading, error, initialized, load, upload, remove, reset }
})
