<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

type Mode = 'login' | 'register'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const mode = ref<Mode>(route.query.mode === 'register' ? 'register' : 'login')
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  email: '',
  password: '',
  confirmPassword: '',
  displayName: '',
})

const isRegister = computed(() => mode.value === 'register')

function validateConfirm(
  _rule: unknown,
  value: string,
  callback: (error?: string | Error) => void,
): void {
  if (isRegister.value && value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules = computed<FormRules>(() => {
  const base: FormRules = {
    email: [
      { required: true, message: '请输入邮箱', trigger: 'blur' },
      { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 8, max: 128, message: '密码长度需在 8-128 位之间', trigger: 'blur' },
    ],
  }
  if (isRegister.value) {
    base.confirmPassword = [
      { required: true, message: '请再次输入密码', trigger: 'blur' },
      { validator: validateConfirm, trigger: ['blur', 'change'] },
    ]
  }
  return base
})

function switchMode(next: Mode): void {
  mode.value = next
  form.password = ''
  form.confirmPassword = ''
  formRef.value?.clearValidate()
}

async function goAfterAuth(): Promise<void> {
  const redirect = route.query.redirect
  const target =
    typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
      ? redirect
      : '/'
  await router.replace(target)
}

async function submit(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    if (isRegister.value) {
      await auth.register({
        email: form.email.trim(),
        password: form.password,
        display_name: form.displayName.trim() || null,
      })
      ElMessage.success('注册成功，已自动登录')
    } else {
      await auth.login({
        email: form.email.trim(),
        password: form.password,
      })
      ElMessage.success('登录成功')
    }
    await goAfterAuth()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <section class="brand-panel">
      <el-tag effect="plain" round class="eyebrow">账号与数据安全</el-tag>
      <h1>先建立身份，<br />再开始诊断。</h1>
      <p class="brand-desc">
        简历、诊断报告和面试记录都会绑定到你的账号。换设备登录，历史记录仍然在。
      </p>
      <ul class="benefits">
        <li>
          <span class="bullet"></span>
          <span>账号之间的数据完全隔离</span>
        </li>
        <li>
          <span class="bullet"></span>
          <span>密码加密存储，不保存明文</span>
        </li>
        <li>
          <span class="bullet"></span>
          <span>换设备登录，简历与记录仍然在</span>
        </li>
      </ul>
      <p class="brand-foot">基于 DeepSeek 的智能简历诊断与面试模拟平台</p>
    </section>

    <el-card class="auth-card" shadow="never">
      <div class="auth-head">
        <h2>{{ isRegister ? '创建账号' : '欢迎回来' }}</h2>
        <p>
          {{ isRegister ? '注册后自动登录，开始建立你的简历档案。' : '登录后继续查看诊断与面试记录。' }}
        </p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submit"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            size="large"
            placeholder="you@example.com"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item v-if="isRegister" label="昵称（可选）" prop="displayName">
          <el-input
            v-model="form.displayName"
            size="large"
            maxlength="50"
            placeholder="怎么称呼你"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            size="large"
            show-password
            :placeholder="isRegister ? '至少 8 位' : '请输入密码'"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
          />
        </el-form-item>

        <el-form-item v-if="isRegister" label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            size="large"
            show-password
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="submit"
          native-type="submit"
          :loading="submitting"
        >
          {{ isRegister ? '注册并登录' : '登录' }}
        </el-button>
      </el-form>

      <div class="switch">
        <span>{{ isRegister ? '已有账号？' : '还没有账号？' }}</span>
        <el-button link type="primary" @click="switchMode(isRegister ? 'login' : 'register')">
          {{ isRegister ? '去登录' : '立即注册' }}
        </el-button>
      </div>

      <p class="security-note">登录凭证仅保存在本机浏览器；退出登录会立即清除。</p>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
  gap: 48px;
  align-items: center;
  min-height: calc(100vh - 240px);
  padding: 24px 0 40px;
}

.brand-panel {
  padding: 12px 0;
}

.eyebrow {
  margin-bottom: 20px;
  color: var(--app-primary);
  border-color: #bfdbfe;
  background: #eff6ff;
}

.brand-panel h1 {
  margin: 0 0 18px;
  font-size: clamp(32px, 4.4vw, 48px);
  line-height: 1.22;
  letter-spacing: -0.8px;
  color: var(--app-text);
}

.brand-desc {
  max-width: 460px;
  margin: 0 0 26px;
  font-size: 15px;
  line-height: 1.85;
  color: var(--app-muted);
}

.benefits {
  list-style: none;
  margin: 0 0 32px;
  padding: 0;
  display: grid;
  gap: 13px;
}

.benefits li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #334155;
}

.bullet {
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--app-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
  flex: none;
}

.brand-foot {
  margin: 0;
  font-size: 11.5px;
  color: #94a3b8;
}

.auth-card {
  border-radius: 18px;
  border-color: var(--app-border);
  box-shadow: 0 24px 50px -36px rgba(15, 23, 42, 0.45);
}

.auth-head {
  margin-bottom: 22px;
}

.auth-head h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: var(--app-text);
}

.auth-head p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--app-muted);
}

.submit {
  width: 100%;
  margin-top: 4px;
}

.switch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  margin-top: 18px;
  font-size: 13px;
  color: var(--app-muted);
}

.security-note {
  margin: 18px 0 0;
  padding-top: 14px;
  border-top: 1px dashed var(--app-border);
  font-size: 11px;
  line-height: 1.6;
  color: #94a3b8;
  text-align: center;
}

@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: minmax(0, 1fr);
    gap: 28px;
    padding-top: 8px;
  }

  .brand-panel h1 {
    font-size: 32px;
  }

  .benefits {
    margin-bottom: 12px;
  }

  .brand-foot {
    display: none;
  }
}
</style>
