<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'

interface Dimension {
  key: string
  name: string
  weight: number
  hint: string
  color: string
}

interface Stage {
  title: string
  detail: string
  state: 'done' | 'current' | 'todo'
}

const app = useAppStore()
const router = useRouter()
const { health, loading, error } = storeToRefs(app)

const dimensions: Dimension[] = [
  { key: 'format', name: '格式规范性', weight: 15, hint: '文本可解析、板块标题、日期一致性', color: '#60a5fa' },
  { key: 'completeness', name: '内容完整度', weight: 20, hint: '教育、工作、项目、技能与成果表达', color: '#34d399' },
  { key: 'keywords', name: '关键词优化', weight: 25, hint: 'JD 关键词覆盖、同义词归一、技能层级', color: '#fbbf24' },
  { key: 'jd_match', name: 'JD 匹配度', weight: 40, hint: '硬性要求、经验相关性、项目证据', color: '#2563eb' },
]

const stages: Stage[] = [
  { title: '工程骨架', detail: '配置系统、PostgreSQL 连接、Alembic、健康检查、前端基座', state: 'done' },
  { title: '用户与认证', detail: '注册登录、JWT、受保护路由、用户级数据隔离', state: 'done' },
  {
    title: '简历上传与解析',
    detail: 'PDF/DOCX 上传、文件校验、文本提取、用户隔离；字段校正与 OCR 后续',
    state: 'current',
  },
  { title: '四维诊断', detail: '规则评分、模型语义证据、事实约束修改示例', state: 'todo' },
  { title: '模拟面试', detail: '简历与 JD 驱动出题、逐题评价、两级追问、报告', state: 'todo' },
  { title: '历史成长', detail: '同岗位、同 rubric_version 的趋势与弱项对比', state: 'todo' },
]

const statusText = computed(() => {
  if (loading.value) return '检测中'
  if (error.value) return '后端未连接'
  if (!health.value) return '待检测'
  return health.value.database === 'ok' ? '服务正常' : '数据库未就绪'
})

const statusType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  if (loading.value) return 'info'
  if (error.value) return 'danger'
  if (health.value?.database === 'ok') return 'success'
  if (health.value) return 'warning'
  return 'info'
})

function formatDate(value?: string): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

function refresh(): void {
  void app.checkHealth()
}

function goResumes(): void {
  void router.push({ name: 'resumes' })
}

function openDocs(): void {
  window.open('http://127.0.0.1:8000/docs', '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-copy">
        <el-tag effect="plain" round class="stage-tag">阶段 3a · 简历上传</el-tag>
        <h1>把简历从“投出去”<br />变成“有证据地投出去”</h1>
        <p class="hero-desc">
          结构化解析 → 四维诊断 → 事实约束改写 → 简历驱动面试 → 同口径成长对比。
          当前已完成账号体系与简历上传提取，接下来进入字段校正与四维诊断。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="goResumes">进入我的简历</el-button>
          <el-button size="large" :loading="loading" @click="refresh">检测后端服务</el-button>
          <el-button size="large" @click="openDocs">打开 API 文档</el-button>
        </div>
      </div>

      <div class="hero-panel">
        <div class="panel-head">
          <span>四维诊断权重</span>
          <span class="panel-badge">100 分制</span>
        </div>
        <div v-for="dimension in dimensions" :key="dimension.key" class="dimension">
          <div class="dimension-meta">
            <span>{{ dimension.name }}</span>
            <strong>{{ dimension.weight }}%</strong>
          </div>
          <el-progress
            :percentage="dimension.weight"
            :stroke-width="8"
            :show-text="false"
            :color="dimension.color"
          />
          <p>{{ dimension.hint }}</p>
        </div>
        <p class="panel-note">规则算分，模型只提供语义判断与证据，总分由程序合成。</p>
      </div>
    </section>

    <section class="workspace">
      <el-card shadow="never" class="panel-card health-card">
        <template #header>
          <div class="card-head">
            <span>运行状态</span>
            <el-tag :type="statusType" effect="light" size="small">{{ statusText }}</el-tag>
          </div>
        </template>

        <el-alert
          v-if="error"
          :title="error"
          type="error"
          :closable="false"
          show-icon
          class="health-alert"
        />

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="后端服务">
            {{ health ? '已连接' : '未连接' }}
          </el-descriptions-item>
          <el-descriptions-item label="数据库">
            {{ health?.database === 'ok' ? 'PostgreSQL 正常' : '未就绪' }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">{{ health?.version ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ health?.environment ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="接口前缀">/api/v1</el-descriptions-item>
          <el-descriptions-item label="检查时间">
            {{ formatDate(health?.checked_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <p v-if="health?.database_error" class="db-error">{{ health.database_error }}</p>
        <p class="hint">
          数据库不可用时后端返回 degraded 而不是崩溃；填入真实密码后，健康检查会自动恢复。
        </p>
      </el-card>

      <el-card shadow="never" class="panel-card roadmap-card">
        <template #header>
          <div class="card-head">
            <span>开发路线</span>
            <span class="subtle">一次只推进一个模块</span>
          </div>
        </template>

        <ol class="timeline">
          <li v-for="stage in stages" :key="stage.title" :class="`stage-${stage.state}`">
            <span class="timeline-dot"></span>
            <div class="timeline-body">
              <div class="timeline-title">
                {{ stage.title }}
                <el-tag v-if="stage.state === 'current'" size="small" effect="plain">当前</el-tag>
              </div>
              <p>{{ stage.detail }}</p>
            </div>
          </li>
        </ol>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 34px;
  align-items: stretch;
  margin-bottom: 30px;
}

.hero-copy {
  padding: 12px 0;
}

.stage-tag {
  margin-bottom: 18px;
  color: var(--app-primary);
  border-color: #bfdbfe;
  background: #eff6ff;
}

.hero h1 {
  margin: 0 0 16px;
  font-size: clamp(30px, 4.4vw, 46px);
  line-height: 1.24;
  letter-spacing: -0.6px;
  color: var(--app-text);
}

.hero-desc {
  margin: 0 0 26px;
  max-width: 520px;
  font-size: 15px;
  line-height: 1.85;
  color: var(--app-muted);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-panel {
  background: linear-gradient(160deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid var(--app-border);
  border-radius: 18px;
  padding: 22px 22px 16px;
  box-shadow: 0 18px 40px -28px rgba(15, 23, 42, 0.35);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text);
  margin-bottom: 18px;
}

.panel-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--app-muted);
  background: #f1f5f9;
  border-radius: 999px;
  padding: 3px 9px;
}

.dimension + .dimension {
  margin-top: 14px;
}

.dimension-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  color: #334155;
  margin-bottom: 6px;
}

.dimension-meta strong {
  color: var(--app-text);
  font-weight: 600;
}

.dimension p {
  margin: 6px 0 0;
  font-size: 11px;
  color: var(--app-muted);
}

.panel-note {
  margin: 18px 0 0;
  padding-top: 14px;
  border-top: 1px dashed var(--app-border);
  font-size: 11px;
  line-height: 1.6;
  color: var(--app-muted);
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 22px;
}

.panel-card {
  border-radius: 16px;
  border-color: var(--app-border);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text);
}

.subtle {
  font-size: 11px;
  font-weight: 400;
  color: var(--app-muted);
}

.health-alert {
  margin-bottom: 14px;
}

.db-error {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: 9px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
}

.hint {
  margin: 14px 0 0;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--app-muted);
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline li {
  position: relative;
  display: flex;
  gap: 12px;
  padding-bottom: 16px;
}

.timeline li:last-child {
  padding-bottom: 0;
}

.timeline li::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 14px;
  bottom: 0;
  width: 1px;
  background: var(--app-border);
}

.timeline li:last-child::before {
  display: none;
}

.timeline-dot {
  width: 9px;
  height: 9px;
  margin-top: 5px;
  border-radius: 50%;
  background: #cbd5e1;
  flex: none;
  z-index: 1;
}

.stage-current .timeline-dot {
  background: var(--app-primary);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14);
}

.stage-done .timeline-dot {
  background: #16a34a;
}

.stage-done .timeline-title {
  color: #334155;
}

.timeline-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text);
}

.timeline-body p {
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--app-muted);
}

.stage-todo .timeline-title {
  color: #475569;
}

@media (max-width: 900px) {
  .hero,
  .workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-copy {
    padding: 0;
  }
}
</style>
