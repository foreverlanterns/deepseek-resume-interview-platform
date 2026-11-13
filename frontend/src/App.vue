<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const app = useAppStore()
const auth = useAuthStore()
const router = useRouter()
const { health, loading, error } = storeToRefs(app)
const { isAuthenticated, displayName } = storeToRefs(auth)

const statusText = computed(() => {
  if (loading.value) return '正在检测'
  if (error.value) return '后端未连接'
  if (!health.value) return '等待检测'
  return health.value.database === 'ok' ? '服务正常' : '数据库未就绪'
})

const statusClass = computed(() => {
  if (error.value) return 'danger'
  if (health.value?.database === 'ok') return 'ok'
  return 'warn'
})

async function handleUserCommand(command: string | number | object): Promise<void> {
  if (command !== 'logout') {
    return
  }
  auth.logout()
  ElMessage.success('已退出登录')
  await router.push({ name: 'auth' })
}

onMounted(() => {
  void app.checkHealth()
  void auth.restore()
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="header-inner">
        <router-link to="/" class="brand">
          <span class="brand-mark">AI</span>
          <span class="brand-text">
            <strong>智能简历诊断与面试模拟平台</strong>
            <small>DeepSeek 驱动的简历优化与面试训练</small>
          </span>
        </router-link>

        <nav class="nav">
          <router-link v-if="isAuthenticated" to="/" class="nav-link">工作台</router-link>
          <router-link v-if="isAuthenticated" to="/resumes" class="nav-link">简历</router-link>
        </nav>

        <div v-if="isAuthenticated" class="user-menu">
          <el-dropdown trigger="click" @command="handleUserCommand">
            <button class="user-trigger" type="button">
              <span class="user-avatar">{{ displayName.slice(0, 1).toUpperCase() }}</span>
              <span class="user-name">{{ displayName }}</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <router-link v-else to="/auth" class="auth-link">登录 / 注册</router-link>

        <div class="status" :class="statusClass">
          <span class="status-dot"></span>
          <span>{{ statusText }}</span>
        </div>
      </div>
    </header>

    <main class="app-main">
      <router-view />
    </main>

    <footer class="app-footer">
      <span>毕业设计 · 阶段 3a 简历上传</span>
      <span>FastAPI · Vue 3 · TypeScript · PostgreSQL 17</span>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.86);
  border-bottom: 1px solid var(--app-border);
  backdrop-filter: blur(12px);
}

.header-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 28px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.25);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.brand-text strong {
  font-size: 15px;
  color: var(--app-text);
}

.brand-text small {
  font-size: 11px;
  color: var(--app-muted);
}

.nav {
  margin-left: auto;
}

.nav-link {
  font-size: 14px;
  color: var(--app-muted);
  padding: 6px 10px;
  border-radius: 8px;
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--app-primary);
  background: #eff4ff;
}

.auth-link {
  font-size: 13px;
  color: var(--app-primary);
  padding: 6px 10px;
  border-radius: 8px;
  background: #eff6ff;
}

.auth-link:hover {
  background: #dbeafe;
}

.user-menu {
  flex: none;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--app-text);
  font-size: 13px;
  cursor: pointer;
}

.user-trigger:hover {
  background: #f1f5f9;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--app-muted);
  border: 1px solid var(--app-border);
  border-radius: 999px;
  padding: 5px 11px;
  background: #fff;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
}

.status.ok .status-dot {
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15);
}

.status.warn .status-dot {
  background: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
}

.status.danger .status-dot {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.15);
}

.app-main {
  flex: 1;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 34px 24px 56px;
}

.app-footer {
  border-top: 1px solid var(--app-border);
  padding: 18px 24px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
  font-size: 12px;
  color: var(--app-muted);
}

@media (max-width: 720px) {
  .header-inner {
    flex-wrap: wrap;
    gap: 12px;
  }

  .nav {
    order: 3;
    margin-left: 0;
  }

  .status {
    margin-left: auto;
  }

  .user-name {
    display: none;
  }

  .app-footer {
    flex-direction: column;
  }
}
</style>
