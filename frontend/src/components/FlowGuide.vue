<script setup lang="ts">
import { computed } from 'vue'

type FlowStep = 'resume' | 'structure' | 'jd' | 'diagnosis' | 'interview' | 'growth'

const props = defineProps<{ current: FlowStep }>()

const steps: Array<{ key: FlowStep; label: string; to?: string }> = [
  { key: 'resume', label: '上传简历', to: '/resumes' },
  { key: 'structure', label: '确认信息' },
  { key: 'jd', label: '填写岗位', to: '/jds' },
  { key: 'diagnosis', label: '四维诊断' },
  { key: 'interview', label: '模拟面试' },
  { key: 'growth', label: '成长复盘', to: '/growth' },
]

const currentIndex = computed(() => Math.max(0, steps.findIndex((step) => step.key === props.current)))
</script>

<template>
  <nav class="flow-guide" aria-label="使用流程">
    <span class="flow-title">使用流程</span>
    <ol>
      <li
        v-for="(step, index) in steps"
        :key="step.key"
        :class="{ current: index === currentIndex }"
        :aria-current="index === currentIndex ? 'step' : undefined"
      >
        <router-link v-if="step.to" :to="step.to" class="flow-link">
          <span class="flow-dot">{{ index + 1 }}</span>
          <span class="flow-label">{{ step.label }}</span>
        </router-link>
        <span v-else class="flow-link static">
          <span class="flow-dot">{{ index + 1 }}</span>
          <span class="flow-label">{{ step.label }}</span>
        </span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.flow-guide {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 9px 14px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: #fff;
  overflow-x: auto;
}

.flow-title {
  flex: none;
  font-size: 12px;
  color: var(--app-muted);
}

ol {
  display: flex;
  align-items: center;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

li {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  font-size: 12px;
  color: #94a3b8;
}

li + li::before {
  content: '';
  width: 14px;
  height: 1px;
  margin-right: 2px;
  background: var(--app-border);
}

.flow-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  background: #f1f5f9;
  color: #64748b;
}

.flow-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: inherit;
  text-decoration: none;
}

.flow-link:not(.static):hover .flow-label {
  color: var(--app-primary);
}

.flow-label {
  line-height: 1;
}

.current .flow-dot {
  background: var(--app-primary);
  color: #fff;
}

.current .flow-label {
  color: var(--app-text);
  font-weight: 600;
}

@media (max-width: 640px) {
  .flow-title {
    display: none;
  }
}
</style>
