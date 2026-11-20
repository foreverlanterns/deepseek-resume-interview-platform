<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadFile, type UploadInstance } from 'element-plus'

import FlowGuide from '@/components/FlowGuide.vue'
import { fetchResume } from '@/api/resumes'
import { useResumeStore } from '@/stores/resumes'
import type { ResumeDetail, ResumeStatus } from '@/types/resume'

const ALLOWED_EXTENSIONS = ['.pdf', '.docx']
const MAX_SIZE = 10 * 1024 * 1024

const store = useResumeStore()
const router = useRouter()
const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<ResumeDetail | null>(null)

const STATUS_META: Record<
  ResumeStatus,
  { label: string; type: 'success' | 'warning' | 'info' | 'danger' }
> = {
  uploaded: { label: '待解析', type: 'info' },
  extracting: { label: '解析中', type: 'warning' },
  extracted: { label: '已提取', type: 'success' },
  needs_ocr: { label: '需 OCR', type: 'warning' },
  failed: { label: '解析失败', type: 'danger' },
}

function statusLabel(status: ResumeStatus): string {
  return STATUS_META[status]?.label ?? status
}

function statusType(status: ResumeStatus): 'success' | 'warning' | 'info' | 'danger' {
  return STATUS_META[status]?.type ?? 'info'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false })
}

function validateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
    return '仅支持 PDF 和 DOCX 文件'
  }
  if (file.size === 0) {
    return '文件内容为空'
  }
  if (file.size > MAX_SIZE) {
    return '文件大小不能超过 10 MB'
  }
  return null
}

function handleFileChange(uploadFile: UploadFile): void {
  const raw = uploadFile.raw
  if (!raw) {
    return
  }
  const message = validateFile(raw)
  if (message) {
    ElMessage.error(message)
    selectedFile.value = null
    uploadRef.value?.clearFiles()
    return
  }
  selectedFile.value = raw
}

function clearSelection(): void {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}

async function submitUpload(): Promise<void> {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 PDF 或 DOCX 文件')
    return
  }
  try {
    const result = await store.upload(selectedFile.value)
    ElMessage.success(
      result.status === 'extracted' ? '上传成功，已提取文本' : '上传完成，请查看解析状态',
    )
    clearSelection()
    await openDetail(result.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '简历上传失败')
  }
}

async function openDetail(resumeId: string): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await fetchResume(resumeId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '简历详情加载失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function removeResume(resumeId: string, filename: string): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除「${filename}」？原文件与提取文本都会删除。`,
      '删除简历',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  try {
    await store.remove(resumeId)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除简历失败')
  }
}

function refresh(): void {
  void store.load(true)
}

function goDiagnosis(resumeId: string): void {
  void router.push({ name: 'diagnosis', params: { id: resumeId } })
}

function openWorkspace(resumeId: string): void {
  void router.push({ name: 'resume-workspace', params: { id: resumeId } })
}

onMounted(() => {
  void store.load(true)
})
</script>

<template>
  <div class="resumes-page">
    <header class="page-head">
      <div>
        <h1>我的简历</h1>
        <p>
          上传 PDF 或 DOCX，系统会保存原文件并提取文本。后续诊断、修改示例和面试都会基于这份文本。
        </p>
      </div>
      <el-button :loading="store.loading" @click="refresh">刷新列表</el-button>
    </header>

    <FlowGuide current="resume" />

    <el-card class="upload-card" shadow="never">
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        accept=".pdf,.docx"
        :auto-upload="false"
        :show-file-list="false"
        :on-change="handleFileChange"
      >
        <div class="upload-zone">
          <div class="upload-icon">PDF</div>
          <p class="upload-title">拖拽简历到这里，或点击选择文件</p>
          <p class="upload-hint">支持 PDF、DOCX，单个文件不超过 10 MB</p>
        </div>
      </el-upload>

      <div v-if="selectedFile" class="selected-file">
        <div class="selected-info">
          <strong>{{ selectedFile.name }}</strong>
          <span>{{ formatSize(selectedFile.size) }}</span>
        </div>
        <el-button link type="danger" @click="clearSelection">移除</el-button>
      </div>

      <div class="upload-actions">
        <el-button
          type="primary"
          :disabled="!selectedFile"
          :loading="store.uploading"
          @click="submitUpload"
        >
          上传并提取文本
        </el-button>
        <span class="upload-note">暂不支持图片型简历，请上传 PDF 或 Word 文件</span>
      </div>
      <p class="flow-hint">上传后点击列表中的“结构化”，确认信息后即可开始诊断或模拟面试。</p>
    </el-card>

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      :closable="false"
      show-icon
      class="error-alert"
    />

    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span>已上传简历</span>
          <span class="subtle">共 {{ store.items.length }} 份</span>
        </div>
      </template>

      <el-table
        v-loading="store.loading"
        :data="store.items"
        empty-text="还没有简历，先上传一份吧"
      >
        <el-table-column prop="original_filename" label="文件名" min-width="220" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文本量" width="110">
          <template #default="{ row }">{{ row.text_length }} 字</template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">预览</el-button>
            <el-button link type="primary" @click="openWorkspace(row.id)">结构化</el-button>
            <el-button
              v-if="row.status === 'extracted'"
              link
              type="primary"
              @click="goDiagnosis(row.id)"
            >
              诊断
            </el-button>
            <el-button link type="danger" @click="removeResume(row.id, row.original_filename)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="detailVisible" title="简历文本预览" size="min(560px, 92vw)">
      <div v-loading="detailLoading" class="detail">
        <template v-if="detail">
          <div class="detail-head">
            <strong>{{ detail.original_filename }}</strong>
            <el-tag :type="statusType(detail.status)" size="small" effect="light">
              {{ statusLabel(detail.status) }}
            </el-tag>
          </div>
          <div class="detail-meta">
            <span>{{ formatSize(detail.file_size) }}</span>
            <span>{{ detail.text_length }} 字</span>
            <span v-if="detail.page_count">{{ detail.page_count }} 页</span>
          </div>
          <el-alert
            v-if="detail.error_message"
            :title="detail.error_message"
            type="warning"
            :closable="false"
            show-icon
            class="detail-alert"
          />
          <pre class="text-preview">{{ detail.text_preview || '未提取到文本内容' }}</pre>
          <p class="preview-note">仅展示前 800 字；完整内容与信息校正请进入“结构化”。</p>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.flow-hint {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--app-muted);
}

.resumes-page {
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
  max-width: 680px;
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--app-muted);
}

.upload-card {
  border-radius: 16px;
  border-color: var(--app-border);
}

.upload-zone {
  padding: 18px 12px 8px;
}

.upload-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #dbeafe, #eff6ff);
  color: var(--app-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.upload-title {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--app-text);
}

.upload-hint {
  margin: 0;
  font-size: 11.5px;
  color: var(--app-muted);
}

.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding: 10px 14px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #f8fbff;
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.selected-info strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--app-text);
}

.selected-info span {
  flex: none;
  font-size: 11.5px;
  color: var(--app-muted);
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.upload-note {
  font-size: 11.5px;
  color: #94a3b8;
}

.error-alert {
  border-radius: 10px;
}

.list-card {
  border-radius: 16px;
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

.subtle {
  font-size: 11.5px;
  font-weight: 400;
  color: var(--app-muted);
}

.detail {
  min-height: 200px;
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.detail-head strong {
  font-size: 15px;
  color: var(--app-text);
  word-break: break-all;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 14px;
  font-size: 11.5px;
  color: var(--app-muted);
}

.detail-alert {
  margin-bottom: 14px;
}

.text-preview {
  margin: 0;
  padding: 16px;
  min-height: 240px;
  max-height: calc(100vh - 280px);
  overflow: auto;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: #f8fafc;
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-note {
  margin: 12px 0 0;
  font-size: 11px;
  color: #94a3b8;
}

@media (max-width: 720px) {
  .page-head {
    flex-direction: column;
  }

  .page-head h1 {
    font-size: 26px;
  }
}
</style>
