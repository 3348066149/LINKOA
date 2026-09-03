<template>
  <div class="files-page">
    <el-card shadow="never" class="layout-card">
      <div class="files-layout">
        <!-- 左侧：项目列表 -->
        <div class="project-pane">
          <div class="pane-head">
            <el-input v-model="projectKeyword" size="small" placeholder="搜索项目" clearable :prefix-icon="Search" />
          </div>
          <div class="project-list">
            <div
              v-for="p in filteredProjects"
              :key="p.id"
              class="project-item"
              :class="{ active: p.id === selectedProjectId }"
              @click="onSelectProject(p)"
            >
              <div class="project-name">{{ p.projectName }}</div>
              <div class="project-meta">{{ p.customerName || '—' }} · {{ p.projectStatus }}</div>
            </div>
            <el-empty v-if="filteredProjects.length === 0" description="暂无项目" :image-size="60" />
          </div>
        </div>

        <!-- 右侧：文件列表 -->
        <div class="file-pane">
          <div class="file-head">
            <div class="file-title">{{ selectedProject ? `${selectedProject.projectName} 的文件` : '请选择左侧项目' }}</div>
            <div class="file-actions">
              <el-input v-model="fileKeyword" size="small" placeholder="搜索文件名" clearable :prefix-icon="Search" style="width: 200px" />
              <el-button v-if="selectedProjectId" type="primary" size="small" :icon="Upload" @click="openUpload">上传文件</el-button>
            </div>
          </div>
          <ResponsiveTable
            :columns="fileColumns"
            :data="filteredFiles"
            :loading="fileLoading"
            card-title-key="fileName"
            action-key="actions"
            row-key="id"
          >
            <template #nodeTitle="{ row }">{{ row.nodeTitle || '—' }}</template>
            <template #createTime="{ row }">{{ formatTime(row.createTime) }}</template>
            <template #fileSize="{ row }">{{ formatSize(row.fileSize) }}</template>
            <template #actions="{ row }">
              <el-button link type="primary" @click="onDownload(row)">下载</el-button>
              <el-button
                v-if="canDelete(row)"
                link type="danger"
                @click="onDelete(row)"
              >删除</el-button>
            </template>
          </ResponsiveTable>
          <el-empty
            v-if="!fileLoading && selectedProjectId && filteredFiles.length === 0"
            description="该项目暂无文件"
          />
        </div>
      </div>
    </el-card>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传文件" width="min(460px, 92vw)">
      <el-form label-width="80px">
        <el-form-item label="所属节点" required>
          <el-select v-model="uploadForm.projectNodeId" style="width: 100%" placeholder="选择上传到的节点">
            <el-option v-for="n in nodeOptions" :key="n.id" :label="n.nodeTitle" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件" required>
          <el-upload :show-file-list="false" :http-request="doUpload" accept="*/*">
            <el-button type="primary" :loading="uploading" :icon="Upload">选择文件并上传</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload } from '@element-plus/icons-vue'
import { deleteAttachment, downloadUrl, listByProject, uploadAttachment } from '@/api/attachment'
import { listProjects, projectDetail } from '@/api/project'
import { useUserStore } from '@/stores/user'
import ResponsiveTable from '@/components/ResponsiveTable.vue'

const userStore = useUserStore()

// 文件表格列配置
const fileColumns = [
  { prop: 'fileName', label: '文件名', minWidth: 220, ellipsis: true },
  { prop: 'nodeTitle', label: '所属节点', minWidth: 140 },
  { prop: 'uploadUserName', label: '上传人', width: 110 },
  { prop: 'createTime', label: '上传时间', width: 150 },
  { prop: 'fileSize', label: '大小', width: 100 },
  { prop: 'actions', label: '操作', width: 130, fixed: 'right' }
]

const projectKeyword = ref('')
const fileKeyword = ref('')
const projects = ref([])
const selectedProjectId = ref(null)
const selectedProject = computed(() => projects.value.find((p) => p.id === selectedProjectId.value) || null)

const fileLoading = ref(false)
const files = ref([])

const filteredProjects = computed(() => {
  const kw = projectKeyword.value.trim()
  if (!kw) return projects.value
  return projects.value.filter((p) => (p.projectName || '').includes(kw) || (p.customerName || '').includes(kw))
})

const filteredFiles = computed(() => {
  const kw = fileKeyword.value.trim()
  if (!kw) return files.value
  return files.value.filter((f) => (f.fileName || '').includes(kw))
})

function formatTime(t) { return t ? t.slice(0, 16) : '' }
function formatSize(bytes) {
  if (!bytes) return '0B'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`
}
function canDelete(row) {
  // 上传本人或管理员可删（V1.4 管理员可删任意文件）
  return row.uploadUserId === userStore.userInfo?.id || userStore.role === '管理员'
}

async function loadProjects() {
  // 后端 pageSize 上限 200，循环分页拉取全部项目（避免项目数超过单页缺失）
  const all = []
  const pageSize = 200
  let pageNum = 1
  let total = Infinity
  while (all.length < total) {
    const data = await listProjects({ pageNum, pageSize })
    const items = data.items || []
    total = data.total ?? all.length
    all.push(...items)
    if (items.length < pageSize) break
    pageNum += 1
  }
  projects.value = all
  if (projects.value.length && !selectedProjectId.value) {
    onSelectProject(projects.value[0])
  }
}

async function onSelectProject(p) {
  selectedProjectId.value = p.id
  fileLoading.value = true
  try {
    files.value = await listByProject(p.id)
    // 顺带加载节点列表（供上传选节点）
    const detail = await projectDetail(p.id).catch(() => null)
    nodeOptions.value = detail?.nodes || []
  } finally {
    fileLoading.value = false
  }
}

function onDownload(row) {
  window.open(downloadUrl(row.id), '_blank')
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除文件「${row.fileName}」吗？删除后不可恢复！`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteAttachment({ attachmentId: row.id })
  ElMessage.success('已删除')
  files.value = await listByProject(selectedProjectId.value)
}

// ---- 上传 ----
const uploadVisible = ref(false)
const uploading = ref(false)
const nodeOptions = ref([])
const uploadForm = reactive({ projectNodeId: null })

function openUpload() {
  uploadForm.projectNodeId = nodeOptions.value.length ? nodeOptions.value[0].id : null
  uploadVisible.value = true
}

async function doUpload({ file }) {
  if (!uploadForm.projectNodeId) {
    ElMessage.warning('请先选择所属节点')
    return
  }
  uploading.value = true
  try {
    await uploadAttachment(file, selectedProjectId.value, uploadForm.projectNodeId)
    ElMessage.success('上传成功')
    uploadVisible.value = false
    files.value = await listByProject(selectedProjectId.value)
  } finally {
    uploading.value = false
  }
}

onMounted(loadProjects)
</script>

<style scoped>
.files-page { height: calc(100vh - 112px); }
.layout-card { height: 100%; }
.layout-card :deep(.el-card__body) { height: 100%; padding: 0; }
.files-layout { display: flex; height: 100%; }
.project-pane {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
}
.pane-head { padding: 12px; border-bottom: 1px solid #ebeef5; }
.project-list { flex: 1; overflow-y: auto; padding: 8px; }
.project-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
}
.project-item:hover { background: #f5f7fa; }
.project-item.active { background: #ecf5ff; }
.project-name { font-size: 14px; font-weight: bold; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.project-meta { font-size: 12px; color: var(--lk-text-3); margin-top: 2px; }
.file-pane { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.file-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
}
.file-title { font-size: 15px; font-weight: bold; color: #303133; }
.file-actions { display: flex; align-items: center; gap: 10px; }
.file-pane .el-table { flex: 1; }
.file-pane :deep(.rt) { flex: 1; overflow-y: auto; }

/* ---- 移动端：左右栏堆叠，左栏项目列表横向滚动 ---- */
@media (max-width: 767px) {
  .files-page { height: calc(100vh - 76px); }
  .files-layout { flex-direction: column; }
  .project-pane {
    width: 100%;
    height: 150px;
    border-right: none;
    border-bottom: 1px solid #ebeef5;
  }
  .project-list {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 8px;
    -webkit-overflow-scrolling: touch;
  }
  .project-item {
    flex: 0 0 150px;
    margin-bottom: 0;
    border: 1px solid #ebeef5;
  }
  .file-head { flex-wrap: wrap; gap: 8px; }
  .file-actions { width: 100%; }
  .file-actions .el-input { flex: 1; width: auto !important; }
}
</style>
