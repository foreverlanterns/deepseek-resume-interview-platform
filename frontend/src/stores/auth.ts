import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchMe,
  login as loginRequest,
  register as registerRequest,
} from '@/api/auth'
import type { LoginPayload, RegisterPayload, User } from '@/types/auth'
import {
  clearToken,
  getToken,
  setToken,
  setUnauthorizedHandler,
} from '@/utils/token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<User | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const displayName = computed(() => user.value?.display_name || user.value?.email || '')

  // Axios 401 时同步清空页面状态，避免 token 已失效但界面仍显示已登录
  setUnauthorizedHandler(() => {
    token.value = null
    user.value = null
    initialized.value = true
  })

  function applySession(accessToken: string): void {
    token.value = accessToken
    setToken(accessToken)
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    clearToken()
  }

  async function completeLogin(accessToken: string): Promise<void> {
    applySession(accessToken)
    user.value = await fetchMe()
    initialized.value = true
  }

  async function login(payload: LoginPayload): Promise<void> {
    loading.value = true
    try {
      const result = await loginRequest(payload)
      await completeLogin(result.access_token)
    } catch (error) {
      clearSession()
      throw error
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<void> {
    loading.value = true
    try {
      await registerRequest(payload)
      const result = await loginRequest({
        email: payload.email,
        password: payload.password,
      })
      await completeLogin(result.access_token)
    } catch (error) {
      clearSession()
      throw error
    } finally {
      loading.value = false
    }
  }

  async function restore(): Promise<void> {
    if (initialized.value) {
      return
    }
    if (!token.value) {
      initialized.value = true
      return
    }
    try {
      user.value = await fetchMe()
    } catch {
      clearSession()
    } finally {
      initialized.value = true
    }
  }

  function logout(): void {
    clearSession()
    initialized.value = true
  }

  return {
    token,
    user,
    loading,
    initialized,
    isAuthenticated,
    displayName,
    login,
    register,
    restore,
    logout,
  }
})
