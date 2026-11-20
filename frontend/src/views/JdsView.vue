<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import LinesEditor from '@/components/LinesEditor.vue'
import { useJdStore } from '@/stores/jds'
import type { JobDescription, JobDescriptionPayload } from '@/types/jd'

interface JdForm {
  title: string
  company: string
  raw_text: string
  required_skills: string[]
  preferred_skills: string[]
  keywords: string[]
  responsibilities: string[]
  qualifications: string[]
}

const store = useJdStore()
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive<JdForm>(emptyForm())

function emptyForm(): JdForm {
  return {
    title: '',
    company: '',
    raw_text: '',
    required_skills: [],
    preferred_skills: [],
    keywords: [],
    responsibilities: [],
    qualifications: [],
  }
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString('zh-CN')
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(jd: JobDescription): void {
  editingId.value = jd.id
  Object.assign(form, {
    title: jd.title,
    company: jd.company ?? '',
    raw_text: jd.raw_text,
    required_skills: [...jd.required_skills],
    preferred_skills: [...jd.preferred_skills],
    keywords: [...jd.keywords],
    responsibilities: [...jd.responsibilities],
    qualifications: [...jd.qualifications],
  })
  dialogVisible.value = true
}

function cleanList(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean)
}

function hasRequirements(value: JdForm): boolean {
  return [value.required_skills, value.preferred_skills, value.keywords, value.qualifications].some(
    (items) => cleanList(items).length > 0,
  )
}

function toPayload(value: JdForm): JobDescriptionPayload {
  return {
    title: value.title.trim(),
    company: value.company.trim() || null,
    raw_text: value.raw_text,
    required_skills: cleanList(value.required_skills),
    preferred_skills: cleanList(value.preferred_skills),
    keywords: cleanList(value.keywords),
    responsibilities: cleanList(value.responsibilities),
    qualifications: cleanList(value.qualifications),
  }
}

async function save(): Promise<void> {
  if (!form.title.trim()) {
    ElMessage.warning('请填写岗位名称')
    return
  }
  if (!hasRequirements(form)) {
    ElMessage.warning('至少填写一项岗位要求：技能、关键词或任职资格')
    return
  }

  try {
    const payload = toPayload(form)
    if (editingId.value) {
      await store.update(editingId.value, payload)
      ElMessage.success('岗位已更新')
    } else {
      await store.create(payload)
      ElMessage.success('岗位已创建')
    }
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '岗位保存失败')
  }
}

async function remove(jd: JobDescription): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除「${jd.title}」？引用它的诊断历史也会被删除。`,
      '删除岗位',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  try {
    await store.remove(jd.id)
    ElMessage.success('岗位已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '岗位删除失败')
  }
}

onMounted(() => {
  void store.load(true)
})
</script>

<template>
  <div class="jds-page">
    <header class="page-head">
      <div>
        <h1>岗位描述</h1>
        <p>
          维护目标岗位的技能、关键词与任职资格。诊断时用这些要求与简历逐条对齐；
          至少填写一项要求，诊断才能运行。
        </p>
      </div>
      <el-button type="primary" @click="openCreate">新建岗位</el-button>
    </header>

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      :closable="false"
      show-icon
    />

    <div v-loading="store.loading" class="jd-grid">
      <el-card v-for="jd in store.items" :key="jd.id" class="jd-card" shadow="never">
        <div class="jd-head">
          <div>
            <h2>{{ jd.title }}</h2>
            <p>{{ jd.company || '未填写公司' }} · {{ formatDate(jd.created_at) }}</p>
          </div>
          <div class="jd-actions">
            <el-button link type="primary" @click="openEdit(jd)">编辑</el-button>
            <el-button link type="danger" @click="remove(jd)">删除</el-button>
          </div>
        </div>

        <div class="tag-group">
          <span class="group-label">必备</span>
          <el-tag
            v-for="skill in jd.required_skills"
            :key="`required-${skill}`"
            size="small"
            type="danger"
            effect="light"
          >
            {{ skill }}
          </el-tag>
          <span v-if="!jd.required_skills.length" class="muted">未填写</span>
        </div>

        <div class="tag-group">
          <span class="group-label">加分</span>
          <el-tag
            v-for="skill in jd.preferred_skills"
            :key="`preferred-${skill}`"
            size="small"
            type="warning"
            effect="light"
          >
            {{ skill }}
          </el-tag>
          <span v-if="!jd.preferred_skills.length" class="muted">未填写</span>
        </div>

        <div class="tag-group">
          <span class="group-label">关键词</span>
          <el-tag
            v-for="keyword in jd.keywords"
            :key="`keyword-${keyword}`"
            size="small"
            type="info"
            effect="plain"
          >
            {{ keyword }}
          </el-tag>
          <span v-if="!jd.keywords.length" class="muted">未填写</span>
        </div>

        <p class="jd-meta">
          任职资格 {{ jd.qualifications.length }} 条 · 职责 {{ jd.responsibilities.length }} 条
        </p>
      </el-card>

      <el-empty
        v-if="!store.loading && !store.items.length"
        description="还没有岗位描述，先新建一个目标岗位"
        class="empty-block"
      >
        <el-button type="primary" @click="openCreate">新建岗位</el-button>
      </el-empty>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑岗位' : '新建岗位'"
      width="min(760px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <div class="field-grid">
          <el-form-item label="岗位名称" required>
            <el-input v-model="form.title" placeholder="例如：后端开发工程师" />
          </el-form-item>
          <el-form-item label="公司">
            <el-input v-model="form.company" placeholder="可选" />
          </el-form-item>
        </div>

        <el-form-item label="岗位原文">
          <el-input
            v-model="form.raw_text"
            type="textarea"
            :rows="5"
            placeholder="粘贴岗位描述原文，方便后续回看；诊断使用下面的结构化要求"
          />
        </el-form-item>

        <el-form-item label="必备技能（每行一条）">
          <LinesEditor v-model="form.required_skills" :rows="3" placeholder="Python&#10;FastAPI" />
        </el-form-item>

        <el-form-item label="加分技能（每行一条）">
          <LinesEditor v-model="form.preferred_skills" :rows="2" placeholder="Docker&#10;Kubernetes" />
        </el-form-item>

        <el-form-item label="关键词（每行一条）">
          <LinesEditor v-model="form.keywords" :rows="2" placeholder="PostgreSQL&#10;微服务" />
        </el-form-item>

        <el-form-item label="任职资格（每行一条）">
          <LinesEditor v-model="form.qualifications" :rows="3" placeholder="本科及以上&#10;3 年以上后端经验" />
        </el-form-item>

        <el-form-item label="岗位职责（每行一条，可选）">
          <LinesEditor v-model="form.responsibilities" :rows="3" placeholder="负责后端服务设计与开发" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.jds-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.page-head h1 {
  margin: 0 0 8px;
  font-size: 30px;
  letter-spacing: -0.5px;
  color: var(--app-text);
}

.page-head p {
  max-width: 700px;
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--app-muted);
}

.jd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  min-height: 180px;
}

.jd-card {
  border-radius: 14px;
  border-color: var(--app-border);
}

.jd-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.jd-head h2 {
  margin: 0 0 4px;
  font-size: 17px;
  color: var(--app-text);
}

.jd-head p {
  margin: 0;
  font-size: 11.5px;
  color: var(--app-muted);
}

.jd-actions {
  display: flex;
  flex: none;
}

.tag-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 9px;
}

.group-label {
  width: 42px;
  flex: none;
  font-size: 11px;
  color: var(--app-muted);
}

.muted {
  font-size: 11px;
  color: #94a3b8;
}

.jd-meta {
  margin: 12px 0 0;
  padding-top: 10px;
  border-top: 1px dashed var(--app-border);
  font-size: 11px;
  color: var(--app-muted);
}

.empty-block {
  grid-column: 1 / -1;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 720px) {
  .page-head {
    flex-direction: column;
  }

  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
