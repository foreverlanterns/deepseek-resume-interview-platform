import { AxiosError } from 'axios'
import { describe, expect, it } from 'vitest'

import { ApiError, extractErrorMessage, normalizeApiError } from '@/api/http'

describe('extractErrorMessage', () => {
  it('读取 FastAPI 字符串 detail', () => {
    expect(extractErrorMessage({ detail: '账号或密码错误' })).toBe('账号或密码错误')
  })

  it('合并 422 校验错误并带字段路径', () => {
    const message = extractErrorMessage({
      detail: [
        { loc: ['body', 'email'], msg: '邮箱格式不正确' },
        { loc: ['body', 'password'], msg: '长度不足 8 位' },
      ],
    })
    expect(message).toBe('body.email: 邮箱格式不正确；body.password: 长度不足 8 位')
  })

  it('无法识别时返回兜底文案', () => {
    expect(extractErrorMessage(undefined, '兜底文案')).toBe('兜底文案')
  })
})

describe('normalizeApiError', () => {
  it('已是 ApiError 时原样返回', () => {
    const original = new ApiError('原始错误')
    expect(normalizeApiError(original)).toBe(original)
  })

  it('网络不可用时给出启动提示', () => {
    const normalized = normalizeApiError(new AxiosError('Network Error', 'ERR_NETWORK'))
    expect(normalized).toBeInstanceOf(ApiError)
    expect(normalized.code).toBe('network_error')
    expect(normalized.message).toContain('无法连接服务器')
  })

  it('超时单独标记', () => {
    const normalized = normalizeApiError(new AxiosError('timeout', 'ECONNABORTED'))
    expect(normalized.code).toBe('timeout')
  })

  it('普通 Error 转为 ApiError', () => {
    const normalized = normalizeApiError(new Error('渲染失败'))
    expect(normalized.code).toBe('client_error')
    expect(normalized.message).toBe('渲染失败')
  })
})
