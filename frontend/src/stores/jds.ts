import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  createJobDescription,
  deleteJobDescription,
  fetchJobDescriptions,
  updateJobDescription,
} from '@/api/jds'
import type { JobDescription, JobDescriptionPayload } from '@/types/jd'

export const useJdStore = defineStore('jds', () => {
  const items = ref<JobDescription[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)

  async function load(force = false): Promise<void> {
    if (initialized.value && !force) {
      return
    }
    loading.value = true
    error.value = null
    try {
      items.value = await fetchJobDescriptions()
      initialized.value = true
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '岗位列表加载失败'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function create(payload: JobDescriptionPayload): Promise<JobDescription> {
    saving.value = true
    error.value = null
    try {
      const jd = await createJobDescription(payload)
      items.value = [jd, ...items.value]
      initialized.value = true
      return jd
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '岗位创建失败'
      throw caught
    } finally {
      saving.value = false
    }
  }

  async function update(
    jdId: string,
    payload: JobDescriptionPayload,
  ): Promise<JobDescription> {
    saving.value = true
    error.value = null
    try {
      const jd = await updateJobDescription(jdId, payload)
      items.value = items.value.map((item) => (item.id === jdId ? jd : item))
      return jd
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '岗位更新失败'
      throw caught
    } finally {
      saving.value = false
    }
  }

  async function remove(jdId: string): Promise<void> {
    error.value = null
    try {
      await deleteJobDescription(jdId)
      items.value = items.value.filter((item) => item.id !== jdId)
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '岗位删除失败'
      throw caught
    }
  }

  function reset(): void {
    items.value = []
    error.value = null
    initialized.value = false
  }

  return { items, loading, saving, error, initialized, load, create, update, remove, reset }
})
