<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome(): void {
  void router.push('/')
}
</script>

<template>
  <div class="not-found">
    <el-result icon="warning" title="页面不存在" sub-title="请检查地址，或返回工作台继续。">
      <template #extra>
        <el-button type="primary" @click="goHome">返回工作台</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.not-found {
  padding: 60px 0;
}
</style>
