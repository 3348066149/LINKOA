<template>
  <div class="detail-page">
    <!-- 顶部控制栏（PRD 9.5） -->
    <el-card class="top-bar" shadow="never">
      <div class="top-left">
        <span class="project-name">{{ detail.projectName }}</span>
        <el-tag :type="isArchived ? 'info' : 'success'" effect="dark">{{ detail.projectStatus }}</el-tag>
        <span v-if="detail.expectTime" class="expect-time">预计截止：{{ formatTime(detail.expectTime) }}</span>
        <el-tag
          v-if="deadlineInfo(detail.expectTime, detail.projectStatus)"
          :type="deadlineInfo(detail.expectTime, detail.projectStatus).type"
          effect="dark"
          round
        >⏳ {{ deadlineInfo(detail.expectTime, detail.projectStatus).label }}</el-tag>
      </div>
      <div class="top-actions">
        <el-button
          size="small"
          type="primary"
          :icon="Check"
          :disabled="!selectedNodeId || isArchived"
          :loading="savingAll"
          @click="saveSelectedNode"
        >保存</el-button>
        <template v-if="canWrite">
          <el-button size="small" :icon="Edit" @click="openEditBase">编辑基础信息</el-button>
          <el-button v-if="!isArchived" size="small" type="warning" :icon="Folder" @click="onArchive">归档</el-button>
          <el-button v-else size="small" type="success" :icon="FolderOpened" @click="onUnArchive">取消归档</el-button>
          <el-button size="small" type="danger" :icon="Delete" @click="onDeleteProject">删除</el-button>
        </template>
      </div>
    </el-card>

    <!-- 归档提示条 -->
    <el-alert
      v-if="isArchived"
      title="📁 当前项目已归档（只读查看模式）"
      type="warning"
      :closable="false"
      class="archive-banner"
    />

    <div class="content-area">
      <!-- 左侧 70% 画布 -->
      <div class="canvas-area">
        <FlowCanvas
          ref="canvasRef"
          :nodes="nodes"
          :edges="edges"
          :readonly="isArchived"
          :selected-node-id="selectedNodeId"
          :presets="nodeTemplates"
          @node-click="onNodeClick"
          @pane-click="onDeselect"
          @add-preset="onAddPreset"
          @add-connected="onAddConnected"
          @node-delete="onDeleteNode"
          @nodes-delete="onDeleteNodes"
          @positions-change="onPositionsChange"
          @connect="onConnect"
          @edge-remove="onEdgeRemove"
        />
      </div>

      <!-- 右侧 30% 双态面板 -->
      <div class="panel-area">
        <!-- 状态 B：选中节点（节点工作台） -->
        <el-card v-if="selectedNode" shadow="never" class="panel-card">
          <div class="panel-header">
            <span class="panel-title">{{ selectedNode.nodeTitle }}</span>
            <el-button link :icon="Close" @click="onDeselect" />
          </div>
          <el-tabs v-model="nodeTab">
            <el-tab-pane label="表单" name="form">
              <el-form label-position="top">
                <el-form-item label="节点类型">
                  <!-- 节点类型固定为节点库预设，不可改名 -->
                  <el-input :model-value="selectedNode.nodeTitle" disabled />
                </el-form-item>
              </el-form>
              <DynamicForm
                ref="dynamicFormRef"
                :fields="formFields"
                :disabled="isArchived"
                :saving="savingForm"
                @save="onSaveForm"
              />
            </el-tab-pane>
            <el-tab-pane label="附件" name="attachment">
              <div class="attach-header">
                <el-upload
                  v-if="!isArchived"
                  :show-file-list="false"
                  :http-request="onUpload"
                  accept="*/*"
                >
                  <el-button type="primary" size="small" :icon="Upload" :loading="uploading">上传附件</el-button>
                </el-upload>
              </div>
              <div v-if="attachments.length === 0" class="empty-text">暂无附件</div>
              <div v-for="a in attachments" :key="a.id" class="attach-item">
                <!-- 图片缩略图 + 大图预览 -->
                <el-image
                  v-if="isImage(a.fileName)"
                  :src="downloadUrl(a.id)"
                  :preview-src-list="[downloadUrl(a.id)]"
                  fit="cover"
                  class="attach-thumb"
                  preview-teleported
                />
                <span v-else class="file-icon">{{ fileIcon(a.fileName) }}</span>
                <div class="attach-info">
                  <div class="attach-name" :title="a.fileName">{{ a.fileName }}</div>
                  <div class="attach-meta">{{ a.uploadUserName }} · {{ formatSize(a.fileSize) }} · {{ formatTime(a.createTime) }}</div>
                </div>
                <div class="attach-actions">
                  <el-button link type="primary" size="small" @click="onDownload(a)">下载</el-button>
                  <el-button
                    v-if="!isArchived && (a.uploadUserId === userStore.userInfo?.id || userStore.role === '管理员')"
                    link type="danger" size="small"
                    @click="onDeleteAttachment(a)"
                  >删除</el-button>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>

        <!-- 状态 A：未选中节点（项目级面板） -->
        <el-card v-else shadow="never" class="panel-card">
          <el-tabs v-model="projectTab">
            <el-tab-pane label="项目概览" name="overview">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="关联客户">{{ detail.customerName }}</el-descriptions-item>
                <el-descriptions-item label="创建人">{{ detail.createUserName }}</el-descriptions-item>
                <el-descriptions-item label="创建时间">{{ formatTime(detail.createTime) }}</el-descriptions-item>
                <el-descriptions-item label="项目描述">{{ detail.projectDesc || '—' }}</el-descriptions-item>
              </el-descriptions>
              <el-divider content-position="left">项目参与人</el-divider>
              <div v-if="detail.designerList?.length" class="designer-list">
                <el-tag v-for="d in detail.designerList" :key="d.userId" class="designer-tag">{{ d.realName }}</el-tag>
              </div>
              <div v-else class="empty-text">未关联参与人</div>
            </el-tab-pane>

            <el-tab-pane label="项目讨论" name="comment">
              <div class="comment-input">
                <el-input
                  v-model="newComment"
                  type="textarea"
                  :rows="2"
                  :disabled="isArchived"
                  placeholder="发表评论..."
                />
                <el-button
                  type="primary" size="small" :disabled="isArchived || !newComment.trim()"
                  :loading="commenting" @click="onAddComment"
                >发表</el-button>
              </div>
              <div v-if="comments.length === 0" class="empty-text">暂无评论</div>
              <div v-for="c in comments" :key="c.id" class="comment-item">
                <div class="comment-head">
                  <span class="comment-user">{{ c.createUserName }}</span>
                  <span class="comment-time">{{ formatTime(c.createTime) }}</span>
                  <el-button
                    v-if="!isArchived && c.createUserId === userStore.userInfo?.id"
                    link type="danger" size="small"
                    @click="onDeleteComment(c)"
                  >删除</el-button>
                </div>
                <div class="comment-content">{{ c.content }}</div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="客户评价" name="evaluation">
              <el-alert
                v-if="evaluation && evalLowScore"
                title="低分预警：任一单项评分 ≤ 2 星，请关注并复盘"
                type="error"
                :closable="false"
                show-icon
                class="eval-low-alert"
              />
              <div v-if="evaluation" class="eval-block">
                <EvaluationStars :evaluation="evaluation" />
              </div>
              <div v-else class="empty-text">客户暂未评价</div>

              <template v-if="evaluation">
                <el-divider content-position="left">反思 / 总结</el-divider>
                <div class="reflection-box">
                  <el-input
                    v-model="reflectionDraft"
                    type="textarea"
                    :rows="4"
                    maxlength="5000"
                    show-word-limit
                    placeholder="填写内部复盘总结（客户不可见）"
                  />
                  <div v-if="evaluation.reflectionTime" class="reflection-meta">
                    上次更新：{{ evaluation.reflectionUserName }} · {{ formatTime(evaluation.reflectionTime) }}
                  </div>
                  <el-button type="primary" size="small" :loading="savingReflection" @click="onSaveReflection">保存反思</el-button>
                </div>
              </template>
            </el-tab-pane>

            <el-tab-pane label="操作记录" name="log">
              <el-timeline v-if="logs.length">
                <el-timeline-item v-for="l in logs" :key="l.id" :timestamp="formatTime(l.operTime)" placement="top">
                  <span class="log-user">{{ l.operUserName }}</span> {{ l.operDesc }}
                </el-timeline-item>
              </el-timeline>
              <div v-else class="empty-text">暂无操作记录</div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </div>

    <!-- 编辑基础信息弹窗 -->
    <el-dialog v-model="editBaseVisible" title="编辑项目基础信息" width="min(560px, 92vw)">
      <el-form :model="baseForm" label-width="90px">
        <el-form-item label="项目名称" required>
          <el-input v-model="baseForm.projectName" maxlength="256" />
        </el-form-item>
        <el-form-item label="客户单位" required>
          <el-select v-model="baseForm.categoryId" placeholder="请选择客户单位" style="width: 100%" @change="onBaseCategoryChange">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户对接人" required>
          <el-select v-model="baseForm.contactCustomerIds" multiple placeholder="选择该单位下的对接人（可多选）" style="width: 100%" :disabled="!baseForm.categoryId">
            <el-option v-for="c in contactsOf(baseForm.categoryId)" :key="c.id" :label="c.customerName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="baseForm.projectDesc" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="预计截止时间">
          <el-date-picker v-model="baseForm.expectTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="项目参与人">
          <!-- 仅管理员可取全量用户列表；其他角色保持现有关联不变 -->
          <el-select v-if="userStore.role === '管理员'" v-model="baseForm.designerRelUserIdList" multiple style="width: 100%">
            <el-option v-for="u in designerOptions" :key="u.id" :label="u.realName" :value="u.id" />
          </el-select>
          <div v-else>
            <el-tag v-for="d in detail.designerList" :key="d.userId" class="designer-tag">{{ d.realName }}</el-tag>
            <span class="empty-text">（仅管理员可调整）</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editBaseVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingBase" @click="submitBase">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close, Delete, Edit, Folder, FolderOpened, Upload } from '@element-plus/icons-vue'
import DynamicForm from '@/components/DynamicForm.vue'
import FlowCanvas from '@/components/FlowCanvas.vue'
import EvaluationStars from '@/components/EvaluationStars.vue'
import { deleteAttachment, downloadUrl, listAttachments, uploadAttachment } from '@/api/attachment'
import { addComment, deleteComment, listComments } from '@/api/comment'
import { getEvaluation, saveReflection } from '@/api/evaluation'
import { listCategories, listCustomers } from '@/api/customer'
import { projectLogs } from '@/api/log'
import { addEdge, addNode, batchUpdatePositions, deleteEdge, deleteNode, getNodeForm, saveFormValue } from '@/api/projectNode'
import { archiveProject, deleteProject, projectDetail, unArchiveProject, updateProjectBase } from '@/api/project'
import { listUsers } from '@/api/sysUser'
import { listNodeTemplates } from '@/api/nodeTemplate'
import { useMessageStore } from '@/stores/message'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const messageStore = useMessageStore()

const projectId = Number(route.params.id)
const canWrite = computed(() => ['管理员'].includes(userStore.role))
const isArchived = computed(() => detail.projectStatus === '已归档')

const detail = ref({})
const nodes = ref([])
const edges = ref([])
const selectedNodeId = ref(null)
const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) || null)

const nodeTab = ref('form')
const projectTab = ref('overview')

const canvasRef = ref(null)

function formatTime(t) { return t ? t.slice(0, 16) : '' }
function formatSize(bytes) {
  if (!bytes) return '0B'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`
}
const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg']
function isImage(name) { return IMAGE_EXTS.includes((name || '').split('.').pop().toLowerCase()) }
function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  const map = { psd: '🎨', ai: '🎨', zip: '📦', rar: '📦', pdf: '📕', doc: '📘', docx: '📘', xls: '📗', xlsx: '📗', mp4: '🎬' }
  return map[ext] || '📄'
}

// ---- 数据加载 ----
async function loadDetail() {
  const data = await projectDetail(projectId)
  detail.value = data
  nodes.value = data.nodes || []
  edges.value = data.edges || []
}

async function loadComments() { comments.value = await listComments(projectId) }
async function loadLogs() { logs.value = await projectLogs(projectId) }

// ---- 客户评价 + 反思 ----
const evaluation = ref(null)
const reflectionDraft = ref('')
const savingReflection = ref(false)

const evalLowScore = computed(() => {
  const e = evaluation.value
  if (!e) return false
  return [e.designScore, e.serviceScore, e.productScore].some((s) => s <= 2)
})

async function loadEvaluation() {
  const data = await getEvaluation(projectId)
  evaluation.value = data
  reflectionDraft.value = data?.reflection || ''
}

async function onSaveReflection() {
  if (!reflectionDraft.value.trim()) {
    ElMessage.warning('反思内容不能为空')
    return
  }
  savingReflection.value = true
  try {
    await saveReflection({ projectId, reflection: reflectionDraft.value.trim() })
    ElMessage.success('反思已保存')
    await loadEvaluation()
  } finally {
    savingReflection.value = false
  }
}

// ---- 节点选中：加载表单与附件 ----
const formFields = ref([])
const attachments = ref([])

// 未保存修改拦截：表单脏时弹确认框。
// confirm(保存) → 落库后放行；cancel(放弃修改) → 直接放行；X/ESC 关闭 → 中止当前操作。
// 返回 true=可继续，false=用户中止。confirmText 用于定制确认按钮文案。
async function guardUnsaved(message, confirmText = '保存') {
  if (!dynamicFormRef.value?.isDirty) return true
  try {
    await ElMessageBox.confirm(message, '未保存的修改', {
      confirmButtonText: confirmText,
      cancelButtonText: '放弃修改',
      type: 'warning',
      showCancelButton: true,
      distinguishCancelAndClose: true,
      closeOnClickModal: false,
      closeOnPressEscape: false
    })
    await saveSelectedNode()
    return true
  } catch (action) {
    if (action === 'cancel') return true // 用户选择放弃修改，继续操作
    return false // X / ESC 关闭弹窗，中止操作
  }
}

async function onNodeClick(nodeId) {
  if (nodeId === selectedNodeId.value) return
  const ok = await guardUnsaved(
    '当前节点表单有未保存的修改，切换节点将丢失。是否先保存？',
    '保存并切换'
  )
  if (!ok) return
  selectedNodeId.value = nodeId
  nodeTab.value = 'form'
  const n = nodes.value.find((x) => x.id === nodeId)
  const [form, attach] = await Promise.all([getNodeForm(nodeId), listAttachments(nodeId)])
  formFields.value = form.fields || []
  attachments.value = attach || []
  // 更新节点徽章：表单已填/附件计数
  n.formFilled = (form.fields || []).some((f) => f.fieldValue)
  n.attachmentCount = (attach || []).length
}

// 取消选中（点击画布空白 / 面板关闭按钮）：同样需拦截未保存修改
async function onDeselect() {
  const ok = await guardUnsaved(
    '当前节点表单有未保存的修改，关闭将丢失。是否先保存？',
    '保存'
  )
  if (!ok) return
  selectedNodeId.value = null
}

// ---- 节点操作 ----
const savingAll = ref(false)
const dynamicFormRef = ref(null)
const nodeTemplates = ref([])  // 节点库（管理员预设，后端加载）

function viewportCenter() {
  const rect = canvasRef.value?.$el?.getBoundingClientRect?.() || { left: 0, top: 0, width: 800, height: 600 }
  return canvasRef.value?.screenToFlowCoordinate
    ? canvasRef.value.screenToFlowCoordinate({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
    : { x: 300, y: 300 }
}

// 从节点库点选（只能使用管理员预设的节点类型）
async function onAddPreset(preset) {
  const ok = await guardUnsaved(
    '当前节点表单有未保存的修改，新增节点将切换并丢失。是否先保存？',
    '保存并新增'
  )
  if (!ok) return
  const center = viewportCenter()
  const maxSort = Math.max(0, ...nodes.value.map((n) => n.sort || 0))
  const data = await addNode({
    projectId,
    nodeTemplateId: preset.id,
    sort: maxSort + 1,
    posX: Math.round(center.x),
    posY: Math.round(center.y)
  })
  await loadDetail()
  selectedNodeId.value = data.id
  nodeTab.value = 'form'
  // 新增节点后面板保持新节点：加载其空表单与空附件，避免残留上一节点的表单字段
  const [form, attach] = await Promise.all([getNodeForm(data.id), listAttachments(data.id)])
  formFields.value = form.fields || []
  attachments.value = attach || []
  messageStore.fetchUnread()
}

// 连线拖拽松开选节点：在松开位置创建节点并自动连一条线到原节点（V1.4）
async function onAddConnected({ sourceNodeId, preset, posX, posY }) {
  const ok = await guardUnsaved(
    '当前节点表单有未保存的修改，新增节点将切换并丢失。是否先保存？',
    '保存并新增'
  )
  if (!ok) return
  const maxSort = Math.max(0, ...nodes.value.map((n) => n.sort || 0))
  const data = await addNode({
    projectId,
    nodeTemplateId: preset.id,
    sort: maxSort + 1,
    posX,
    posY
  })
  await addEdge({ projectId, sourceNodeId, targetNodeId: data.id, label: '' })
  await loadDetail()
  selectedNodeId.value = data.id
  nodeTab.value = 'form'
  // 与 onAddPreset 同理：加载新节点的空表单与附件
  const [form, attach] = await Promise.all([getNodeForm(data.id), listAttachments(data.id)])
  formFields.value = form.fields || []
  attachments.value = attach || []
  messageStore.fetchUnread()
}

// 顶部栏「保存」：保存当前选中节点的表单填写值（节点标题/说明来自节点模板，不可改）
async function saveSelectedNode() {
  if (!selectedNodeId.value || isArchived.value) return
  if (formFields.value.length === 0) return
  savingAll.value = true
  try {
    const formValueList = dynamicFormRef.value?.collect()
    if (formValueList && formValueList.length) {
      await saveFormValue({ projectNodeId: selectedNodeId.value, formValueList })
      if (selectedNode.value) {
        selectedNode.value.formFilled = formValueList.some((v) => v.fieldValue)
      }
    }
    dynamicFormRef.value?.markClean()
    ElMessage.success('已保存')
    messageStore.fetchUnread()
  } finally {
    savingAll.value = false
  }
}

async function onDeleteNode(nodeId) {
  const n = nodes.value.find((x) => x.id === nodeId)
  await ElMessageBox.confirm(`确定删除节点「${n?.nodeTitle}」吗？其连线与表单数据将一并删除，不可恢复！`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteNode({ nodeId })
  if (selectedNodeId.value === nodeId) selectedNodeId.value = null
  ElMessage.success('节点已删除')
  loadDetail()
  messageStore.fetchUnread()
}

// 键盘 Delete/Backspace 删除节点：批量持久化（V1.4 修复键盘删除不同步后端）
async function onDeleteNodes(nodeIds) {
  if (!nodeIds || nodeIds.length === 0) return
  const titles = nodeIds.map((id) => nodes.value.find((n) => n.id === id)?.nodeTitle || id).join('、')
  await ElMessageBox.confirm(`确定删除节点「${titles}」吗？其连线与表单数据将一并删除，不可恢复！`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  for (const id of nodeIds) {
    await deleteNode({ nodeId: id })
  }
  if (nodeIds.includes(selectedNodeId.value)) selectedNodeId.value = null
  ElMessage.success('节点已删除')
  loadDetail()
  messageStore.fetchUnread()
}

// ---- 坐标批量更新（拖拽防抖提交） ----
let posTimer = null
function onPositionsChange(positions) {
  clearTimeout(posTimer)
  posTimer = setTimeout(async () => {
    await batchUpdatePositions({ projectId, positions })
  }, 500)
}

// ---- 连线 ----
async function onConnect({ sourceNodeId, targetNodeId }) {
  if (sourceNodeId === targetNodeId) {
    ElMessage.warning('不能连接到节点自身')
    return
  }
  await addEdge({ projectId, sourceNodeId, targetNodeId, label: '' })
  loadDetail()
}

async function onEdgeRemove(edgeIds) {
  await ElMessageBox.confirm('确定删除该连线吗？删除后流程将断开。', '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  for (const id of edgeIds) {
    await deleteEdge({ id })
  }
  loadDetail()
}

// ---- 表单保存 ----
const savingForm = ref(false)

async function onSaveForm(formValueList) {
  savingForm.value = true
  try {
    await saveFormValue({ projectNodeId: selectedNodeId.value, formValueList })
    ElMessage.success('表单已保存')
    if (selectedNode.value) {
      selectedNode.value.formFilled = formValueList.some((v) => v.fieldValue)
    }
    dynamicFormRef.value?.markClean()
    messageStore.fetchUnread()
  } finally {
    savingForm.value = false
  }
}

// ---- 附件 ----
const uploading = ref(false)

async function onUpload({ file }) {
  uploading.value = true
  try {
    await uploadAttachment(file, projectId, selectedNodeId.value)
    ElMessage.success('上传成功')
    attachments.value = await listAttachments(selectedNodeId.value)
    if (selectedNode.value) selectedNode.value.attachmentCount = attachments.value.length
  } finally {
    uploading.value = false
  }
}

function onDownload(a) {
  window.open(downloadUrl(a.id), '_blank')
}

async function onDeleteAttachment(a) {
  await ElMessageBox.confirm(`确定删除附件「${a.fileName}」吗？删除后不可恢复！`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteAttachment({ attachmentId: a.id })
  attachments.value = await listAttachments(selectedNodeId.value)
  if (selectedNode.value) selectedNode.value.attachmentCount = attachments.value.length
  ElMessage.success('已删除')
}

// ---- 评论 ----
const comments = ref([])
const newComment = ref('')
const commenting = ref(false)

async function onAddComment() {
  commenting.value = true
  try {
    await addComment({ projectId, content: newComment.value.trim() })
    newComment.value = ''
    loadComments()
    messageStore.fetchUnread()
  } finally {
    commenting.value = false
  }
}

async function onDeleteComment(c) {
  await ElMessageBox.confirm('确定删除该评论吗？删除后不可恢复。', '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteComment({ commentId: c.id })
  loadComments()
}

// ---- 日志 ----
const logs = ref([])

// ---- 项目级操作 ----
const editBaseVisible = ref(false)
const savingBase = ref(false)
const categoryOptions = ref([])
const customerOptions = ref([])
const designerOptions = ref([])
const baseForm = reactive({
  id: projectId, projectName: '', categoryId: null, contactCustomerIds: [], projectDesc: '',
  expectTime: null, designerRelUserIdList: []
})

// 某客户单位下的对接人选项（V1.4.7）
function contactsOf(categoryId) {
  if (!categoryId) return []
  return customerOptions.value.filter((c) => c.categoryId === categoryId)
}

function onBaseCategoryChange() {
  baseForm.contactCustomerIds = []
}

function openEditBase() {
  Object.assign(baseForm, {
    projectName: detail.value.projectName,
    categoryId: detail.value.categoryId,
    contactCustomerIds: (detail.value.contactList || []).map((c) => c.customerId),
    projectDesc: detail.value.projectDesc,
    expectTime: detail.value.expectTime,
    designerRelUserIdList: (detail.value.designerList || []).map((d) => d.userId)
  })
  editBaseVisible.value = true
}

async function submitBase() {
  if (!baseForm.categoryId) {
    ElMessage.warning('请选择客户单位')
    return
  }
  if (!baseForm.contactCustomerIds.length) {
    ElMessage.warning('请至少选择一位客户对接人')
    return
  }
  savingBase.value = true
  try {
    await updateProjectBase({ ...baseForm })
    ElMessage.success('已保存')
    editBaseVisible.value = false
    loadDetail()
  } finally {
    savingBase.value = false
  }
}

async function onArchive() {
  const ok = await guardUnsaved(
    '当前节点表单有未保存的修改，归档后内容将只读。是否先保存？',
    '保存并归档'
  )
  if (!ok) return
  await ElMessageBox.confirm('确定归档该项目吗？归档后全部内容只读。', '归档确认', { type: 'warning' })
  await archiveProject({ projectId })
  ElMessage.success('已归档')
  loadDetail()
}

async function onUnArchive() {
  await unArchiveProject({ projectId })
  ElMessage.success('已取消归档')
  loadDetail()
}

async function onDeleteProject() {
  await ElMessageBox.confirm(
    '确定删除该项目吗？全部业务数据与附件文件将物理销毁，不可恢复！',
    '删除确认',
    { type: 'error', confirmButtonText: '确认删除' }
  )
  await deleteProject({ projectId })
  ElMessage.success('项目已删除')
  router.push('/projects')
}

onMounted(async () => {
  await Promise.all([loadDetail(), loadComments(), loadLogs(), loadEvaluation()])
  // 节点库（全角色可读，画布只能选择预设节点类型）
  const tpls = await listNodeTemplates().catch(() => [])
  nodeTemplates.value = (tpls || []).map((t) => ({
    id: t.id, title: t.nodeTitle, remark: t.nodeRemark, icon: t.icon, formFields: t.formFields || []
  }))
  if (canWrite.value) {
    const [cats, custs] = await Promise.all([
      listCategories().catch(() => []),
      listCustomers({ pageNum: 1, pageSize: 200 }).catch(() => ({ items: [] }))
    ])
    categoryOptions.value = cats || []
    customerOptions.value = custs.items || []
    if (userStore.role === '管理员') {
      const users = await listUsers().catch(() => [])
      designerOptions.value = (users || []).filter((u) => u.isEnable === 1 && u.role !== '客户')
    }
  }
})

// 路由离开守卫：离开项目详情页前，若有未保存的表单修改需拦截
onBeforeRouteLeave(async (to, from, next) => {
  if (dynamicFormRef.value?.isDirty) {
    try {
      await ElMessageBox.confirm(
        '当前节点表单有未保存的修改，离开页面将丢失。是否先保存？',
        '未保存的修改',
        {
          confirmButtonText: '保存并离开',
          cancelButtonText: '放弃修改',
          type: 'warning',
          showCancelButton: true,
          distinguishCancelAndClose: true,
          closeOnClickModal: false,
          closeOnPressEscape: false
        }
      )
      await saveSelectedNode()
      next()
    } catch (action) {
      if (action === 'cancel') next() // 放弃修改，离开
      else next(false) // X / ESC 关闭弹窗，中止离开
    }
  } else {
    next()
  }
})
</script>

<style scoped>
.detail-page { height: calc(100vh - 92px); display: flex; flex-direction: column; }
.top-bar { margin-bottom: 8px; }
.top-bar :deep(.el-card__body) { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.top-left { display: flex; align-items: center; gap: 12px; }
.project-name { font-size: 17px; font-weight: bold; }
.expect-time { color: var(--lk-text-3); font-size: 13px; }
.archive-banner { margin-bottom: 8px; }
.content-area { flex: 1; display: flex; gap: 8px; min-height: 0; }
.canvas-area { flex: 7; border-radius: 8px; overflow: hidden; }
.panel-area { flex: 3; min-width: 300px; }
.panel-card { height: 100%; overflow-y: auto; }
.panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.panel-title { font-size: 15px; font-weight: bold; }
.empty-text { color: var(--lk-text-3); font-size: 13px; padding: 8px 0; }
.designer-list { display: flex; flex-wrap: wrap; gap: 6px; }
.designer-tag { margin-right: 4px; }
.comment-input { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.comment-input .el-button { align-self: flex-end; }
.comment-item { border-bottom: 1px solid #ebeef5; padding: 8px 0; }
.comment-head { display: flex; align-items: center; gap: 8px; }
.comment-user { font-weight: bold; font-size: 13px; }
.comment-time { color: var(--lk-text-3); font-size: 12px; flex: 1; }
.comment-content { margin-top: 4px; font-size: 13px; color: #606266; white-space: pre-wrap; }
.log-user { font-weight: bold; }
/* 客户评价 + 反思 */
.eval-block { margin-bottom: 8px; }
.eval-low-alert { margin-bottom: 8px; }
.reflection-box { display: flex; flex-direction: column; gap: 8px; }
.reflection-box .el-button { align-self: flex-end; }
.reflection-meta { font-size: 12px; color: var(--lk-text-3); }
.attach-header { margin-bottom: 8px; }
.attach-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #ebeef5; }
.attach-thumb { width: 48px; height: 48px; border-radius: 6px; flex-shrink: 0; }
.file-icon { font-size: 28px; flex-shrink: 0; }
.attach-info { flex: 1; min-width: 0; }
.attach-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.attach-meta { font-size: 12px; color: var(--lk-text-3); }
.attach-actions { flex-shrink: 0; }

/* ---- 移动端：画布在上（vh 自适应），面板在下堆叠 ---- */
@media (max-width: 767px) {
  .detail-page { height: auto; }
  .top-bar :deep(.el-card__body) { flex-wrap: wrap; gap: 8px; }
  .top-actions { flex-wrap: wrap; }
  .content-area { flex-direction: column; }
  .canvas-area { flex: none; height: 48vh; min-height: 300px; }
  .panel-area { flex: none; width: 100%; min-width: 0; max-height: 60vh; }
}
</style>
