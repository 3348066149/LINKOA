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

      <!-- 节点表单只读弹窗 -->
      <el-dialog v-model="formVisible" :title="`${currentNode?.nodeTitle || ''} - 已填内容`" width="min(560px, 92vw)">
        <div v-if="currentNode" class="node-time-bar">🕐 创建：{{ formatTime(currentNode.createTime) }}</div>
        <el-descriptions v-if="currentFormFields.length" :column="1" border>
          <el-descriptions-item v-for="f in currentFormFields" :key="f.id || f.fieldLabel" :label="f.fieldLabel">
            <template v-if="f.fieldType === 'image' && f.fieldValue">
              <el-image
                :src="f.fieldValue.startsWith('http') ? f.fieldValue : `/uploads/${f.fieldValue}`"
                :preview-src-list="[f.fieldValue.startsWith('http') ? f.fieldValue : `/uploads/${f.fieldValue}`]"
                :preview-teleported="true"
                fit="cover"
                style="width: 120px; height: 120px; border-radius: 8px"
              />
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
                <el-image :src="`/uploads/${f.fieldValue}`" :preview-src-list="[`/uploads/${f.fieldValue}`]" :preview-teleported="true" fit="cover" style="width: 100px; height: 100px; border-radius: 6px" />
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
                  <el-image v-if="reviewForm.feedback[f.fieldLabel]" :src="'/uploads/' + reviewForm.feedback[f.fieldLabel]" :preview-src-list="['/uploads/' + reviewForm.feedback[f.fieldLabel]]" :preview-teleported="true" fit="cover" style="width: 120px; height: 120px; border-radius: 6px" />
                  <span v-else class="empty-value">未上传</span>
                </template>
                <span v-else :class="{ 'empty-value': !reviewForm.feedback[f.fieldLabel] }">{{ reviewForm.feedback[f.fieldLabel] || '未填写' }}</span>
              </template>
              <!-- 填写模式 -->
              <template v-else>
                <el-input v-if="f.fieldType === 'text_single'" v-model="reviewForm.feedback[f.fieldLabel]" placeholder="请输入" />
                <el-input v-else-if="f.fieldType === 'text_multi'" v-model="reviewForm.feedback[f.fieldLabel]" type="textarea" :rows="3" placeholder="请输入" />
                <template v-else-if="f.fieldType === 'image'">
                  <el-upload :show-file-list="false" :action="reviewUploadUrl" :data="{projectNodeId: currentNode.id}" :headers="{'Authorization': 'Bearer ' + (userStore.token || '')}" accept="image/*" :before-upload="beforeReviewImageUpload" :on-success="(res) => onReviewImageSuccess(res, f.fieldLabel)" :on-error="onReviewImageError">
                    <el-button size="small" :icon="Picture">上传图片</el-button>
                  </el-upload>
                  <div v-if="reviewForm.feedback[f.fieldLabel]" class="img-preview">
                    <el-image :src="'/uploads/' + reviewForm.feedback[f.fieldLabel]" :preview-src-list="['/uploads/' + reviewForm.feedback[f.fieldLabel]]" :preview-teleported="true" fit="cover" style="width: 120px; height: 120px; border-radius: 6px" />
                    <el-button v-if="!reviewReadonly" link type="danger" size="small" @click="reviewForm.feedback[f.fieldLabel] = ''">删除</el-button>
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
import { submitReview } from '@/api/review'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const detail = ref(null)
const loading = ref(false)

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
const reviewUploadUrl = '/api/review/upload'  // 客户审核专用上传接口（V1.4.20）

// 客户反馈图片上传：el-upload 直接打后端 multipart 接口，回调拿到的是原始响应体。
// 注意后端统一约定 HTTP 状态恒为 200、业务码在 body.code，所以业务失败也会走 on-success，
// 必须自己判断 code 并提示，否则客户点「上传图片」失败时页面毫无反应（V1.4.21 修复）。
function beforeReviewImageUpload(file) {
  if (!file.type || !file.type.startsWith('image/')) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片不能超过 5MB')
    return false
  }
  return true
}

function onReviewImageSuccess(res, fieldKey) {
  const p = res?.data?.path
  if (res?.code !== 200 || !p) {
    ElMessage.error(res?.msg || '图片上传失败，请重试')
    return
  }
  reviewForm.value.feedback[fieldKey] = p
  ElMessage.success('图片上传成功')
}

function onReviewImageError(err) {
  ElMessage.error(err?.message || '图片上传失败，请检查网络后重试')
}

// 项目参与者 / 我方负责人（顿号分隔）
const designerNames = computed(() => (detail.value?.designerList || []).map((d) => d.realName).join('、'))
const contactNames = computed(() => (detail.value?.contactList || []).map((c) => c.customerName).join('、'))

function formatTime(t) { return t ? t.slice(0, 16) : '—' }

async function loadData() {
  loading.value = true
  try {
    detail.value = await projectDetail(route.params.id)
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
