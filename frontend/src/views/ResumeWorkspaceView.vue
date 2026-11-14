<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import LinesEditor from '@/components/LinesEditor.vue'
import { fetchResume } from '@/api/resumes'
import { useResumeVersionStore } from '@/stores/resumeVersions'
import type { ResumeDetail } from '@/types/resume'
import type {
  ParsedResumeForm,
  ResumeVersionStatus,
} from '@/types/resumeVersion'
import {
  createEmptyParsedResumeForm,
  toParsedResumeForm,
  toParsedResumePayload,
} from '@/utils/resumeForm'

const route = useRoute()
const router = useRouter()
const store = useResumeVersionStore()

const resume = ref<ResumeDetail | null>(null)
const form = ref<ParsedResumeForm>(createEmptyParsedResumeForm())
const hasData = ref(false)
const pageLoading = ref(false)

const resumeId = computed(() => String(route.params.id))
const current = computed(() => store.current)
const canParse = computed(
  () => resume.value?.status === 'extracted' && (resume.value?.text_length ?? 0) > 0,
)

const VERSION_STATUS: Record<
  ResumeVersionStatus,
  { label: string; type: 'success' | 'info' | 'danger' }
> = {
  parsed: { label: '模型解析', type: 'success' },
  corrected: { label: '人工校正', type: 'info' },
  failed: { label: '解析失败', type: 'danger' },
}

const RESUME_STATUS: Record<ResumeDetail['status'], string> = {
  uploaded: '待解析',
  extracting: '解析中',
  extracted: '文本已提取',
  needs_ocr: '需 OCR',
  failed: '文本提取失败',
}

function versionLabel(status: ResumeVersionStatus): string {
  return VERSION_STATUS[status]?.label ?? status
}

function versionType(status: ResumeVersionStatus): 'success' | 'info' | 'danger' {
  return VERSION_STATUS[status]?.type ?? 'info'
}

function resumeStatusType(status: ResumeDetail['status']): 'success' | 'info' | 'warning' | 'danger' {
  if (status === 'extracted') return 'success'
  if (status === 'needs_ocr' || status === 'extracting') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

function syncForm(): void {
  const data = store.current?.effective_data
  if (data) {
    form.value = toParsedResumeForm(data)
    hasData.value = true
    return
  }
  form.value = createEmptyParsedResumeForm()
  hasData.value = false
}

async function load(): Promise<void> {
  pageLoading.value = true
  store.reset()
  try {
    resume.value = await fetchResume(resumeId.value)
    await store.loadVersions(resumeId.value)
    const first = store.versions[0]
    if (first) {
      await store.selectVersion(resumeId.value, first.version_no)
    }
    syncForm()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '简历加载失败')
  } finally {
    pageLoading.value = false
  }
}

async function selectVersion(versionNo: number): Promise<void> {
  try {
    await store.selectVersion(resumeId.value, versionNo)
    syncForm()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '版本加载失败')
  }
}

async function runParse(): Promise<void> {
  if (!canParse.value) {
    ElMessage.warning('当前简历没有可解析文本，请先在简历列表确认文本提取状态')
    return
  }

  if (store.versions.length) {
    try {
      await ElMessageBox.confirm(
        '重新解析会调用 DeepSeek 并生成新版本，可能产生 API 费用。继续吗？',
        '重新解析',
        { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  }

  try {
    const version = await store.parse(resumeId.value)
    syncForm()
    ElMessage.success(`解析完成，已生成 v${version.version_no}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '结构化解析失败')
    try {
      await store.loadVersions(resumeId.value)
      const first = store.versions[0]
      if (first) {
        await store.selectVersion(resumeId.value, first.version_no)
        syncForm()
      }
    } catch {
      // 列表刷新失败时保留原始错误提示即可
    }
  }
}

function validateForm(value: ParsedResumeForm): string | null {
  if (value.education.some((item) => !item.school.trim())) {
    return '教育经历的学校名称不能为空，请填写或删除空白条目'
  }
  if (value.work_experience.some((item) => !item.company.trim())) {
    return '工作经历的公司名称不能为空，请填写或删除空白条目'
  }
  if (value.projects.some((item) => !item.name.trim())) {
    return '项目名称不能为空，请填写或删除空白条目'
  }
  if (value.skills.some((item) => !item.category.trim())) {
    return '技能分类不能为空，请填写或删除空白条目'
  }
  if (value.certificates.some((item) => !item.name.trim())) {
    return '证书名称不能为空，请填写或删除空白条目'
  }
  if (value.awards.some((item) => !item.name.trim())) {
    return '奖项名称不能为空，请填写或删除空白条目'
  }
  if (value.languages.some((item) => !item.name.trim())) {
    return '语言名称不能为空，请填写或删除空白条目'
  }
  return null
}

async function saveCorrection(): Promise<void> {
  if (!hasData.value || !current.value) {
    return
  }
  const validation = validateForm(form.value)
  if (validation) {
    ElMessage.warning(validation)
    return
  }

  try {
    const version = await store.saveCorrection(
      resumeId.value,
      current.value.version_no,
      toParsedResumePayload(form.value),
    )
    syncForm()
    ElMessage.success(`已保存为 v${version.version_no}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '校正保存失败')
  }
}

function addEducation(): void {
  form.value.education.push({
    school: '',
    degree: '',
    major: '',
    start_date: '',
    end_date: '',
    details: [],
    source_text: '',
  })
}

function addWork(): void {
  form.value.work_experience.push({
    company: '',
    title: '',
    start_date: '',
    end_date: '',
    location: '',
    highlights: [],
    source_text: '',
  })
}

function addProject(): void {
  form.value.projects.push({
    name: '',
    role: '',
    start_date: '',
    end_date: '',
    description: '',
    highlights: [],
    tech_stack: [],
    source_text: '',
  })
}

function addSkill(): void {
  form.value.skills.push({ category: '', items: [], source_text: '' })
}

function addCertificate(): void {
  form.value.certificates.push({ name: '', issuer: '', date: '', source_text: '' })
}

function addAward(): void {
  form.value.awards.push({ name: '', date: '', description: '', source_text: '' })
}

function addLanguage(): void {
  form.value.languages.push({ name: '', level: '' })
}

function removeAt(items: unknown[], index: number): void {
  items.splice(index, 1)
}

function goBack(): void {
  void router.push({ name: 'resumes' })
}

function goDiagnosis(): void {
  void router.push({ name: 'diagnosis', params: { id: resumeId.value } })
}

function goInterview(): void {
  void router.push({ name: 'interviews', query: { resume_id: resumeId.value } })
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div v-loading="pageLoading || store.loading" class="workspace-page">
    <header class="page-head">
      <div class="head-main">
        <el-button link type="primary" @click="goBack">← 返回简历列表</el-button>
        <h1>{{ resume?.original_filename || '简历结构化' }}</h1>
        <div v-if="resume" class="head-meta">
          <el-tag size="small" :type="resumeStatusType(resume.status)" effect="light">
            {{ RESUME_STATUS[resume.status] }}
          </el-tag>
          <span>{{ resume.text_length }} 字</span>
          <span>{{ formatDate(resume.created_at) }}</span>
        </div>
      </div>
      <div class="head-actions">
        <el-button v-if="hasData" type="primary" plain @click="goDiagnosis">
          开始诊断
        </el-button>
        <el-button v-if="hasData" plain @click="goInterview">模拟面试</el-button>
        <el-button
          type="primary"
          :loading="store.parsing"
          :disabled="!canParse"
          @click="runParse"
        >
          {{ store.versions.length ? '重新解析' : '用 DeepSeek 解析' }}
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="resume && !canParse"
      title="当前简历没有可解析文本。请先在简历列表确认文本提取状态；扫描件需要 OCR 支持。"
      type="warning"
      :closable="false"
      show-icon
      class="page-alert"
    />

    <div class="workspace-grid">
      <aside class="version-panel">
        <div class="panel-title">
          <span>版本历史</span>
          <small>{{ store.versions.length }}</small>
        </div>
        <button
          v-for="version in store.versions"
          :key="version.version_no"
          type="button"
          class="version-item"
          :class="{ active: current?.version_no === version.version_no }"
          @click="selectVersion(version.version_no)"
        >
          <span class="version-no">v{{ version.version_no }}</span>
          <el-tag size="small" :type="versionType(version.status)" effect="light">
            {{ versionLabel(version.status) }}
          </el-tag>
          <span class="version-meta">
            {{ version.model_name || '手动校正' }} · {{ formatDate(version.created_at) }}
          </span>
        </button>
        <el-empty
          v-if="!store.versions.length"
          :image-size="56"
          description="还没有结构化版本"
        />
      </aside>

      <main class="editor-panel">
        <el-alert
          v-if="current?.status === 'failed'"
          :title="current.error_message || '结构化解析失败'"
          type="error"
          :closable="false"
          show-icon
          class="page-alert"
        />

        <template v-if="hasData">
          <div class="editor-toolbar">
            <div>
              <strong>v{{ current?.version_no }}</strong>
              <span class="toolbar-meta">
                {{ current?.model_name || '手动校正' }} ·
                {{ current?.parser_version || 'manual' }}
              </span>
            </div>
            <el-button type="primary" :loading="store.saving" @click="saveCorrection">
              保存为新版本
            </el-button>
          </div>

          <el-alert
            v-if="current?.status === 'corrected'"
            title="当前版本包含人工校正，原始模型结果仍保留在上一版本中。"
            type="success"
            :closable="false"
            show-icon
            class="page-alert"
          />

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-title">基本信息</div>
            </template>
            <div class="field-grid">
              <label class="field">
                <span>姓名</span>
                <el-input v-model="form.basic_info.name" placeholder="姓名" />
              </label>
              <label class="field">
                <span>电话</span>
                <el-input v-model="form.basic_info.phone" placeholder="手机号" />
              </label>
              <label class="field">
                <span>邮箱</span>
                <el-input v-model="form.basic_info.email" placeholder="邮箱" />
              </label>
              <label class="field">
                <span>城市</span>
                <el-input v-model="form.basic_info.location" placeholder="城市" />
              </label>
            </div>
            <label class="field">
              <span>一句话标题</span>
              <el-input v-model="form.basic_info.headline" placeholder="例如：后端开发工程师" />
            </label>
            <label class="field">
              <span>个人简介</span>
              <el-input v-model="form.summary" type="textarea" :rows="3" placeholder="原文没有可留空" />
            </label>
            <p v-if="form.basic_info.source_text" class="source-text">
              原文：{{ form.basic_info.source_text }}
            </p>
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">教育经历</span>
                <el-button link type="primary" @click="addEducation">添加一条</el-button>
              </div>
            </template>
            <el-empty
              v-if="!form.education.length"
              :image-size="44"
              description="暂无教育经历"
            />
            <div v-for="(item, index) in form.education" :key="index" class="entry">
              <div class="entry-head">
                <span>教育经历 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.education, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid three">
                <label class="field">
                  <span>学校 *</span>
                  <el-input v-model="item.school" placeholder="学校名称" />
                </label>
                <label class="field">
                  <span>学历</span>
                  <el-input v-model="item.degree" placeholder="本科 / 硕士" />
                </label>
                <label class="field">
                  <span>专业</span>
                  <el-input v-model="item.major" placeholder="专业" />
                </label>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>开始时间</span>
                  <el-input v-model="item.start_date" placeholder="2020.09" />
                </label>
                <label class="field">
                  <span>结束时间</span>
                  <el-input v-model="item.end_date" placeholder="2024.06" />
                </label>
              </div>
              <label class="field">
                <span>在校经历 / 课程（每行一条）</span>
                <LinesEditor v-model="item.details" :rows="3" />
              </label>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">工作经历</span>
                <el-button link type="primary" @click="addWork">添加一条</el-button>
              </div>
            </template>
            <el-empty
              v-if="!form.work_experience.length"
              :image-size="44"
              description="暂无工作经历"
            />
            <div v-for="(item, index) in form.work_experience" :key="index" class="entry">
              <div class="entry-head">
                <span>工作经历 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.work_experience, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>公司 *</span>
                  <el-input v-model="item.company" placeholder="公司名称" />
                </label>
                <label class="field">
                  <span>职位</span>
                  <el-input v-model="item.title" placeholder="职位" />
                </label>
              </div>
              <div class="field-grid three">
                <label class="field">
                  <span>开始时间</span>
                  <el-input v-model="item.start_date" placeholder="2024.07" />
                </label>
                <label class="field">
                  <span>结束时间</span>
                  <el-input v-model="item.end_date" placeholder="至今" />
                </label>
                <label class="field">
                  <span>地点</span>
                  <el-input v-model="item.location" placeholder="杭州" />
                </label>
              </div>
              <label class="field">
                <span>职责 / 成果（每行一条）</span>
                <LinesEditor v-model="item.highlights" :rows="4" />
              </label>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">项目经历</span>
                <el-button link type="primary" @click="addProject">添加一条</el-button>
              </div>
            </template>
            <el-empty v-if="!form.projects.length" :image-size="44" description="暂无项目经历" />
            <div v-for="(item, index) in form.projects" :key="index" class="entry">
              <div class="entry-head">
                <span>项目 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.projects, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>项目名称 *</span>
                  <el-input v-model="item.name" placeholder="项目名称" />
                </label>
                <label class="field">
                  <span>角色</span>
                  <el-input v-model="item.role" placeholder="后端开发 / 负责人" />
                </label>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>开始时间</span>
                  <el-input v-model="item.start_date" placeholder="2025.03" />
                </label>
                <label class="field">
                  <span>结束时间</span>
                  <el-input v-model="item.end_date" placeholder="2025.06" />
                </label>
              </div>
              <label class="field">
                <span>项目描述</span>
                <el-input v-model="item.description" type="textarea" :rows="2" />
              </label>
              <label class="field">
                <span>技术栈（每行一条）</span>
                <LinesEditor v-model="item.tech_stack" :rows="2" />
              </label>
              <label class="field">
                <span>职责 / 成果（每行一条）</span>
                <LinesEditor v-model="item.highlights" :rows="4" />
              </label>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">技能</span>
                <el-button link type="primary" @click="addSkill">添加一组</el-button>
              </div>
            </template>
            <el-empty v-if="!form.skills.length" :image-size="44" description="暂无技能" />
            <div v-for="(item, index) in form.skills" :key="index" class="entry">
              <div class="entry-head">
                <span>技能组 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.skills, index)">
                  删除
                </el-button>
              </div>
              <label class="field">
                <span>分类 *</span>
                <el-input v-model="item.category" placeholder="编程语言 / 框架 / 工具" />
              </label>
              <label class="field">
                <span>技能项（每行一条）</span>
                <LinesEditor v-model="item.items" :rows="3" />
              </label>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">证书与奖项</span>
                <div class="section-actions">
                  <el-button link type="primary" @click="addCertificate">添加证书</el-button>
                  <el-button link type="primary" @click="addAward">添加奖项</el-button>
                </div>
              </div>
            </template>

            <div v-for="(item, index) in form.certificates" :key="`cert-${index}`" class="entry">
              <div class="entry-head">
                <span>证书 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.certificates, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid three">
                <label class="field">
                  <span>名称 *</span>
                  <el-input v-model="item.name" placeholder="CET-6" />
                </label>
                <label class="field">
                  <span>颁发机构</span>
                  <el-input v-model="item.issuer" placeholder="机构" />
                </label>
                <label class="field">
                  <span>日期</span>
                  <el-input v-model="item.date" placeholder="2023.06" />
                </label>
              </div>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>

            <div v-for="(item, index) in form.awards" :key="`award-${index}`" class="entry">
              <div class="entry-head">
                <span>奖项 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.awards, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>名称 *</span>
                  <el-input v-model="item.name" placeholder="奖学金 / 竞赛奖项" />
                </label>
                <label class="field">
                  <span>日期</span>
                  <el-input v-model="item.date" placeholder="2023.10" />
                </label>
              </div>
              <label class="field">
                <span>说明</span>
                <el-input v-model="item.description" type="textarea" :rows="2" />
              </label>
              <p v-if="item.source_text" class="source-text">原文：{{ item.source_text }}</p>
            </div>

            <el-empty
              v-if="!form.certificates.length && !form.awards.length"
              :image-size="44"
              description="暂无证书或奖项"
            />
          </el-card>

          <el-card class="section" shadow="never">
            <template #header>
              <div class="section-head">
                <span class="section-title">语言</span>
                <el-button link type="primary" @click="addLanguage">添加一条</el-button>
              </div>
            </template>
            <el-empty v-if="!form.languages.length" :image-size="44" description="暂无语言信息" />
            <div v-for="(item, index) in form.languages" :key="index" class="entry">
              <div class="entry-head">
                <span>语言 {{ index + 1 }}</span>
                <el-button link type="danger" @click="removeAt(form.languages, index)">
                  删除
                </el-button>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>语言 *</span>
                  <el-input v-model="item.name" placeholder="英语" />
                </label>
                <label class="field">
                  <span>水平</span>
                  <el-input v-model="item.level" placeholder="CET-6 / 流利" />
                </label>
              </div>
            </div>
          </el-card>

          <div class="editor-footer">
            <el-button type="primary" :loading="store.saving" @click="saveCorrection">
              保存为新版本
            </el-button>
            <span>保存后会生成新版本，历史版本不会被覆盖。</span>
          </div>
        </template>

        <el-empty
          v-else
          description="选择左侧版本查看结构化数据，或先执行解析"
        >
          <el-button v-if="canParse" type="primary" :loading="store.parsing" @click="runParse">
            开始解析
          </el-button>
        </el-empty>
      </main>
    </div>
  </div>
</template>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 420px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.head-main h1 {
  margin: 10px 0 8px;
  font-size: 28px;
  letter-spacing: -0.5px;
  color: var(--app-text);
  word-break: break-all;
}

.head-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11.5px;
  color: var(--app-muted);
}

.page-alert {
  border-radius: 10px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.version-panel {
  position: sticky;
  top: 88px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #fff;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text);
}

.panel-title small {
  font-size: 11px;
  font-weight: 400;
  color: var(--app-muted);
}

.version-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 8px;
  width: 100%;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}

.version-item:hover {
  border-color: #bfdbfe;
}

.version-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.version-no {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-primary);
}

.version-item :deep(.el-tag) {
  justify-self: end;
}

.version-meta {
  grid-column: 1 / -1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10.5px;
  color: var(--app-muted);
}

.editor-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: #fff;
}

.editor-toolbar strong {
  font-size: 15px;
  color: var(--app-text);
}

.toolbar-meta {
  margin-left: 10px;
  font-size: 11px;
  color: var(--app-muted);
}

.section {
  border-radius: 14px;
  border-color: var(--app-border);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-actions {
  display: flex;
  gap: 4px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.field-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.field > span {
  font-size: 11.5px;
  color: var(--app-muted);
}

.entry {
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fcfdff;
}

.entry:last-child {
  margin-bottom: 0;
}

.entry-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.source-text {
  margin: 4px 0 0;
  padding: 8px 10px;
  border-left: 3px solid #bfdbfe;
  border-radius: 0 6px 6px 0;
  background: #f8fbff;
  font-size: 11px;
  line-height: 1.7;
  color: #64748b;
  word-break: break-word;
}

.editor-footer {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 4px 0 20px;
}

.editor-footer span {
  font-size: 11px;
  color: var(--app-muted);
}

@media (max-width: 900px) {
  .workspace-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .version-panel {
    position: static;
  }

  .field-grid,
  .field-grid.three {
    grid-template-columns: minmax(0, 1fr);
  }

  .page-head {
    flex-direction: column;
  }
}
</style>
