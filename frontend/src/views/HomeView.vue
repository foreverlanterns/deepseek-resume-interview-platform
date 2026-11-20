<script setup lang="ts">
import { useRouter } from 'vue-router'

interface Dimension {
  key: string
  name: string
  weight: number
  hint: string
  color: string
}

interface Step {
  title: string
  detail: string
}

interface Benefit {
  title: string
  detail: string
}

const router = useRouter()

const dimensions: Dimension[] = [
  {
    key: 'format',
    name: '格式规范性',
    weight: 15,
    hint: '文本可解析、板块标题清晰、时间线一致',
    color: '#60a5fa',
  },
  {
    key: 'completeness',
    name: '内容完整度',
    weight: 20,
    hint: '教育、工作、项目、技能与成果表达完整',
    color: '#34d399',
  },
  {
    key: 'keywords',
    name: '关键词匹配',
    weight: 25,
    hint: '目标岗位关键词覆盖、同义词归一、技能层级',
    color: '#fbbf24',
  },
  {
    key: 'jd_match',
    name: '岗位匹配度',
    weight: 40,
    hint: '硬性要求、经验相关性、项目证据',
    color: '#2563eb',
  },
]

const steps: Step[] = [
  {
    title: '上传简历',
    detail: '支持 PDF 与 Word，自动提取文本并整理成教育、工作、项目、技能等信息。',
  },
  {
    title: '选择目标岗位',
    detail: '填写岗位的技能、关键词与任职要求，诊断会逐条对照你的简历。',
  },
  {
    title: '诊断与面试',
    detail: '查看四维评分和改写建议，再用模拟面试检验表达，记录每次进步。',
  },
]

const benefits: Benefit[] = [
  {
    title: '看得懂的四维评分',
    detail: '格式、完整度、关键词与岗位匹配分别打分，每一项都附简历原文依据。',
  },
  {
    title: '不改事实的改写建议',
    detail: '每条建议给出原文、问题、改写示例和理由，不会替你编造经历或数据。',
  },
  {
    title: '接近真实的模拟面试',
    detail: '根据简历与岗位出题，逐题评价并追问，结束后生成复盘报告。',
  },
  {
    title: '可比较的成长记录',
    detail: '同一份简历、同一个岗位下的诊断与面试趋势放在一起看，定位重复出现的弱项。',
  },
]

function goResumes(): void {
  void router.push({ name: 'resumes' })
}

function goInterviews(): void {
  void router.push({ name: 'interviews' })
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-copy">
        <el-tag effect="plain" round class="eyebrow">AI 简历诊断 · 面试训练</el-tag>
        <h1>把简历从“投出去”<br />变成“有证据地投出去”</h1>
        <p class="hero-desc">
          上传简历，选择目标岗位，获得四维诊断与可执行的改写建议；
          再用一场模拟面试检验表达，把每次进步记录下来。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="goResumes">开始诊断</el-button>
          <el-button size="large" @click="goInterviews">开始模拟面试</el-button>
        </div>
      </div>

      <div class="hero-panel">
        <div class="panel-head">
          <span>诊断看什么</span>
          <span class="panel-badge">四维综合评分</span>
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
        <p class="panel-note">每个维度都会给出得分依据，改写建议只基于简历原文。</p>
      </div>
    </section>

    <section class="workspace">
      <el-card shadow="never" class="panel-card">
        <template #header>
          <div class="card-head">
            <span>三步开始</span>
            <span class="subtle">从上传到复盘</span>
          </div>
        </template>

        <ol class="steps">
          <li v-for="(step, index) in steps" :key="step.title">
            <span class="step-index">{{ index + 1 }}</span>
            <div class="step-body">
              <strong>{{ step.title }}</strong>
              <p>{{ step.detail }}</p>
            </div>
          </li>
        </ol>

        <div class="card-foot">
          <el-button type="primary" plain @click="goResumes">上传第一份简历</el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="panel-card">
        <template #header>
          <div class="card-head">
            <span>你会得到</span>
            <span class="subtle">每一步都有依据</span>
          </div>
        </template>

        <ul class="benefits">
          <li v-for="item in benefits" :key="item.title">
            <span class="benefit-mark"></span>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
            </div>
          </li>
        </ul>

        <div class="card-foot">
          <el-button link type="primary" @click="goInterviews">去看看面试怎么练 →</el-button>
        </div>
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

.eyebrow {
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
  max-width: 540px;
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
  display: flex;
  flex-direction: column;
}

.panel-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
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

.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.steps li {
  display: flex;
  gap: 14px;
}

.step-index {
  flex: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-primary);
  background: #eff6ff;
  border: 1px solid #dbeafe;
}

.step-body strong {
  display: block;
  font-size: 13.5px;
  color: var(--app-text);
}

.step-body p {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--app-muted);
}

.benefits {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.benefits li {
  display: flex;
  gap: 12px;
}

.benefit-mark {
  flex: none;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #16a34a;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.1);
}

.benefits strong {
  display: block;
  font-size: 13px;
  color: var(--app-text);
}

.benefits p {
  margin: 4px 0 0;
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--app-muted);
}

.card-foot {
  margin-top: auto;
  padding-top: 20px;
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
