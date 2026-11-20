<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { fetchResumes } from '@/api/resumes'
import { fetchResumeVersions } from '@/api/resumeVersions'
import { useInterviewStore } from '@/stores/interviews'
import { useJdStore } from '@/stores/jds'
import type {
  InterviewStatus,
  InterviewType,
  QuestionSource,
} from '@/types/interview'
import type { ResumeSummary } from '@/types/resume'
import type { ResumeVersionSummary } from '@/types/resumeVersion'

const route = useRoute()
const router = useRouter()
const store = useInterviewStore()
const jdStore = useJdStore()

const resumes = ref<ResumeSummary[]>([])
const versions = ref<ResumeVersionSummary[]>([])
const resumeId = ref('')
const versionNo = ref<number | null>(null)
const jdId = ref('')
const interviewType = ref<InterviewType>('mixed')
const questionCount = ref(8)
const pageLoading = ref(false)

const usableVersions = computed(() =>
  versions.value.filter((version) => version.status !== 'failed'),
)
const canCreate = computed(
  () =>
    Boolean(resumeId.value && versionNo.value) &&
    (interviewType.value !== 'jd' || Boolean(jdId.value)),
)

const TYPE_LABELS: Record<InterviewType, string> = {
  mixed: '综合面试',
  resume: '简历深挖',
  jd: '岗位匹配',
  behavioral: '行为面试',
}

const STATUS_META: Record<
  InterviewStatus,
  { label: string; type: 'info' | 'warning' | 'success' }
> = {
  ready: { label: '待开始', type: 'info' },
  in_progress: { label: '进行中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
}

const SOURCE_LABELS: Record<QuestionSource, string> = {
  resume: '简历',
  jd: '岗位',
  behavioral: '行为题',
}

function statusMeta(status: InterviewStatus): { label: string; type: 'info' | 'warning' | 'success' } {
  return STATUS_META[status] ?? { label: status, type: 'info' }
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

async function loadVersions(): Promise<void> {
  versionNo.value = null
  versions.value = []
  if (!resumeId.value) return
  try {
    versions.value = await fetchResumeVersions(resumeId.value)
    versionNo.value = usableVersions.value[0]?.version_no ?? null
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '简历版本加载失败')
  }
}

async function load(): Promise<void> {
  pageLoading.value = true
  try {
    const [resumeList] = await Promise.all([fetchResumes(), jdStore.load(true)])
    resumes.value = resumeList
    const queryResume = typeof route.query.resume_id === 'string' ? route.query.resume_id : ''
    resumeId.value =
      resumeList.find((item) => item.id === queryResume)?.id ?? resumeList[0]?.id ?? ''
    jdId.value = jdStore.items[0]?.id ?? ''
    await loadVersions()
    await store.load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '面试页面加载失败')
  } finally {
    pageLoading.value = false
  }
}

async function startInterview(): Promise<void> {
  if (!canCreate.value || !versionNo.value) {
    ElMessage.warning('请先选择简历版本；岗位匹配面试还需要选择目标岗位')
    return
  }
  try {
    const detail = await store.create({
      resume_id: resumeId.value,
      resume_version_no: versionNo.value,
      jd_id: jdId.value || null,
      interview_type: interviewType.value,
      question_count: questionCount.value,
    })
    ElMessage.success(`已生成 ${detail.question_count} 道面试题`)
    await router.push({ name: 'interview-room', params: { id: detail.id } })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '面试创建失败')
  }
}

function openInterview(interviewId: string): void {
  void router.push({ name: 'interview-room', params: { id: interviewId } })
}

function goResumes(): void {
  void router.push({ name: 'resumes' })
}

function goJds(): void {
  void router.push({ name: 'jds' })
}

watch(resumeId, () => {
  void loadVersions()
})

onMounted(() => {
  void load()
})
</script>

<template>
  <div v-loading="pageLoading" class="interviews-page">
    <header class="page-head">
      <h1>模拟面试</h1>
      <p>
        由简历与目标岗位驱动出题，逐题给出五维评价，并支持最多两级追问；结束后生成复盘报告。
      </p>
    </header>

    <el-alert
      v-if="!resumes.length"
      title="还没有简历。请先上传并完成结构化解析，再开始模拟面试。"
      type="warning"
      :closable="false"
      show-icon
    >
      <el-button link type="primary" @click="goResumes">去上传简历</el-button>
    </el-alert>

    <el-alert
      v-else-if="!usableVersions.length"
      title="当前简历还没有可用的结构化版本。请先在结构化编辑页完成解析或人工校正。"
      type="warning"
      :closable="false"
      show-icon
    >
      <el-button
        link
        type="primary"
        @click="router.push({ name: 'resume-workspace', params: { id: resumeId } })"
      >
        去结构化编辑
      </el-button>
    </el-alert>

    <el-card class="control-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>新建面试</span>
          <small>出题与评价会调用 DeepSeek，按实际用量计费</small>
        </div>
      </template>

      <div class="control-grid">
        <label class="control-field">
          <span>简历</span>
          <el-select v-model="resumeId" placeholder="选择简历" style="width: 100%">
            <el-option
              v-for="item in resumes"
              :key="item.id"
              :value="item.id"
              :label="item.original_filename"
            />
          </el-select>
        </label>

        <label class="control-field">
          <span>结构化版本</span>
          <el-select v-model="versionNo" placeholder="选择版本" style="width: 100%">
            <el-option
              v-for="version in usableVersions"
              :key="version.version_no"
              :value="version.version_no"
              :label="`v${version.version_no} · ${version.status === 'corrected' ? '人工校正' : '模型解析'}`"
            />
          </el-select>
        </label>

        <label class="control-field">
          <span>目标岗位（可选）</span>
          <el-select v-model="jdId" clearable placeholder="不指定岗位" style="width: 100%">
            <el-option
              v-for="jd in jdStore.items"
              :key="jd.id"
              :value="jd.id"
              :label="`${jd.title}${jd.company ? ' · ' + jd.company : ''}`"
            />
          </el-select>
        </label>

        <label class="control-field">
          <span>面试类型</span>
          <el-radio-group v-model="interviewType">
            <el-radio-button
              v-for="(label, value) in TYPE_LABELS"
              :key="value"
              :value="value"
            >
              {{ label }}
            </el-radio-button>
          </el-radio-group>
        </label>

        <label class="control-field">
          <span>主问题数量</span>
          <el-input-number v-model="questionCount" :min="3" :max="12" />
        </label>

        <el-button
          type="primary"
          size="large"
          :disabled="!canCreate"
          :loading="store.creating"
          @click="startInterview"
        >
          生成面试题
        </el-button>
      </div>

      <p class="control-note">
        追问不计入主问题数量，最多两级；题目必须标记来源，来源无法核实的题目会降级为通用行为题。
        <el-button v-if="!jdStore.items.length" link type="primary" @click="goJds">
          去创建岗位
        </el-button>
      </p>
    </el-card>

    <el-card class="history-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>面试记录</span>
          <small>{{ store.items.length }} 场</small>
        </div>
      </template>

      <el-table v-if="store.items.length" :data="store.items" size="small">
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="resume_filename" label="简历" min-width="160" />
        <el-table-column label="岗位" min-width="140">
          <template #default="{ row }">{{ row.jd_title || '未指定' }}</template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            {{ TYPE_LABELS[row.interview_type as InterviewType] }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="statusMeta(row.status).type" effect="light">
              {{ statusMeta(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="100">
          <template #default="{ row }">{{ row.answered_count }} / {{ row.question_count }}</template>
        </el-table-column>
        <el-table-column label="总分" width="80">
          <template #default="{ row }">
            <strong v-if="row.total_score !== null">{{ row.total_score.toFixed(1) }}</strong>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="openInterview(row.id)">
              {{ row.status === 'completed' ? '查看' : '继续' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :image-size="48" description="还没有面试记录" />
    </el-card>

    <el-card class="tips-card" shadow="never">
      <template #header>
        <div class="card-head"><span>面试评分口径</span></div>
      </template>
      <div class="tips-grid">
        <div>
          <strong>五维评价</strong>
          <p>相关性、专业正确性、结构、证据、表达，各 0—100 分，等权平均为单题得分。</p>
        </div>
        <div>
          <strong>总分</strong>
          <p>所有已作答题目的算术平均，包含追问；未作答题目不计入。</p>
        </div>
        <div>
          <strong>来源标记</strong>
          <p>
            每题标记{{ SOURCE_LABELS.resume }}条目、{{ SOURCE_LABELS.jd }}要求或通用行为题，便于核对题目是否有事实依据。
          </p>
        </div>
        <div>
          <strong>报告</strong>
          <p>结束面试后生成，包含整体总结、优势、短板、改进建议与逐题点评。</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.interviews-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head h1 {
  margin: 10px 0 6px;
  font-size: 30px;
  letter-spacing: -0.5px;
  color: var(--app-text);
}

.page-head p {
  margin: 0;
  max-width: 720px;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--app-muted);
}

.control-card,
.history-card,
.tips-card {
  border-radius: 14px;
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

.card-head small {
  font-size: 11px;
  font-weight: 400;
  color: var(--app-muted);
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 14px;
  align-items: end;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-field > span {
  font-size: 11.5px;
  color: var(--app-muted);
}

.control-note {
  margin: 14px 0 0;
  font-size: 11.5px;
  line-height: 1.7;
  color: #94a3b8;
}

.muted {
  color: #94a3b8;
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.tips-grid strong {
  font-size: 12.5px;
  color: #334155;
}

.tips-grid p {
  margin: 4px 0 0;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--app-muted);
}

@media (max-width: 900px) {
  .control-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .tips-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
