<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import DiagnosisRadar from '@/components/DiagnosisRadar.vue'
import FlowGuide from '@/components/FlowGuide.vue'
import { fetchResume } from '@/api/resumes'
import { fetchResumeVersions } from '@/api/resumeVersions'
import { useDiagnosisStore } from '@/stores/diagnoses'
import { useJdStore } from '@/stores/jds'
import type {
  CheckStatus,
  DimensionKey,
  SuggestionStatus,
  Verdict,
} from '@/types/diagnosis'
import type { ResumeDetail } from '@/types/resume'
import type { ResumeVersionSummary } from '@/types/resumeVersion'

const route = useRoute()
const router = useRouter()
const jdStore = useJdStore()
const diagnosisStore = useDiagnosisStore()

const resume = ref<ResumeDetail | null>(null)
const versions = ref<ResumeVersionSummary[]>([])
const selectedVersion = ref<number | null>(null)
const selectedJd = ref('')
const pageLoading = ref(false)

const resumeId = computed(() => String(route.params.id))
const current = computed(() => diagnosisStore.current)
const usableVersions = computed(() =>
  versions.value.filter((version) => version.status !== 'failed'),
)
const canRun = computed(() => Boolean(selectedVersion.value && selectedJd.value))

const DIMENSION_LABELS: Record<DimensionKey, string> = {
  format: '格式规范',
  completeness: '内容完整',
  keyword: '关键词',
  jd_match: '岗位匹配',
}

const VERDICT_META: Record<
  Verdict,
  { label: string; type: 'success' | 'warning' | 'danger' }
> = {
  met: { label: '满足', type: 'success' },
  partial: { label: '部分', type: 'warning' },
  missing: { label: '缺失', type: 'danger' },
}

const CHECK_META: Record<
  CheckStatus,
  { label: string; type: 'success' | 'warning' | 'danger' }
> = {
  pass: { label: '通过', type: 'success' },
  partial: { label: '部分', type: 'warning' },
  fail: { label: '缺失', type: 'danger' },
}

const SUGGESTION_META: Record<
  SuggestionStatus,
  { label: string; type: 'success' | 'warning' | 'danger' | 'info' }
> = {
  supported: { label: '可直接参考', type: 'success' },
  needs_user_input: { label: '需补充事实', type: 'warning' },
  needs_review: { label: '需人工核对', type: 'danger' },
}

function dimensionLabel(dimension: DimensionKey): string {
  return DIMENSION_LABELS[dimension] ?? dimension
}

function verdictMeta(verdict: Verdict): {
  label: string
  type: 'success' | 'warning' | 'danger' | 'info'
} {
  return VERDICT_META[verdict] ?? { label: verdict, type: 'info' }
}

function checkMeta(status: CheckStatus): {
  label: string
  type: 'success' | 'warning' | 'danger' | 'info'
} {
  return CHECK_META[status] ?? { label: status, type: 'info' }
}

function suggestionMeta(status: SuggestionStatus): {
  label: string
  type: 'success' | 'warning' | 'danger' | 'info'
} {
  return SUGGESTION_META[status] ?? { label: status, type: 'info' }
}

function scoreLevel(score: number): string {
  if (score >= 80) return 'good'
  if (score >= 60) return 'mid'
  return 'low'
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

async function load(): Promise<void> {
  pageLoading.value = true
  diagnosisStore.reset()
  try {
    resume.value = await fetchResume(resumeId.value)
    await jdStore.load(true)
    versions.value = await fetchResumeVersions(resumeId.value)
    selectedVersion.value = usableVersions.value[0]?.version_no ?? null
    selectedJd.value = jdStore.items[0]?.id ?? ''
    await diagnosisStore.loadHistory(resumeId.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '诊断页面加载失败')
  } finally {
    pageLoading.value = false
  }
}

async function runDiagnosis(): Promise<void> {
  if (!selectedVersion.value || !selectedJd.value) {
    ElMessage.warning('请先选择简历版本和目标岗位')
    return
  }

  try {
    const detail = await diagnosisStore.create({
      resume_id: resumeId.value,
      resume_version_no: selectedVersion.value,
      jd_id: selectedJd.value,
    })
    ElMessage.success(`诊断完成，总分 ${detail.total_score.toFixed(2)}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '诊断失败')
  }
}

async function selectDiagnosis(diagnosisId: string): Promise<void> {
  try {
    await diagnosisStore.select(diagnosisId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '诊断详情加载失败')
  }
}

function goWorkspace(): void {
  void router.push({ name: 'resume-workspace', params: { id: resumeId.value } })
}

function goInterview(): void {
  void router.push({
    name: 'interviews',
    query: { resume_id: resumeId.value, jd_id: selectedJd.value },
  })
}

function goJds(): void {
  void router.push({ name: 'jds' })
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div v-loading="pageLoading" class="diagnosis-page">
    <header class="page-head">
      <div>
        <el-button link type="primary" @click="goWorkspace">← 返回结构化编辑</el-button>
        <h1>四维诊断</h1>
        <p v-if="resume">{{ resume.original_filename }} · {{ resume.text_length }} 字</p>
      </div>
    </header>

    <FlowGuide current="diagnosis" />

    <el-alert
      v-if="!usableVersions.length"
      title="还没有可诊断的结构化版本。请先回到结构化编辑页完成解析或校正。"
      type="warning"
      :closable="false"
      show-icon
    >
      <el-button link type="primary" @click="goWorkspace">去结构化编辑</el-button>
    </el-alert>

    <el-alert
      v-else-if="!jdStore.items.length"
      title="还没有岗位描述。先创建目标岗位，诊断需要技能、关键词或任职资格。"
      type="warning"
      :closable="false"
      show-icon
    >
      <el-button link type="primary" @click="goJds">去创建岗位</el-button>
    </el-alert>

    <el-card class="control-card" shadow="never">
      <div class="control-grid">
        <label class="control-field">
          <span>简历版本</span>
          <el-select v-model="selectedVersion" placeholder="选择版本" style="width: 100%">
            <el-option
              v-for="version in usableVersions"
              :key="version.version_no"
              :value="version.version_no"
              :label="`v${version.version_no} · ${version.status === 'corrected' ? '人工校正' : 'AI 解析'}`"
            />
          </el-select>
        </label>

        <label class="control-field">
          <span>目标岗位</span>
          <el-select v-model="selectedJd" placeholder="选择岗位" style="width: 100%">
            <el-option
              v-for="jd in jdStore.items"
              :key="jd.id"
              :value="jd.id"
              :label="`${jd.title}${jd.company ? ' · ' + jd.company : ''}`"
            />
          </el-select>
        </label>

        <el-button
          type="primary"
          size="large"
          :disabled="!canRun"
          :loading="diagnosisStore.creating"
          @click="runDiagnosis"
        >
          开始诊断
        </el-button>
      </div>
      <p class="control-note">
        四个维度综合评分，每条结论都附简历原文证据与可执行的修改示例。
      </p>
    </el-card>

    <template v-if="current">
      <el-card class="overview-card" shadow="never">
        <div class="overview-grid">
          <div class="total-panel">
            <div class="total-score" :class="scoreLevel(current.total_score)">
              {{ current.total_score.toFixed(1) }}
              <small>/ 100</small>
            </div>
            <p class="summary-text">{{ current.summary }}</p>
            <p class="overview-meta">生成于 {{ formatDate(current.created_at) }}</p>
          </div>

          <div class="score-panel">
            <div class="score-card">
              <span>格式规范</span>
              <strong :class="scoreLevel(current.format_score)">{{ current.format_score }}</strong>
              <small>占比 15%</small>
            </div>
            <div class="score-card">
              <span>内容完整</span>
              <strong :class="scoreLevel(current.completeness_score)">{{ current.completeness_score }}</strong>
              <small>占比 20%</small>
            </div>
            <div class="score-card">
              <span>关键词</span>
              <strong :class="scoreLevel(current.keyword_score)">{{ current.keyword_score }}</strong>
              <small>占比 25%</small>
            </div>
            <div class="score-card">
              <span>岗位匹配</span>
              <strong :class="scoreLevel(current.jd_match_score)">{{ current.jd_match_score }}</strong>
              <small>占比 40%</small>
            </div>
          </div>

          <DiagnosisRadar
            class="radar-panel"
            :scores="{
              format: current.format_score,
              completeness: current.completeness_score,
              keyword: current.keyword_score,
              jd_match: current.jd_match_score,
            }"
          />
        </div>
      </el-card>

      <el-card class="detail-card" shadow="never">
        <el-tabs>
          <el-tab-pane label="维度明细">
            <div class="dimension-grid">
              <section>
                <h3>格式规范 · {{ current.format_score }}/100</h3>
                <div v-for="check in current.format_details" :key="check.name" class="check-row">
                  <div class="check-main">
                    <strong>{{ check.label }}</strong>
                    <p>{{ check.message }}</p>
                  </div>
                  <span class="check-score">{{ check.score }}/{{ check.max_score }}</span>
                  <el-tag size="small" :type="checkMeta(check.status).type" effect="light">
                    {{ checkMeta(check.status).label }}
                  </el-tag>
                </div>
              </section>

              <section>
                <h3>内容完整 · {{ current.completeness_score }}/100</h3>
                <div
                  v-for="check in current.completeness_details"
                  :key="check.name"
                  class="check-row"
                >
                  <div class="check-main">
                    <strong>{{ check.label }}</strong>
                    <p>{{ check.message }}</p>
                  </div>
                  <span class="check-score">{{ check.score }}/{{ check.max_score }}</span>
                  <el-tag size="small" :type="checkMeta(check.status).type" effect="light">
                    {{ checkMeta(check.status).label }}
                  </el-tag>
                </div>
              </section>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`关键词 ${current.keyword_details.score}`">
            <div class="keyword-head">
              <span>
                命中 {{ current.keyword_details.matched_count }} /
                {{ current.keyword_details.total_count }}
              </span>
              <span>
                加权 {{ current.keyword_details.matched_weight }} /
                {{ current.keyword_details.total_weight }}
              </span>
            </div>
            <div class="keyword-groups">
              <div class="keyword-group">
                <h4>已命中</h4>
                <div class="tag-list">
                  <el-tag
                    v-for="hit in current.keyword_details.hits.filter((item) => item.matched)"
                    :key="hit.keyword"
                    type="success"
                    effect="light"
                  >
                    {{ hit.keyword }}
                  </el-tag>
                  <span
                    v-if="!current.keyword_details.hits.some((item) => item.matched)"
                    class="muted"
                  >
                    暂无命中
                  </span>
                </div>
              </div>
              <div class="keyword-group">
                <h4>未命中</h4>
                <div class="tag-list">
                  <el-tag
                    v-for="hit in current.keyword_details.hits.filter((item) => !item.matched)"
                    :key="hit.keyword"
                    type="danger"
                    effect="plain"
                  >
                    {{ hit.keyword }}
                  </el-tag>
                  <span
                    v-if="!current.keyword_details.hits.some((item) => !item.matched)"
                    class="muted"
                  >
                    全部命中
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`岗位匹配 ${current.jd_match_details.score}`">
            <el-table :data="current.jd_match_details.matches" size="small">
              <el-table-column prop="requirement" label="岗位要求" min-width="150" />
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  {{ row.source === 'required' ? '必备' : '加分' }}
                </template>
              </el-table-column>
              <el-table-column label="判定" width="86">
                <template #default="{ row }">
                  <el-tag size="small" :type="verdictMeta(row.verdict).type" effect="light">
                    {{ verdictMeta(row.verdict).label }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="evidence" label="简历证据" min-width="220">
                <template #default="{ row }">{{ row.evidence || '—' }}</template>
              </el-table-column>
              <el-table-column prop="reason" label="理由" min-width="180" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`修改示例 ${current.suggestions.length}`">
            <el-empty
              v-if="!current.suggestions.length"
              :image-size="48"
              description="本次没有生成修改示例"
            />
            <div
              v-for="(suggestion, index) in current.suggestions"
              :key="index"
              class="suggestion-card"
            >
              <div class="suggestion-head">
                <el-tag size="small" effect="plain">
                  {{ dimensionLabel(suggestion.dimension) }}
                </el-tag>
                <el-tag
                  size="small"
                  :type="suggestionMeta(suggestion.fact_status).type"
                  effect="light"
                >
                  {{ suggestionMeta(suggestion.fact_status).label }}
                </el-tag>
              </div>
              <div class="suggestion-block">
                <span>原文</span>
                <p>{{ suggestion.original_text || '（未找到原文）' }}</p>
              </div>
              <div class="suggestion-block">
                <span>问题</span>
                <p>{{ suggestion.issue }}</p>
              </div>
              <div class="suggestion-block">
                <span>建议</span>
                <p>{{ suggestion.suggestion }}</p>
              </div>
              <div class="suggestion-block">
                <span>改写示例</span>
                <p>{{ suggestion.rewritten_example || '—' }}</p>
              </div>
              <div class="suggestion-block">
                <span>理由</span>
                <p>{{ suggestion.reason }}</p>
              </div>
              <el-alert
                v-if="suggestion.missing_facts.length"
                :title="`需要补充：${suggestion.missing_facts.join('、')}`"
                type="warning"
                :closable="false"
                show-icon
                class="suggestion-alert"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>

    <el-empty v-else description="选择版本和岗位后开始诊断">
      <el-button v-if="canRun" type="primary" :loading="diagnosisStore.creating" @click="runDiagnosis">
        开始诊断
      </el-button>
    </el-empty>

    <el-card v-if="current && selectedJd" class="next-card" shadow="never">
      <div class="next-copy">
        <strong>下一步：用这份简历和目标岗位练一场面试</strong>
        <p>题目会结合简历证据与岗位要求，逐题给出评价和追问。</p>
      </div>
      <el-button type="primary" @click="goInterview">开始模拟面试</el-button>
    </el-card>

    <el-card class="history-card" shadow="never">
      <template #header>
        <div class="history-head">
          <span>诊断历史</span>
          <small>{{ diagnosisStore.history.length }} 条</small>
        </div>
      </template>
      <el-table
        v-if="diagnosisStore.history.length"
        :data="diagnosisStore.history"
        size="small"
      >
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="resume_filename" label="简历" min-width="160" />
        <el-table-column prop="jd_title" label="岗位" min-width="160" />
        <el-table-column label="版本" width="80">
          <template #default="{ row }">v{{ row.resume_version_no }}</template>
        </el-table-column>
        <el-table-column label="总分" width="90">
          <template #default="{ row }">
            <strong :class="scoreLevel(row.total_score)">{{ row.total_score.toFixed(1) }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="selectDiagnosis(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :image-size="48" description="还没有诊断记录" />
    </el-card>
  </div>
</template>

<style scoped>
.next-card {
  border-radius: 14px;
  border-color: var(--app-border);
}

.next-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.next-copy strong {
  display: block;
  font-size: 14px;
  color: var(--app-text);
}

.next-copy p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-muted);
}

.diagnosis-page {
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
  font-size: 12px;
  color: var(--app-muted);
}

.control-card,
.overview-card,
.detail-card,
.history-card {
  border-radius: 14px;
  border-color: var(--app-border);
}

.control-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
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
  font-size: 11px;
  color: #94a3b8;
}

.overview-grid {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 22px;
  align-items: center;
}

.radar-panel {
  grid-column: 1 / -1;
}

.total-panel {
  border-right: 1px dashed var(--app-border);
  padding-right: 20px;
}

.total-score {
  font-size: 52px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -2px;
}

.total-score small {
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--app-muted);
}

.total-score.good,
.score-card strong.good,
.history-card strong.good {
  color: #16a34a;
}

.total-score.mid,
.score-card strong.mid,
.history-card strong.mid {
  color: #d97706;
}

.total-score.low,
.score-card strong.low,
.history-card strong.low {
  color: #dc2626;
}

.summary-text {
  margin: 14px 0 8px;
  font-size: 12px;
  line-height: 1.75;
  color: #475569;
}

.overview-meta {
  margin: 0;
  font-size: 10.5px;
  color: #94a3b8;
  word-break: break-all;
}

.score-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.score-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.score-card span {
  font-size: 11.5px;
  color: var(--app-muted);
}

.score-card strong {
  font-size: 24px;
  line-height: 1.1;
}

.score-card small {
  font-size: 10px;
  color: #94a3b8;
}

.dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.dimension-grid h3 {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--app-text);
}

.check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.check-main {
  flex: 1;
  min-width: 0;
}

.check-main strong {
  font-size: 12.5px;
  color: #334155;
}

.check-main p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--app-muted);
}

.check-score {
  flex: none;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.keyword-head {
  display: flex;
  gap: 20px;
  margin-bottom: 14px;
  font-size: 12px;
  color: var(--app-muted);
}

.keyword-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.keyword-group h4 {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: #475569;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  font-size: 11px;
  color: #94a3b8;
}

.suggestion-card {
  padding: 16px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fcfdff;
}

.suggestion-head {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.suggestion-block {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 8px;
}

.suggestion-block > span {
  font-size: 11px;
  color: #94a3b8;
}

.suggestion-block p {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: #334155;
  word-break: break-word;
}

.suggestion-alert {
  margin-top: 10px;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text);
}

.history-head small {
  font-size: 11px;
  font-weight: 400;
  color: var(--app-muted);
}

@media (max-width: 900px) {
  .overview-grid,
  .dimension-grid,
  .keyword-groups {
    grid-template-columns: minmax(0, 1fr);
  }

  .total-panel {
    border-right: 0;
    border-bottom: 1px dashed var(--app-border);
    padding: 0 0 16px;
  }

  .control-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
