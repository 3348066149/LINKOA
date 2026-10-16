<template>
  <div class="client-layout">
    <header class="client-header">
      <div class="brand">
        <img class="brand-logo" src="/link-icon.png" alt="青岛领客文化传播有限公司" />
        <span class="brand-name">领客文化 · 客户门户</span>
      </div>
      <div class="header-right">
        <el-tag type="primary" effect="plain" size="small">{{ userStore.userInfo?.companyName || userStore.userInfo?.customerName || '客户' }}</el-tag>
        <span class="user-name">{{ userStore.realName }}</span>
        <el-button size="small" text @click="onLogout">退出登录</el-button>
      </div>
    </header>

    <main v-if="detail" class="client-main">
      <el-button link :icon="Back" class="back-btn" @click="$router.push('/client')">返回我的项目</el-button>

      <!-- 项目概览卡 -->
      <div class="overview-card">
        <div class="ov-head">
          <h2 class="ov-title">{{ detail.projectName }}</h2>
          <el-tag :type="detail.projectStatus === '进行中' ? 'success' : 'info'" effect="dark">{{ detail.projectStatus === '已归档' ? '已结项' : detail.projectStatus }}</el-tag>
        </div>
        <div class="ov-meta">
          <div class="meta-row"><span class="meta-label">项目参与者</span><span class="meta-value">{{ designerNames || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">项目对接人</span><span class="meta-value">{{ contactNames || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">项目描述</span><span class="meta-value">{{ detail.projectDesc || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">立项时间</span><span class="meta-value">{{ formatTime(detail.createTime) }}</span></div>
          <div v-if="detail.stageCount > 0 && detail.activeStagePlanTime" class="deadline-badge" :class="`dl-${deadlineInfo(detail.activeStagePlanTime, detail.projectStatus, detail.activeStageName).type}`">
            {{ deadlineInfo(detail.activeStagePlanTime, detail.projectStatus, detail.activeStageName).label }}
          </div>
        </div>

        <!-- 环节时间线（V1.4.19） -->
        <div v-if="detail.stages && detail.stages.length" class="stage-timeline">
          <div class="stage-title">项目环节</div>
          <div v-for="(s, i) in detail.stages" :key="i" class="stage-item" :class="{ done: s.actualTime }">
            <span class="stage-dot" :class="{ done: s.actualTime, current: !s.actualTime }"></span>
            <div class="stage-info">
              <div class="stage-name">{{ s.stageName }}</div>
              <div class="stage-times">
                <span>预计：{{ s.planTime ? formatTime(s.planTime) : '—' }}</span>
                <span v-if="s.actualTime" class="actual">实际：{{ formatTime(s.actualTime) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 节点进度：画布式拓扑图（只读，客户不能修改） -->
      <h3 class="section-title">流程进度</h3>
      <div v-if="detail.nodes.length" class="topo-wrap">
        <FlowCanvas
          :nodes="detail.nodes"
          :edges="detail.edges"
          readonly
          :deletable="false"
          :selected-node-id="null"
          :presets="[]"
          @node-click="openFormById"
        />
        <div class="topo-tip">仅可查看节点内容与时间，如需修改请联系我方负责人</div>
      </div>
      <el-empty v-else description="该项目暂无节点" />

      <!-- 项目附件（客户查看设计师上传的所有文件） -->
      <h3 class="section-title">项目附件</h3>
      <div v-if="projectAttachments.length" class="attach-grid">
        <div v-for="a in projectAttachments" :key="a.id" class="attach-card">
          <el-image
            v-if="isImage(a.fileName)"
            :src="downloadUrl(a.id)"
            :preview-src-list="[downloadUrl(a.id)]"
            fit="cover"
            class="attach-thumb"
            preview-teleported
          />
          <div v-else-if="isPdf(a.fileName)" class="attach-thumb pdf-thumb" @click="onPreview(a)">
            <span class="file-icon big">PDF</span>
          </div>
          <div v-else-if="isVideo(a.fileName)" class="attach-thumb video-thumb" @click="onPreview(a)">
            <span class="file-icon big">▶</span>
          </div>
          <div v-else class="attach-thumb other-thumb">
            <span class="file-icon big">{{ fileTag(a.fileName) }}</span>
          </div>
          <div class="attach-info">
            <div class="attach-name" :title="a.fileName">{{ a.fileName }}</div>
            <div class="attach-meta">{{ a.nodeTitle || '项目附件' }} · {{ (a.fileSize / 1024 / 1024).toFixed(1) }}MB</div>
          </div>
          <div class="attach-actions">
            <el-button link type="primary" size="small" @click="onPreview(a)">预览</el-button>
            <el-button link type="primary" size="small" @click="window.open(downloadUrl(a.id), '_blank')">下载</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无附件" :image-size="60" />

      <!-- 节点表单只读弹窗 -->
      <el-dialog v-model="formVisible" :title="`${currentNode?.nodeTitle || ''} - 已填内容`" width="min(560px, 92vw)">
        <div v-if="currentNode" class="node-time-bar">🕐 创建：{{ formatTime(currentNode.createTime) }}</div>
        <el-descriptions v-if="currentFormFields.length" :column="1" border>
          <el-descriptions-item v-for="f in currentFormFields" :key="f.id || f.fieldLabel" :label="f.fieldLabel">
            <template v-if="f.fieldType === 'image' && f.fieldValue">
              <!-- 图片：卡片 -->
              <div v-if="parseFiles(f.fieldValue).filter(isImg).length" class="file-preview-grid">
                <div v-for="(path, i) in parseFiles(f.fieldValue).filter(isImg)" :key="'c'+i" class="file-card-sm">
                  <el-image
                    :src="fileUrl(path)"
                    :preview-src-list="parseFiles(f.fieldValue).filter(isImg).map(fileUrl)"
                    :preview-teleported="true"
                    fit="cover"
                    class="file-thumb-sm"
                  />
                  <div class="file-card-name-sm" :title="fileName(path)">{{ fileName(path) }}</div>
                </div>
              </div>
              <!-- 其他：列表 -->
              <div v-if="parseFiles(f.fieldValue).filter(p => !isImg(p)).length" class="file-list-sm">
                <div v-for="(path, i) in parseFiles(f.fieldValue).filter(p => !isImg(p))" :key="'l'+i" class="file-item-sm">
                  <span class="ft-badge" :class="extOf(path)">{{ fileTag(path) }}</span>
                  <span class="file-item-name-sm" :title="fileName(path)">{{ fileName(path) }}</span>
                  <el-icon class="file-item-icon" @click="window.open(fileUrl(path), '_blank')"><Download /></el-icon>
                </div>
              </div>
              <div v-if="f.updateTime" class="image-time">🕐 上传时间：{{ formatTime(f.updateTime) }}</div>
            </template>
            <template v-else-if="f.fieldType === 'select' && Array.isArray(f.fieldValueParsed)">
              <el-tag v-for="(opt, i) in f.fieldValueParsed" :key="i" size="small" style="margin-right: 6px">{{ opt }}</el-tag>
            </template>
            <template v-else-if="f.fieldType === 'link' && f.fieldValue">
              <a
                :href="/^https?:\/\//i.test(f.fieldValue) ? f.fieldValue : `https://${f.fieldValue}`"
                target="_blank"
                rel="noopener"
                class="link-value"
              >{{ f.fieldValue }}</a>
            </template>
            <template v-else>
              <span :class="{ 'empty-value': !f.fieldValue }">{{ f.fieldValue || '未填写' }}</span>
            </template>
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="该节点暂无表单内容" :image-size="60" />
        <div class="readonly-tip"><el-icon><Lock /></el-icon> 当前为只读视图，如需修改请联系我方负责人</div>
      </el-dialog>

      <!-- 客户审核弹窗（V1.4.20 完善：已审只读 / 未审可填） -->
      <el-dialog v-model="reviewVisible" :title="reviewReadonly ? `审核结果：${currentNode?.nodeTitle || ''}` : `审核：${currentNode?.nodeTitle || ''}`" width="min(600px, 92vw)">
        <div v-if="currentNode" class="review-box">
          <!-- 已审顶部提示 -->
          <div v-if="reviewReadonly" class="review-done-tip">
            ✔ 您已于 {{ currentNode.reviewResult?.time || '' }} 提交审核，如需修改请联系我方管理员
          </div>
          <div v-else class="review-tip">请查看下方内容后选择审核结论并填写反馈，提交后不可修改。</div>

          <!-- 我方提交内容 -->
          <div class="review-section-title">设计方提交内容</div>
          <el-descriptions v-if="currentFormFields.length" :column="1" border size="small" class="review-fields">
            <el-descriptions-item v-for="f in currentFormFields" :key="f.id" :label="f.fieldLabel">
              <template v-if="f.fieldType === 'image' && f.fieldValue">
                <div class="file-preview-grid">
                  <div v-for="path in parseFiles(f.fieldValue).filter(isImg)" :key="'c'+path" class="file-card-sm">
                    <el-image :src="fileUrl(path)" :preview-src-list="parseFiles(f.fieldValue).filter(isImg).map(fileUrl)" :preview-teleported="true" fit="cover" class="file-thumb-sm" />
                    <div class="file-card-name-sm" :title="fileName(path)">{{ fileName(path) }}</div>
                  </div>
                </div>
                <div v-for="path in parseFiles(f.fieldValue).filter(p => !isImg(p))" :key="'l'+path" class="file-item-sm">
                  <span class="ft-badge" :class="extOf(path)">{{ fileTag(path) }}</span>
                  <span class="file-item-name-sm" :title="fileName(path)">{{ fileName(path) }}</span>
                  <el-icon class="file-item-icon" @click="window.open(fileUrl(path), '_blank')"><Download /></el-icon>
                </div>
              </template>
              <template v-else>
                <span :class="{ 'empty-value': !f.fieldValue }">{{ f.fieldValue || '未填写' }}</span>
              </template>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无提交内容" :image-size="50" />

          <!-- 审核结论 -->
          <div class="review-section-title">审核结论</div>
          <div class="review-options">
            <el-radio-group v-model="reviewForm.option" :disabled="reviewReadonly">
              <el-radio v-for="opt in (currentNode.reviewOptions || [])" :key="opt" :value="opt">{{ opt }}</el-radio>
            </el-radio-group>
          </div>

          <!-- 客户反馈字段 -->
          <template v-if="(currentNode.clientReviewFields || []).length">
            <div class="review-section-title">我的反馈</div>
            <div v-for="f in currentNode.clientReviewFields" :key="f.fieldLabel" class="feedback-field">
              <div class="feedback-label">{{ f.fieldLabel }}</div>
              <!-- 只读模式 -->
              <template v-if="reviewReadonly">
                <template v-if="f.fieldType === 'image'">
                  <div v-if="reviewForm.feedback[f.fieldLabel]" class="file-preview-grid">
                    <div v-for="path in parseFiles(reviewForm.feedback[f.fieldLabel]).filter(isImg)" :key="'c'+path" class="file-card-sm">
                      <el-image :src="fileUrl(path)" :preview-src-list="parseFiles(reviewForm.feedback[f.fieldLabel]).filter(isImg).map(fileUrl)" :preview-teleported="true" fit="cover" class="file-thumb-sm" />
                      <div class="file-card-name-sm" :title="fileName(path)">{{ fileName(path) }}</div>
                    </div>
                  </div>
                  <div v-for="path in parseFiles(reviewForm.feedback[f.fieldLabel]).filter(p => !isImg(p))" :key="'l'+path" class="file-item-sm">
                    <span class="ft-badge" :class="extOf(path)">{{ fileTag(path) }}</span>
                    <span class="file-item-name-sm" :title="fileName(path)">{{ fileName(path) }}</span>
                    <el-icon class="file-item-icon" @click="window.open(fileUrl(path), '_blank')"><Download /></el-icon>
                  </div>
                  <span v-if="!reviewForm.feedback[f.fieldLabel]" class="empty-value">未上传</span>
                </template>
                <span v-else :class="{ 'empty-value': !reviewForm.feedback[f.fieldLabel] }">{{ reviewForm.feedback[f.fieldLabel] || '未填写' }}</span>
              </template>
              <!-- 填写模式 -->
              <template v-else>
                <el-input v-if="f.fieldType === 'text_single'" v-model="reviewForm.feedback[f.fieldLabel]" placeholder="请输入" />
                <el-input v-else-if="f.fieldType === 'text_multi'" v-model="reviewForm.feedback[f.fieldLabel]" type="textarea" :rows="3" placeholder="请输入" />
                <template v-else-if="f.fieldType === 'image'">
                  <el-upload :show-file-list="false" :before-upload="(file) => onReviewUploadFile(file, f.fieldLabel)" accept="*/*" multiple>
                    <el-button size="small" :icon="Picture">上传文件</el-button>
                  </el-upload>
                  <div v-if="reviewForm.feedback[f.fieldLabel]" class="img-preview">
                    <div class="file-preview-grid">
                      <div v-for="path in parseFiles(reviewForm.feedback[f.fieldLabel]).filter(isImg)" :key="'c'+path" class="file-card-sm">
                        <el-image :src="fileUrl(path)" :preview-src-list="parseFiles(reviewForm.feedback[f.fieldLabel]).filter(isImg).map(fileUrl)" :preview-teleported="true" fit="cover" class="file-thumb-sm" />
                        <div class="file-card-name-sm" :title="fileName(path)">{{ fileName(path) }}</div>
                      </div>
                    </div>
                    <div v-for="path in parseFiles(reviewForm.feedback[f.fieldLabel]).filter(p => !isImg(p))" :key="'l'+path" class="file-item-sm">
                      <span class="ft-badge" :class="extOf(path)">{{ fileTag(path) }}</span>
                      <span class="file-item-name-sm" :title="fileName(path)">{{ fileName(path) }}</span>
                      <el-icon class="file-item-icon" @click="window.open(fileUrl(path), '_blank')"><Download /></el-icon>
                      <el-icon class="file-item-icon danger" @click="removeReviewFile(f.fieldLabel, path)"><Delete /></el-icon>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </template>

          <!-- 批注 -->
          <div class="review-section-title">批注{{ reviewReadonly ? '' : '（选填）' }}</div>
          <el-input v-model="reviewForm.comment" type="textarea" :rows="3" maxlength="500" show-word-limit :disabled="reviewReadonly" />

          <!-- 已审签名 -->
          <div v-if="reviewReadonly" class="review-sign">
            审核人：{{ currentNode.reviewResult?.reviewer || '—' }}　提交时间：{{ currentNode.reviewResult?.time || '' }}
          </div>
        </div>
        <template #footer>
          <el-button @click="reviewVisible = false">{{ reviewReadonly ? '关闭' : '取消' }}</el-button>
          <el-button v-if="!reviewReadonly" type="primary" :loading="submittingReview" @click="onSubmitReview">提交审核</el-button>
        </template>
      </el-dialog>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Lock, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FlowCanvas from '@/components/FlowCanvas.vue'
import { projectDetail } from '@/api/project'
import { getNodeForm } from '@/api/projectNode'
import { submitReview, uploadReviewFile } from '@/api/review'
import { listByProject, downloadUrl } from '@/api/attachment'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const detail = ref(null)
const loading = ref(false)
const projectAttachments = ref([])

const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
const PDF_EXTS = ['pdf']
const VIDEO_EXTS = ['mp4', 'webm', 'ogg']
function isImage(name) { return IMAGE_EXTS.includes((name || '').split('.').pop().toLowerCase()) }
function isPdf(name) { return PDF_EXTS.includes((name || '').split('.').pop().toLowerCase()) }
function isVideo(name) { return VIDEO_EXTS.includes((name || '').split('.').pop().toLowerCase()) }
function fileTag(name) {
  const ext = (name.split('/').pop() || name.split('.').pop() || '').toLowerCase()
  const map = { psd: 'PSD', ai: 'AI', zip: 'ZIP', rar: 'ZIP', pdf: 'PDF', doc: 'DOC', docx: 'DOC', xls: 'XLS', xlsx: 'XLS', mp4: 'MP4', ppt: 'PPT', pptx: 'PPT', mp3: 'MP3' }
  return map[ext] || 'FILE'
}
// 表单文件值解析：兼容 JSON 数组（多文件）与旧单值字符串。
// 必须过滤 null/空串/非字符串项，否则 link 预览会对 null 调 .split() 抛异常导致白屏。
function parseFiles(v) {
  if (!v) return []
  let arr
  try {
    const parsed = JSON.parse(v)
    arr = Array.isArray(parsed) ? parsed : [parsed]
  } catch {
    arr = [v]
  }
  return arr.filter((p) => typeof p === 'string' && p.trim() !== '')
}
function fileUrl(p) { return p.startsWith('http') ? p : `/uploads/${p.replace(/^uploads\//, '')}` }
function isImg(p) { return ['png','jpg','jpeg','gif','bmp','webp'].includes((p.split('.').pop()||'').toLowerCase()) }
function canPreviewFile(p) { return isImg(p) || ['pdf','mp4','webm'].includes((p.split('.').pop()||'').toLowerCase()) }
function fileName(p) {
  const n = p.split('/').pop() || p
  // 新格式：{uuid}_{原文件名}，去掉 uuid_ 前缀
  const i = n.indexOf('_')
  if (i > 0 && /^[0-9a-f]{20,}$/.test(n.slice(0, i))) return n.slice(i + 1)
  // 旧数据：没有 uuid 前缀，直接返回文件名
  return n
}
function extOf(p) { return (p.split('.').pop()||'').toLowerCase() }
function onPreview(a) {
  const url = downloadUrl(a.id)
  if (isPdf(a.fileName) || isVideo(a.fileName) || isImage(a.fileName)) {
    window.open(url, '_blank')
  } else {
    ElMessage.info('该文件类型不支持在线预览，请下载查看')
  }
}

// 表单只读
const formVisible = ref(false)
const currentNode = ref(null)
const currentFormFields = ref([])

// 审核弹窗（V1.4.19）
const reviewVisible = ref(false)
const reviewReadonly = ref(false)  // 已审时只读展示
const reviewForm = ref({ option: '', comment: '', feedback: {} })
const submittedFeedbackFields = ref([])  // 已审时客户提交的反馈字段值
const submittingReview = ref(false)

// 客户审核多文件上传：必须走客户专用接口 /review/upload。
// 客户账号调用设计师侧的 /projectNode/formImage/upload 会被 require_not_customer 拦成 403，
// 所以这里不能复用 uploadFormImage（V1.4.22 修复）。
async function onReviewUploadFile(file, fieldKey) {
  const nodeId = currentNode.value?.id
  if (!nodeId) {
    ElMessage.error('节点信息缺失，请刷新后重试')
    return false
  }
  try {
    const data = await uploadReviewFile(file, nodeId)
    const path = data?.path || data?.imagePath
    if (!path) {
      ElMessage.error('文件上传失败，请重试')
      return false
    }
    const existing = parseFiles(reviewForm.value.feedback[fieldKey] || '[]')
    existing.push(path)
    reviewForm.value.feedback[fieldKey] = JSON.stringify(existing)
    ElMessage.success('文件已上传')
  } catch {
    ElMessage.error('文件上传失败，请检查网络后重试')
  }
  return false
}

function removeReviewFile(fieldKey, path) {
  const arr = parseFiles(reviewForm.value.feedback[fieldKey] || '[]').filter(p => p !== path)
  reviewForm.value.feedback[fieldKey] = arr.length ? JSON.stringify(arr) : ''
}

// 项目参与者 / 我方负责人（顿号分隔）
const designerNames = computed(() => (detail.value?.designerList || []).map((d) => d.realName).join('、'))
const contactNames = computed(() => (detail.value?.contactList || []).map((c) => c.customerName).join('、'))

function formatTime(t) { return t ? t.slice(0, 16) : '—' }

async function loadData() {
  loading.value = true
  try {
    detail.value = await projectDetail(route.params.id)
    projectAttachments.value = await listByProject(route.params.id) || []
  } finally {
    loading.value = false
  }
}

// 客户点拓扑图中的节点：
// - 审核节点 → 打开审核弹窗（未审可填 / 已审只读）
// - 其他 → 只读查看表单内容
async function openFormById(nodeId) {
  const node = detail.value?.nodes?.find((n) => n.id === nodeId)
  if (!node) return
  if (node.isReview) {
    currentNode.value = node
    reviewForm.value = { option: '', comment: '', feedback: {} }
    submittedFeedbackFields.value = []
    reviewReadonly.value = !!node.reviewResult
    reviewVisible.value = true
    if (node.reviewResult) {
      reviewForm.value.option = node.reviewResult.option || ''
      reviewForm.value.comment = node.reviewResult.comment || ''
    }
    // 拉取所有表单字段（含 designer 和 client 两侧）
    try {
      const data = await getNodeForm(node.id)
      const all = (data.fields || []).map((f) => ({
        ...f,
        fieldValueParsed: f.fieldType === 'select' && f.fieldValue ? safeParse(f.fieldValue) : null
      }))
      currentFormFields.value = all.filter((f) => f.side !== 'client')
      submittedFeedbackFields.value = all.filter((f) => f.side === 'client')
      // 已审时把客户反馈值回填到 reviewForm（只读展示图片用）
      if (node.reviewResult) {
        for (const f of submittedFeedbackFields.value) {
          reviewForm.value.feedback[f.fieldLabel] = f.fieldValue
        }
      }
    } catch {
      currentFormFields.value = []
      submittedFeedbackFields.value = []
    }
    return
  }
  currentNode.value = node
  currentFormFields.value = []
  formVisible.value = true
  try {
    const data = await getNodeForm(node.id)
    currentFormFields.value = (data.fields || []).map((f) => ({
      ...f,
      fieldValueParsed: f.fieldType === 'select' && f.fieldValue ? safeParse(f.fieldValue) : null
    })).filter((f) => f.side !== 'client')
  } catch {
    currentFormFields.value = []
  }
}

async function onSubmitReview() {
  if (!reviewForm.value.option) {
    ElMessage.warning('请选择一个审核结论')
    return
  }
  submittingReview.value = true
  try {
    const feedbackFields = (currentNode.value.clientReviewFields || []).map((f) => ({
      fieldLabel: f.fieldLabel,
      fieldType: f.fieldType,
      fieldValue: reviewForm.value.feedback[f.fieldLabel] || null
    }))
    await submitReview({
      projectNodeId: currentNode.value.id,
      option: reviewForm.value.option,
      comment: reviewForm.value.comment || null,
      feedbackFields
    })
    ElMessage.success('审核已提交')
    reviewVisible.value = false
    // 刷新详情，节点状态变已审
    detail.value = await projectDetail(route.params.id)
  } finally {
    submittingReview.value = false
  }
}

function safeParse(v) {
  try { return JSON.parse(v) } catch { return null }
}

function onLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(loadData)
</script>

<style scoped>
/* 弹窗溢出修复：长文本/长字段值必须在弹窗内换行或滚动，不得撑破对话框铺到页面上 */
.client-layout :deep(.el-dialog) {
  max-width: 92vw;
}
.client-layout :deep(.el-dialog .el-dialog__body) {
  max-height: 68vh;
  overflow-y: auto;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.client-layout :deep(.el-dialog .el-descriptions) {
  width: 100%;
  table-layout: fixed;
}
.client-layout :deep(.el-dialog .el-descriptions__label),
.client-layout :deep(.el-dialog .el-descriptions__content) {
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: normal;
}
.client-layout :deep(.el-dialog .el-descriptions__cell) {
  max-width: 0; /* 配合 table-layout:fixed，强制单元格按列宽换行而非撑开 */
}
.client-layout :deep(.el-dialog .link-value) {
  overflow-wrap: anywhere;
  word-break: break-all;
}

.client-layout { min-height: 100vh; background: var(--lk-bg, #f5f7fa); display: flex; flex-direction: column; }
.client-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; height: 60px; background: #fff;
  border-bottom: 1px solid var(--lk-border, #ebeef5);
  position: sticky; top: 0; z-index: 10;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { height: 24px; width: auto; display: block; }
.brand-name { font-size: 16px; font-weight: 700; color: var(--lk-text-1, #303133); }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: var(--lk-text-2, #606266); }

.client-main { flex: 1; padding: 20px 28px 40px; max-width: 960px; width: 100%; margin: 0 auto; box-sizing: border-box; }
.back-btn { margin-bottom: 12px; }

.overview-card { background: #fff; border: 1px solid var(--lk-border, #ebeef5); border-radius: 12px; padding: 20px; }
.ov-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.ov-title { font-size: 20px; font-weight: 700; color: var(--lk-text-1, #303133); margin: 0; word-break: break-all; }
.ov-meta { display: flex; flex-direction: column; gap: 8px; }
.meta-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.5; }
.meta-label { color: var(--lk-text-3, #6f737a); flex-shrink: 0; min-width: 64px; }
.meta-value { color: var(--lk-text-1, #303133); word-break: break-all; }
.deadline-badge {
  display: inline-flex; align-items: center; margin-top: 6px;
  padding: 4px 14px; border-radius: 999px; color: #fff;
  font-size: 14px; font-weight: 700;
}
.dl-success { background: #909399; }
.dl-primary { background: var(--lk-primary, #409eff); }
.dl-warning { background: var(--lk-warning, #e6a23c); }
.dl-danger { background: var(--lk-danger, #f56c6c); animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.18); } }

.section-title { font-size: 17px; font-weight: 700; color: var(--lk-text-1, #303133); margin: 24px 0 14px; }

/* 画布式拓扑图（客户只读） */
.topo-wrap {
  background: #fff; border: 1px solid var(--lk-border, #ebeef5); border-radius: 12px;
  overflow: hidden; height: 480px; position: relative;
}
.topo-wrap .flow-canvas-wrapper { height: 100%; }
.topo-tip {
  position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.92); border: 1px solid var(--lk-border, #ebeef5);
  color: var(--lk-text-3, #6f737a); font-size: 12px; padding: 4px 12px; border-radius: 999px;
  white-space: nowrap; pointer-events: none; z-index: 5;
}
.node-time-bar { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-bottom: 12px; }

/* 环节时间线（V1.4.19） */
.stage-timeline { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--lk-border, #ebeef5); }
.stage-title { font-size: 13px; font-weight: 700; color: var(--lk-text-2, #606266); margin-bottom: 10px; }
.stage-item { display: flex; gap: 10px; padding: 6px 0; align-items: flex-start; }
.stage-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
.stage-dot.current { background: var(--lk-primary, #409eff); box-shadow: 0 0 0 4px rgba(64,158,255,0.15); }
.stage-dot.done { background: var(--lk-success, #67c23a); }
.stage-info { flex: 1; }
.stage-name { font-size: 13px; color: var(--lk-text-1, #303133); font-weight: 600; }
.stage-times { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 2px; display: flex; gap: 12px; }
.stage-times .actual { color: var(--lk-success, #67c23a); }

.empty-value { color: var(--lk-text-3, #6f737a); }
.image-time { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 6px; }
.link-value { color: var(--lk-primary, #409eff); word-break: break-all; }
.readonly-tip {
  margin-top: 12px; font-size: 12px; color: var(--lk-text-3, #6f737a);
  display: flex; align-items: center; gap: 4px;
}

/* 客户审核弹窗（V1.4.19） */
.review-box { display: flex; flex-direction: column; gap: 10px; }
.review-tip { font-size: 13px; color: var(--lk-warning, #e6a23c); background: #fdf6ec; padding: 8px 12px; border-radius: 6px; }
.review-done-tip { font-size: 13px; color: #67c23a; background: #f0f9eb; padding: 8px 12px; border-radius: 6px; }
.review-section-title { font-size: 13px; font-weight: 700; color: var(--lk-text-1, #303133); border-left: 3px solid var(--lk-primary, #409eff); padding-left: 8px; margin-top: 6px; }
.review-fields { margin-bottom: 4px; }
.review-options { padding: 4px 0; }
.review-options .el-radio { margin-right: 16px; }
.feedback-field { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; border-bottom: 1px dashed #ebeef5; }
.feedback-label { font-size: 12px; color: var(--lk-text-2, #606266); }
.img-preview { display: flex; align-items: flex-end; gap: 10px; margin-top: 6px; }
.review-sign { font-size: 12px; color: var(--lk-text-3, #909399); text-align: right; margin-top: 6px; }

/* 项目附件网格卡片 */
.attach-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
.attach-card { border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; background: #fff; transition: box-shadow .2s; }
.attach-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.attach-thumb { width: 100%; height: 100px; object-fit: cover; display: flex; align-items: center; justify-content: center; cursor: pointer; background: #f5f7fa; }
.file-icon { font-size: 14px; font-weight: 600; color: #909399; }
.file-icon.big { font-size: 18px; }
.attach-info { padding: 8px; }
.attach-name { font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.attach-meta { font-size: 11px; color: var(--lk-text-3, #6f737a); margin-top: 2px; }
.attach-actions { padding: 0 8px 8px; display: flex; gap: 4px; }

.file-preview-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.file-card-sm { position: relative; width: 80px; margin-bottom: 18px; }
.file-thumb-sm { width: 80px; height: 80px; border-radius: 6px; object-fit: cover; display: block; }
.file-thumb-sm-icon { display: flex; align-items: center; justify-content: center; background: #f5f7fa; cursor: pointer; }
.file-card-name-sm { font-size: 10px; color: #909399; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center; margin-top: 2px; }
.ft-badge { font-size: 10px; font-weight: 700; color: #fff; padding: 2px 6px; border-radius: 3px; background: #909399; }
.ft-badge.small { font-size: 9px; padding: 1px 4px; }

.file-list-sm { margin-bottom: 6px; }
.file-item-sm { display: flex; align-items: center; gap: 6px; padding: 4px 8px; border: 1px solid #e4e7ed; border-radius: 4px; margin-bottom: 3px; background: #fafafa; }
.file-item-name-sm { flex: 1; font-size: 12px; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-item-icon { cursor: pointer; color: #909399; font-size: 13px; }
.file-item-icon:hover { color: #409eff; }

/* 移动端窄屏适配：防止品牌标题竖排换行 */
@media (max-width: 768px) {
  .client-header { padding: 0 12px; height: 52px; }
  .brand { gap: 6px; min-width: 0; }
  .brand-name { white-space: nowrap; font-size: 14px; }
  .header-right { gap: 6px; min-width: 0; }
  .header-right :deep(.el-tag) { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .user-name { display: none; }
  .client-main { padding: 16px 12px; }
}

</style>
