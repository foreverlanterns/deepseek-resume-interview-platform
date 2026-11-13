import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    globals: true,
    include: ['src/**/*.spec.ts'],
    restoreMocks: true,
    // Windows 下多个测试文件并发写同一个 SSR 缓存文件会触发 EPERM，串行执行更稳定
    fileParallelism: false,
  },
})
