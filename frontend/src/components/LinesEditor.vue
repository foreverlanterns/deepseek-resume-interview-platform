<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    rows?: number
    placeholder?: string
  }>(),
  {
    rows: 3,
    placeholder: '每行一条',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const text = computed({
  get: () => props.modelValue.join('\n'),
  set: (value: string) => emit('update:modelValue', value.split('\n')),
})
</script>

<template>
  <el-input
    v-model="text"
    type="textarea"
    :rows="rows"
    :placeholder="placeholder"
    resize="vertical"
  />
</template>
