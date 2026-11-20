<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import TrendLineChart from '@/components/TrendLineChart.vue'
import { fetchResumes } from '@/api/resumes'
import { useAnalyticsStore } from '@/stores/analytics'
import type { InterviewTrendGroup } from '@/types/analytics'
import type { InterviewType } from '@/types/interview'
import type { ResumeSummary } from '@/types/resume'

const store = useAnalyticsStore()
const router = useRouter()

const resumes = ref<ResumeSummary[]>([])
const resumeFilter = ref('')
const pageLoading = ref(false)
const diagnosisIndex = ref(0)
const interviewIndex = ref(0)

const TYPE_LABELS: Record<InterviewType, string> = {
  mixed: '综合面试',
  resume: '简历深挖',
  jd: '岗位匹配',
  behavioral: '行为面试',
}

const INTERVIEW_DIMENSIONS = [
  { key: 'relevance', label: '相关性', color: '#2563eb' },
  { key: 'correctness', label: '专业正确性', color: '#10b981' },
  { key: 'structure', label: '结构', color: '#f59e0b' },
  { key: 'evidence', label: '证据', color: '#ef4444' },
  { key: 'expression', label: '表达', color: '#8b5cf6' },
]

const selectedDiagnosis = computed(
  () => store.diagnosisGroups[diagnosisIndex.value] ?? null,
)
const selectedInterview = computed(
  () => store.interviewGroups[interviewIndex.value] ?? null,
)

const diagnosisLabels = computed(() =>
  (selectedDiagnosis.value?.points ?? []).map(
    (point) => `${formatShort(point.created_at)} · v${point.resume_version_no}`,
  ),
)

const diagnosisSeries = computed(() => {
  const group = selectedDiagnosis.value
  if (!group) return []
  return [
    { name: '总分', data: group.points.map((point) => point.total_score), color: '#2563eb' },
    { name: '格式', data: group.points.map((point) => point.format_score), color: '#60a5fa' },
    {
      name: '完整度',
      data: group.points.map((point) => point.completeness_score),
      color: '#34d399',
    },
    { name: '关键词', data: group.points.map((point) => point.keyword_score), color: '#fbbf24' },
    {
      name: '岗位匹配',
      data: group.points.map((point) => point.jd_match_score),
      color: '#8b5cf6',
    },
  ]
})

const interviewLabels = computed(() =>
  (selectedInterview.value?.points ?? []).map(
    (point) => `${formatShort(point.created_at)} · v${point.resume_version_no}`,
  ),
)

const interviewSeries = computed(() => {
  const group = selectedInterview.value
  if (!group) return []
  return [
    {
      name: '总分',
      data: group.points.map((point) => point.total_score),
      color: '#2563eb',
    },
    ...INTERVIEW_DIMENSIONS.map((dimension) => ({
      name: dimension.label,
      data: group.points.map((point) => point.dimension_scores[dimension.key] ?? 0),
      color: dimension.color,
    })),
  ]
})

const hasWeakness = computed(() => {
  const report = store.weaknesses
  if (!report) return false
  return Boolean(
    report.missing_keywords.length ||
      report.missing_requirements.length ||
      report.interview_dimensions.length,
  )
})

const lowestDimension = computed(() => {
  const key = store.weaknesses?.lowest_dimension
  if (!key) return null
  return store.weaknesses?.interview_dimensions.find((item) => item.key === key) ?? null
})

function formatShort(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

function scoreLevel(score: number | null | undefined): string {
  if (score === null || score === undefined) return ''
  if (score >= 80) return 'good'
  if (score >= 60) return 'mid'
  return 'low'
}

function improvementText(value: number): string {
  if (value > 0) return `+${value.toFixed(1)}`
  return value.toFixed(1)
}

function changeText(group: InterviewTrendGroup, key: string): string {
  const value = group.dimension_changes[key]
  return value === undefined ? '—' : improvementText(value)
}

function changeLevel(group: InterviewTrendGroup, key: string): string {
  const value = group.dimension_changes[key]
  if (value === undefined) return ''
  return value >= 0 ? 'good' : 'low'
}

async function load(): Promise<void> {
  pageLoading.value = true
  try {
    if (!resumes.value.length) {
      resumes.value = await fetchResumes()
    }
    await store.load(resumeFilter.value || undefined)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '成长数据加载失败')
  } finally {
    pageLoading.value = false
  }
}

function goResumes(): void {
  void router.push({ name: 'resumes' })
}

function goDiagnosis(): void {
  if (selectedDiagnosis.value) {
    void router.push({
      name: 'diagnosis',
      params: { id: selectedDiagnosis.value.resume_id },
    })
  }
}

function goInterviews(): void {
  void router.push({ name: 'interviews' })
}

watch(resumeFilter, () => {
  void load()
})

watch(
  () => store.diagnosisGroups.length,
  () => {
    diagnosisIndex.value = 0
  },
)

watch(
  () => store.interviewGroups.length,
  () => {
    interviewIndex.value = 0
  },
)

onMounted(() => {
  void load()
})
</script>

<template>
  <div v-loading="pageLoading" class="growth-page">
    <header class="page-head">
      <h1>成长分析</h1>
      <p>
        按简历与岗位聚合历史诊断和面试，查看分数趋势与重复出现的弱项。
        只有同一份简历、同一个岗位的记录才会放在一起比较。
      </p>
    </header>

    <el-card class="filter-card" shadow="never">
      <div class="filter-row">
        <label class="filter-field">
          <span>简历范围</span>
          <el-select v-model="resumeFilter" clearable placeholder="全部简历" style="width: 260px">
            <el-option label="全部简历" value="" />
            <el-option
              v-for="item in resumes"
              :key="item.id"
              :value="item.id"
              :label="item.original_filename"
            />
          </el-select>
        </label>
        <el-button :loading="store.loading" @click="load">刷新数据</el-button>
        <span class="filter-note">
          趋势只在同一份简历、同一个岗位下比较；面试还要求同一种面试类型。
        </span>
      </div>
    </el-card>

    <section v-if="store.overview" class="stat-grid">
      <div class="stat-card">
        <span>简历</span>
        <strong>{{ store.overview.resume_count }}</strong>
        <small>已上传</small>
      </div>
      <div class="stat-card">
        <span>诊断</span>
        <strong>{{ store.overview.diagnosis_count }}</strong>
        <small>
          最近
          <b :class="scoreLevel(store.overview.latest_diagnosis?.total_score)">
            {{ store.overview.latest_diagnosis?.total_score?.toFixed(1) ?? '—' }}
          </b>
        </small>
      </div>
      <div class="stat-card">
        <span>面试</span>
        <strong>{{ store.overview.completed_interview_count }}</strong>
        <small>已完成 / 共 {{ store.overview.interview_count }} 场</small>
      </div>
      <div class="stat-card">
        <span>最近面试总分</span>
        <strong :class="scoreLevel(store.overview.latest_interview?.total_score)">
          {{ store.overview.latest_interview?.total_score?.toFixed(1) ?? '—' }}
        </strong>
        <small>{{ store.overview.latest_interview?.jd_title || '未指定岗位' }}</small>
      </div>
    </section>

    <el-card class="trend-card" shadow="never">
      <template #header>
        <div class="card-head">
          <div class="card-title">
            <span>诊断趋势</span>
            <small v-if="store.diagnosisGroups.length">
              {{ store.diagnosisGroups.length }} 组记录
            </small>
          </div>
          <div class="card-actions">
            <el-select
              v-if="store.diagnosisGroups.length > 1"
              v-model="diagnosisIndex"
              size="small"
              style="width: 260px"
            >
              <el-option
                v-for="(group, index) in store.diagnosisGroups"
                :key="`${group.jd_id}-${group.rubric_version}`"
                :value="index"
                :label="`${group.jd_title} · ${group.points.length} 次记录`"
              />
            </el-select>
            <el-button v-if="selectedDiagnosis" link type="primary" @click="goDiagnosis">
              查看诊断
            </el-button>
          </div>
        </div>
      </template>

      <template v-if="selectedDiagnosis">
        <div class="group-meta">
          <span>{{ selectedDiagnosis.resume_filename }}</span>
          <span>{{ selectedDiagnosis.jd_title }}</span>
          <span>{{ selectedDiagnosis.points.length }} 次记录</span>
        </div>

        <div class="metric-row">
          <div class="metric">
            <span>平均总分</span>
            <strong>{{ selectedDiagnosis.average_total.toFixed(1) }}</strong>
          </div>
          <div class="metric">
            <span>最高总分</span>
            <strong class="good">{{ selectedDiagnosis.best_total.toFixed(1) }}</strong>
          </div>
          <div class="metric">
            <span>首末变化</span>
            <strong :class="selectedDiagnosis.improvement >= 0 ? 'good' : 'low'">
              {{ improvementText(selectedDiagnosis.improvement) }}
            </strong>
          </div>
        </div>

        <TrendLineChart :labels="diagnosisLabels" :series="diagnosisSeries" :height="300" />

        <el-table :data="selectedDiagnosis.points" size="small" class="point-table">
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="版本" width="70">
            <template #default="{ row }">v{{ row.resume_version_no }}</template>
          </el-table-column>
          <el-table-column label="总分" width="80">
            <template #default="{ row }">
              <strong :class="scoreLevel(row.total_score)">{{ row.total_score.toFixed(1) }}</strong>
            </template>
          </el-table-column>
          <el-table-column prop="format_score" label="格式" width="70" />
          <el-table-column prop="completeness_score" label="完整度" width="80" />
          <el-table-column prop="keyword_score" label="关键词" width="80" />
          <el-table-column prop="jd_match_score" label="岗位匹配" width="90" />
        </el-table>
      </template>

      <el-empty v-else :image-size="56" description="还没有可对比的诊断记录">
        <el-button type="primary" @click="goResumes">去诊断一份简历</el-button>
      </el-empty>
    </el-card>

    <el-card class="trend-card" shadow="never">
      <template #header>
        <div class="card-head">
          <div class="card-title">
            <span>面试趋势</span>
            <small v-if="store.interviewGroups.length">
              {{ store.interviewGroups.length }} 组记录
            </small>
          </div>
          <div class="card-actions">
            <el-select
              v-if="store.interviewGroups.length > 1"
              v-model="interviewIndex"
              size="small"
              style="width: 280px"
            >
              <el-option
                v-for="(group, index) in store.interviewGroups"
                :key="`${group.jd_id}-${group.interview_type}-${group.rubric_version}`"
                :value="index"
                :label="`${group.jd_title || '未指定岗位'} · ${TYPE_LABELS[group.interview_type as InterviewType] || group.interview_type}`"
              />
            </el-select>
            <el-button link type="primary" @click="goInterviews">去面试</el-button>
          </div>
        </div>
      </template>

      <template v-if="selectedInterview">
        <div class="group-meta">
          <span>{{ selectedInterview.resume_filename }}</span>
          <span>{{ selectedInterview.jd_title || '未指定岗位' }}</span>
          <span>{{ TYPE_LABELS[selectedInterview.interview_type as InterviewType] || selectedInterview.interview_type }}</span>
          <span>{{ selectedInterview.points.length }} 场</span>
        </div>

        <div class="metric-row">
          <div class="metric">
            <span>平均总分</span>
            <strong>{{ selectedInterview.average_total.toFixed(1) }}</strong>
          </div>
          <div class="metric">
            <span>最高总分</span>
            <strong class="good">{{ selectedInterview.best_total.toFixed(1) }}</strong>
          </div>
          <div class="metric">
            <span>首末变化</span>
            <strong :class="selectedInterview.improvement >= 0 ? 'good' : 'low'">
              {{ improvementText(selectedInterview.improvement) }}
            </strong>
          </div>
          <div
            v-for="dimension in INTERVIEW_DIMENSIONS"
            :key="dimension.key"
            class="metric metric-dim"
          >
            <span>{{ dimension.label }}</span>
            <strong :class="changeLevel(selectedInterview, dimension.key)">
              {{ changeText(selectedInterview, dimension.key) }}
            </strong>
          </div>
        </div>

        <TrendLineChart :labels="interviewLabels" :series="interviewSeries" :height="300" />

        <el-table :data="selectedInterview.points" size="small" class="point-table">
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="版本" width="70">
            <template #default="{ row }">v{{ row.resume_version_no }}</template>
          </el-table-column>
          <el-table-column label="总分" width="80">
            <template #default="{ row }">
              <strong :class="scoreLevel(row.total_score)">{{ row.total_score.toFixed(1) }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="答题" width="80">
            <template #default="{ row }">{{ row.answered_count }}/{{ row.question_count }}</template>
          </el-table-column>
          <el-table-column label="相关性" width="80">
            <template #default="{ row }">{{ row.dimension_scores.relevance ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="证据" width="70">
            <template #default="{ row }">{{ row.dimension_scores.evidence ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="表达" width="70">
            <template #default="{ row }">{{ row.dimension_scores.expression ?? '—' }}</template>
          </el-table-column>
        </el-table>
      </template>

      <el-empty v-else :image-size="56" description="还没有已完成的面试记录">
        <el-button type="primary" @click="goInterviews">开始模拟面试</el-button>
      </el-empty>
    </el-card>

    <el-card class="weakness-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>弱项聚合</span>
          <small>来自诊断缺失项与已结束面试的五维均分</small>
        </div>
      </template>

      <el-alert
        v-if="lowestDimension"
        :title="`当前最低维度：${lowestDimension.label}（平均 ${lowestDimension.average.toFixed(1)} 分，${lowestDimension.sample_count} 场样本）`"
        type="warning"
        :closable="false"
        show-icon
        class="weakness-alert"
      />

      <div v-if="hasWeakness" class="weakness-grid">
        <section>
          <h4>高频缺失关键词</h4>
          <div class="tag-list">
            <el-tag
              v-for="item in store.weaknesses?.missing_keywords ?? []"
              :key="item.keyword"
              type="danger"
              effect="plain"
            >
              {{ item.keyword }} × {{ item.count }}
            </el-tag>
            <span v-if="!store.weaknesses?.missing_keywords.length" class="muted">
              暂无缺失关键词
            </span>
          </div>
        </section>

        <section>
          <h4>未满足的岗位要求</h4>
          <div class="tag-list">
            <el-tag
              v-for="item in store.weaknesses?.missing_requirements ?? []"
              :key="item.requirement"
              type="warning"
              effect="plain"
            >
              {{ item.requirement }} × {{ item.count }}
            </el-tag>
            <span v-if="!store.weaknesses?.missing_requirements.length" class="muted">
              暂无未满足要求
            </span>
          </div>
        </section>

        <section class="dimension-section">
          <h4>面试五维均分</h4>
          <div class="dimension-list">
            <div
              v-for="item in store.weaknesses?.interview_dimensions ?? []"
              :key="item.key"
              class="dimension-row"
            >
              <span class="dimension-label">{{ item.label }}</span>
              <el-progress
                :percentage="item.average"
                :stroke-width="7"
                :show-text="false"
                :color="item.average >= 75 ? '#16a34a' : item.average >= 60 ? '#d97706' : '#dc2626'"
              />
              <strong :class="scoreLevel(item.average)">{{ item.average.toFixed(1) }}</strong>
              <small>{{ item.sample_count }} 场</small>
            </div>
            <span v-if="!store.weaknesses?.interview_dimensions.length" class="muted">
              还没有已结束的面试
            </span>
          </div>
        </section>
      </div>

      <el-empty v-else :image-size="56" description="积累诊断或面试记录后，这里会汇总重复出现的弱项" />
    </el-card>
  </div>
</template>

<style scoped>
.growth-page {
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
  max-width: 760px;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--app-muted);
}

.filter-card,
.trend-card,
.weakness-card {
  border-radius: 14px;
  border-color: var(--app-border);
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-field > span {
  font-size: 11.5px;
  color: var(--app-muted);
}

.filter-note {
  margin-left: auto;
  font-size: 11px;
  color: #94a3b8;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: linear-gradient(160deg, #ffffff 0%, #f8fbff 100%);
}

.stat-card span {
  font-size: 11.5px;
  color: var(--app-muted);
}

.stat-card strong {
  font-size: 28px;
  line-height: 1.1;
  color: var(--app-text);
}

.stat-card small {
  font-size: 10.5px;
  color: #94a3b8;
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

.card-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.card-title small {
  font-size: 10.5px;
  font-weight: 400;
  color: #94a3b8;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--app-muted);
}

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
}

.metric {
  min-width: 104px;
  padding: 9px 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.metric span {
  display: block;
  font-size: 10.5px;
  color: var(--app-muted);
  margin-bottom: 3px;
}

.metric strong {
  font-size: 16px;
  color: #334155;
}

.metric-dim strong {
  font-size: 14px;
}

.point-table {
  margin-top: 10px;
}

.weakness-alert {
  margin-bottom: 16px;
}

.weakness-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.weakness-grid h4 {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: #334155;
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

.dimension-section {
  grid-column: 1 / -1;
}

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dimension-row {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr) 48px 48px;
  align-items: center;
  gap: 12px;
}

.dimension-label {
  font-size: 11.5px;
  color: #475569;
}

.dimension-row strong {
  font-size: 12.5px;
  text-align: right;
}

.dimension-row small {
  font-size: 10px;
  color: #94a3b8;
  text-align: right;
}

.good {
  color: #16a34a;
}

.mid {
  color: #d97706;
}

.low {
  color: #dc2626;
}

@media (max-width: 900px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .weakness-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-note {
    margin-left: 0;
  }
}
</style>
