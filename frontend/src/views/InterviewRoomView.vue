<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useInterviewStore } from '@/stores/interviews'
import type {
  AnswerEvaluation,
  EvaluationKey,
  InterviewQuestion,
  InterviewStatus,
  InterviewType,
  QuestionSource,
} from '@/types/interview'

const route = useRoute()
const router = useRouter()
const store = useInterviewStore()

const answerText = ref('')
const pageLoading = ref(false)

const interviewId = computed(() => String(route.params.id))
const detail = computed(() => store.current)
const currentQuestion = computed<InterviewQuestion | null>(() => {
  if (!detail.value?.current_question_id) return null
  return (
    detail.value.questions.find((item) => item.id === detail.value?.current_question_id) ?? null
  )
})
const answeredQuestions = computed(() =>
  (detail.value?.questions ?? []).filter((item) => item.answer),
)
const progress = computed(() => {
  if (!detail.value || !detail.value.question_count) return 0
  return Math.round((detail.value.answered_count / detail.value.question_count) * 100)
})
const canFinish = computed(
  () => Boolean(detail.value && detail.value.status !== 'completed' && detail.value.answered_count),
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

const SOURCE_META: Record<QuestionSource, { label: string; type: 'primary' | 'warning' | 'info' }> = {
  resume: { label: '简历', type: 'primary' },
  jd: { label: '岗位', type: 'warning' },
  behavioral: { label: '行为题', type: 'info' },
}

const DIMENSION_KEYS: EvaluationKey[] = [
  'relevance',
  'correctness',
  'structure',
  'evidence',
  'expression',
]

const DIMENSION_LABELS: Record<EvaluationKey, string> = {
  relevance: '相关性',
  correctness: '专业正确性',
  structure: '结构',
  evidence: '证据',
  expression: '表达',
}

function dimensionLabel(key: EvaluationKey): string {
  return DIMENSION_LABELS[key] ?? key
}

function statusMeta(status: InterviewStatus) {
  return STATUS_META[status] ?? { label: status, type: 'info' as const }
}

function sourceMeta(source: QuestionSource) {
  return SOURCE_META[source] ?? { label: source, type: 'info' as const }
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

function scoreLevel(score: number | null): string {
  if (score === null) return ''
  if (score >= 80) return 'good'
  if (score >= 60) return 'mid'
  return 'low'
}

function evaluationScore(evaluation: AnswerEvaluation | null): number {
  return evaluation?.overall_score ?? 0
}

function dimensionScore(evaluation: AnswerEvaluation | null, key: string): number {
  return evaluation?.dimensions.find((item) => item.key === key)?.score ?? 0
}

function dimensionComment(evaluation: AnswerEvaluation | null, key: string): string {
  return evaluation?.dimensions.find((item) => item.key === key)?.comment ?? ''
}

async function load(): Promise<void> {
  pageLoading.value = true
  try {
    await store.select(interviewId.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '面试加载失败')
  } finally {
    pageLoading.value = false
  }
}

async function submitAnswer(): Promise<void> {
  const question = currentQuestion.value
  if (!question) return
  const text = answerText.value.trim()
  if (!text) {
    ElMessage.warning('请先输入回答')
    return
  }

  try {
    await store.answer(interviewId.value, question.id, text)
    answerText.value = ''
    ElMessage.success('已提交并完成本题评价')
    await nextTick()
    document
      .querySelector<HTMLElement>('.current-card')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '回答提交失败')
  }
}

async function finishEarly(): Promise<void> {
  if (!detail.value) return
  const unanswered = detail.value.question_count - detail.value.answered_count
  try {
    await ElMessageBox.confirm(
      unanswered > 0
        ? `还有 ${unanswered} 道题未回答，结束后将按已答题目计算总分。确定结束？`
        : '确定结束本次面试？',
      '结束面试',
      { type: 'warning', confirmButtonText: '结束面试', cancelButtonText: '继续作答' },
    )
  } catch {
    return
  }

  try {
    await store.finish(interviewId.value)
    ElMessage.success('面试已结束，可以生成复盘报告')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '结束面试失败')
  }
}

async function generateReport(force = false): Promise<void> {
  try {
    await store.report(interviewId.value, force)
    ElMessage.success('复盘报告已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '报告生成失败')
  }
}

function goList(): void {
  void router.push({ name: 'interviews' })
}

function goWorkspace(): void {
  if (!detail.value) return
  void router.push({
    name: 'resume-workspace',
    params: { id: detail.value.resume_id },
  })
}

watch(
  () => currentQuestion.value?.id,
  () => {
    answerText.value = ''
  },
)

onMounted(() => {
  void load()
})
</script>

<template>
  <div v-loading="pageLoading" class="room-page">
    <header class="page-head">
      <div class="head-main">
        <el-button link type="primary" @click="goList">← 返回面试列表</el-button>
        <div class="head-title">
          <h1>模拟面试</h1>
          <template v-if="detail">
            <el-tag size="small" effect="plain">{{ TYPE_LABELS[detail.interview_type] }}</el-tag>
            <el-tag size="small" :type="statusMeta(detail.status).type" effect="light">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </template>
        </div>
        <p v-if="detail" class="head-meta">
          {{ detail.resume_filename }} · v{{ detail.resume_version_no }} ·
          {{ detail.jd_title || '未指定岗位' }} · {{ formatDate(detail.created_at) }}
        </p>
      </div>
      <div class="head-actions">
        <el-button v-if="detail" plain @click="goWorkspace">查看结构化简历</el-button>
        <el-button v-if="canFinish" :loading="store.finishing" @click="finishEarly">
          结束面试
        </el-button>
      </div>
    </header>

    <template v-if="detail">
      <el-card class="progress-card" shadow="never">
        <div class="progress-head">
          <div>
            <strong>进度 {{ detail.answered_count }} / {{ detail.question_count }}</strong>
            <span v-if="detail.total_score !== null" class="total">
              总分 <b :class="scoreLevel(detail.total_score)">{{ detail.total_score.toFixed(1) }}</b>
            </span>
          </div>
          <small>{{ detail.rubric_version }} · {{ detail.model_name || '未记录模型' }}</small>
        </div>
        <el-progress :percentage="progress" :stroke-width="8" :show-text="false" />
        <p class="progress-note">
          每题提交后立即评价；回答出现明显漏洞时会自动生成追问，追问最多两级。
        </p>
      </el-card>

      <el-card v-if="currentQuestion" class="current-card" shadow="never">
        <div class="current-head">
          <div class="current-tags">
            <el-tag size="small" :type="sourceMeta(currentQuestion.source).type" effect="light">
              {{ sourceMeta(currentQuestion.source).label }}
            </el-tag>
            <el-tag v-if="currentQuestion.follow_up_level" size="small" type="warning" effect="plain">
              第 {{ currentQuestion.follow_up_level }} 级追问
            </el-tag>
            <span class="source-ref">{{ currentQuestion.source_ref }}</span>
          </div>
          <span class="question-index">第 {{ currentQuestion.order_index }} 题</span>
        </div>

        <h2 class="question-text">{{ currentQuestion.question }}</h2>
        <p class="intent">考察点：{{ currentQuestion.intent }}</p>

        <el-input
          v-model="answerText"
          type="textarea"
          :rows="8"
          maxlength="8000"
          show-word-limit
          placeholder="建议先给结论，再用 STAR 展开：情境、任务、行动、结果。可以按 Ctrl + Enter 提交。"
          @keydown.ctrl.enter.prevent="submitAnswer"
        />

        <div class="answer-actions">
          <el-button
            type="primary"
            size="large"
            :loading="store.answering"
            :disabled="!answerText.trim()"
            @click="submitAnswer"
          >
            提交回答并评价
          </el-button>
          <span class="hint">提交后会调用 DeepSeek 评分，可能需要数秒</span>
        </div>
      </el-card>

      <el-card v-else class="complete-card" shadow="never">
        <div class="complete-head">
          <div>
            <h2>面试已结束</h2>
            <p>
              共回答 {{ detail.answered_count }} 题，总分
              <b :class="scoreLevel(detail.total_score)">
                {{ detail.total_score === null ? '—' : detail.total_score.toFixed(1) }}
              </b>
            </p>
          </div>
          <div class="complete-actions">
            <el-button
              v-if="!detail.report"
              type="primary"
              :loading="store.reporting"
              @click="generateReport(false)"
            >
              生成复盘报告
            </el-button>
            <el-button
              v-else
              :loading="store.reporting"
              @click="generateReport(true)"
            >
              重新生成报告
            </el-button>
          </div>
        </div>
        <div class="dimension-bars">
          <div v-for="key in DIMENSION_KEYS" :key="key" class="dimension-bar">
            <span>{{ dimensionLabel(key) }}</span>
            <el-progress
              :percentage="detail.dimension_scores[key] ?? 0"
              :stroke-width="8"
              :show-text="false"
              :color="(detail.dimension_scores[key] ?? 0) >= 75 ? '#16a34a' : (detail.dimension_scores[key] ?? 0) >= 60 ? '#d97706' : '#dc2626'"
            />
            <strong :class="scoreLevel(detail.dimension_scores[key] ?? 0)">
              {{ (detail.dimension_scores[key] ?? 0).toFixed(1) }}
            </strong>
          </div>
        </div>
      </el-card>

      <el-card v-if="detail.report" class="report-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span>复盘报告</span>
            <small>{{ detail.prompt_version || '' }}</small>
          </div>
        </template>

        <p class="report-overview">{{ detail.report.overview }}</p>

        <div class="report-grid">
          <section>
            <h4>优势</h4>
            <ul>
              <li v-for="(item, index) in detail.report.strengths" :key="`s-${index}`">
                {{ item }}
              </li>
              <li v-if="!detail.report.strengths.length" class="muted">暂无</li>
            </ul>
          </section>
          <section>
            <h4>短板</h4>
            <ul>
              <li v-for="(item, index) in detail.report.weaknesses" :key="`w-${index}`">
                {{ item }}
              </li>
              <li v-if="!detail.report.weaknesses.length" class="muted">暂无</li>
            </ul>
          </section>
          <section class="improvements">
            <h4>改进建议</h4>
            <ol>
              <li v-for="(item, index) in detail.report.improvements" :key="`i-${index}`">
                {{ item }}
              </li>
              <li v-if="!detail.report.improvements.length" class="muted">暂无</li>
            </ol>
          </section>
        </div>

        <el-table :data="detail.report.question_notes" size="small" class="report-table">
          <el-table-column prop="order_index" label="#" width="56" />
          <el-table-column prop="question" label="题目" min-width="220" />
          <el-table-column prop="comment" label="点评" min-width="220" />
        </el-table>
      </el-card>

      <el-card class="history-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span>问答记录</span>
            <small>{{ answeredQuestions.length }} 题已作答</small>
          </div>
        </template>

        <div class="qa-list">
          <article
            v-for="question in detail.questions"
            :key="question.id"
            class="qa-item"
            :class="{
              'qa-follow-up': question.follow_up_level > 0,
              'qa-current': question.id === detail.current_question_id,
              'qa-pending': !question.answer,
            }"
          >
            <header class="qa-head">
              <div class="qa-tags">
                <span class="qa-order">{{ question.order_index }}</span>
                <el-tag size="small" :type="sourceMeta(question.source).type" effect="light">
                  {{ sourceMeta(question.source).label }}
                </el-tag>
                <el-tag
                  v-if="question.follow_up_level"
                  size="small"
                  type="warning"
                  effect="plain"
                >
                  追问 L{{ question.follow_up_level }}
                </el-tag>
                <span class="qa-ref">{{ question.source_ref }}</span>
              </div>
              <span
                v-if="question.score !== null"
                class="qa-score"
                :class="scoreLevel(question.score)"
              >
                {{ question.score.toFixed(1) }}
              </span>
              <el-tag v-else-if="question.id === detail.current_question_id" size="small" effect="plain">
                当前
              </el-tag>
              <el-tag v-else size="small" type="info" effect="plain">未作答</el-tag>
            </header>

            <p class="qa-question">{{ question.question }}</p>
            <p class="qa-intent">考察点：{{ question.intent }}</p>

            <template v-if="question.answer">
              <div class="qa-answer">
                <span>我的回答</span>
                <p>{{ question.answer }}</p>
              </div>

              <div v-if="question.evaluation" class="evaluation">
                <div class="evaluation-head">
                  <strong>逐题评价</strong>
                  <span>综合 {{ evaluationScore(question.evaluation).toFixed(0) }} 分</span>
                </div>
                <div class="evaluation-dims">
                  <div
                    v-for="key in DIMENSION_KEYS"
                    :key="key"
                    class="evaluation-dim"
                  >
                    <div class="dim-head">
                      <span>{{ dimensionLabel(key) }}</span>
                      <strong>{{ dimensionScore(question.evaluation, key) }}</strong>
                    </div>
                    <el-progress
                      :percentage="dimensionScore(question.evaluation, key)"
                      :stroke-width="5"
                      :show-text="false"
                      :color="dimensionScore(question.evaluation, key) >= 75 ? '#16a34a' : dimensionScore(question.evaluation, key) >= 60 ? '#d97706' : '#dc2626'"
                    />
                    <p>{{ dimensionComment(question.evaluation, key) }}</p>
                  </div>
                </div>
                <p class="eval-summary">{{ question.evaluation.summary }}</p>
                <div class="eval-lists">
                  <div v-if="question.evaluation.strengths.length">
                    <span>做得好</span>
                    <ul>
                      <li v-for="(item, index) in question.evaluation.strengths" :key="`es-${index}`">
                        {{ item }}
                      </li>
                    </ul>
                  </div>
                  <div v-if="question.evaluation.weaknesses.length">
                    <span>待改进</span>
                    <ul>
                      <li v-for="(item, index) in question.evaluation.weaknesses" :key="`ew-${index}`">
                        {{ item }}
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </template>
          </article>
        </div>
      </el-card>
    </template>

    <el-empty v-else-if="!pageLoading" description="面试记录不存在或无权访问">
      <el-button type="primary" @click="goList">返回面试列表</el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.room-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.head-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 0;
}

.head-title h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.5px;
  color: var(--app-text);
}

.head-meta {
  margin: 6px 0 0;
  font-size: 11.5px;
  color: var(--app-muted);
}

.head-actions {
  display: flex;
  gap: 10px;
  flex: none;
}

.progress-card,
.current-card,
.complete-card,
.report-card,
.history-card {
  border-radius: 14px;
  border-color: var(--app-border);
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 12.5px;
  color: #334155;
}

.progress-head .total {
  margin-left: 16px;
  color: var(--app-muted);
}

.progress-head small {
  font-size: 10.5px;
  color: #94a3b8;
}

.progress-note {
  margin: 10px 0 0;
  font-size: 11px;
  color: #94a3b8;
}

.current-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.current-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.source-ref {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: var(--app-muted);
}

.question-index {
  flex: none;
  font-size: 11px;
  color: #94a3b8;
}

.question-text {
  margin: 14px 0 6px;
  font-size: 19px;
  line-height: 1.65;
  color: var(--app-text);
}

.intent {
  margin: 0 0 16px;
  font-size: 11.5px;
  color: var(--app-muted);
}

.answer-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.hint {
  font-size: 11px;
  color: #94a3b8;
}

.complete-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.complete-head h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: var(--app-text);
}

.complete-head p {
  margin: 0;
  font-size: 12.5px;
  color: var(--app-muted);
}

.complete-head b {
  font-size: 20px;
}

.dimension-bars {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.dimension-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.dimension-bar span {
  font-size: 11px;
  color: var(--app-muted);
}

.dimension-bar strong {
  font-size: 16px;
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
  font-size: 10.5px;
  font-weight: 400;
  color: #94a3b8;
}

.report-overview {
  margin: 0 0 16px;
  font-size: 12.5px;
  line-height: 1.85;
  color: #334155;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.report-grid section {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fcfdff;
}

.report-grid h4 {
  margin: 0 0 8px;
  font-size: 12.5px;
  color: #334155;
}

.report-grid ul,
.report-grid ol {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.8;
  color: #475569;
}

.improvements {
  grid-column: 1 / -1;
}

.report-table {
  margin-top: 4px;
}

.qa-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.qa-item {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fcfdff;
}

.qa-item.qa-follow-up {
  margin-left: 26px;
  border-left: 3px solid #f59e0b;
}

.qa-item.qa-current {
  border-color: #bfdbfe;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.qa-item.qa-pending {
  background: #fbfdff;
}

.qa-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.qa-tags {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.qa-order {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #eff6ff;
  color: var(--app-primary);
  font-size: 11px;
  font-weight: 600;
  flex: none;
}

.qa-ref {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10.5px;
  color: #94a3b8;
}

.qa-score {
  font-size: 15px;
  font-weight: 700;
}

.qa-question {
  margin: 10px 0 4px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--app-text);
}

.qa-intent {
  margin: 0 0 12px;
  font-size: 10.5px;
  color: #94a3b8;
}

.qa-answer {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.qa-answer span {
  font-size: 11px;
  color: #94a3b8;
}

.qa-answer p {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}

.evaluation {
  margin-top: 12px;
  padding: 14px;
  border-radius: 10px;
  border: 1px dashed #dbeafe;
  background: #f8fbff;
}

.evaluation-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: #475569;
  margin-bottom: 10px;
}

.evaluation-dims {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.evaluation-dim {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.dim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 10.5px;
  color: #64748b;
}

.dim-head strong {
  color: #334155;
}

.evaluation-dim p {
  margin: 0;
  font-size: 10px;
  line-height: 1.6;
  color: #94a3b8;
}

.eval-summary {
  margin: 12px 0 8px;
  font-size: 11.5px;
  line-height: 1.75;
  color: #475569;
}

.eval-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.eval-lists span {
  font-size: 10.5px;
  color: #94a3b8;
}

.eval-lists ul {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: 11px;
  line-height: 1.7;
  color: #475569;
}

.muted {
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 900px) {
  .page-head,
  .complete-head {
    flex-direction: column;
  }

  .dimension-bars,
  .evaluation-dims {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .report-grid,
  .eval-lists {
    grid-template-columns: minmax(0, 1fr);
  }

  .qa-item.qa-follow-up {
    margin-left: 10px;
  }
}
</style>
