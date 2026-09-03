<template>
  <div class="edit-page">
    <!-- 顶部栏：模板名称 + 保存模板（整图提交） -->
    <el-card class="top-bar" shadow="never">
      <div class="top-left">
        <el-button link :icon="Back" @click="$router.push('/templates')">返回</el-button>
        <el-input v-model="templateName" class="name-input" maxlength="128" />
      </div>
      <el-button type="primary" :icon="Select" :loading="saving" @click="saveGraph">保存模板</el-button>
    </el-card>

    <div class="content-area">
      <!-- 左侧画布（本地编辑，保存时整图提交） -->
      <div class="canvas-area">
        <FlowCanvas
          ref="canvasRef"
          :nodes="nodes"
          :edges="edges"
          :selected-node-id="selectedNodeId"
          :presets="nodeTemplates"
          @node-click="onNodeClick"
          @pane-click="selectedNodeId = null"
          @add-preset="onAddPreset"
          @add-connected="onAddConnected"
          @node-delete="onDeleteNode"
          @nodes-delete="onDeleteNodes"
          @positions-change="onPositionsChange"
          @connect="onConnect"
          @edge-remove="onEdgeRemove"
        />
      </div>

      <!-- 右侧面板 -->
      <div class="panel-area">
        <el-card v-if="selectedNode" shadow="never" class="panel-card">
          <div class="panel-header">
            <span class="panel-title">{{ selectedNode.nodeTitle }}</span>
            <el-button link :icon="Close" @click="selectedNodeId = null" />
          </div>

          <el-form label-position="top">
            <el-form-item label="节点标题">
              <el-input v-model="selectedNode.nodeTitle" maxlength="128" />
            </el-form-item>
            <el-form-item label="节点备注">
              <el-input v-model="selectedNode.nodeRemark" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="排序序号">
              <el-input-number v-model="selectedNode.sort" :min="0" />
            </el-form-item>
          </el-form>

          <el-alert
            title="表单字段在「节点模板」中维护"
            description="该节点的表单字段来自节点模板库，如需调整请到 系统管理 → 节点模板 中修改。"
            type="info"
            :closable="false"
            show-icon
          />
        </el-card>

        <el-card v-else shadow="never" class="panel-card">
          <el-empty description="点击画布节点进行配置；左上角 + 新增节点；拖动节点边缘圆点连线" />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Close, Select } from '@element-plus/icons-vue'
import FlowCanvas from '@/components/FlowCanvas.vue'
import { listNodeTemplates } from '@/api/nodeTemplate'
import { templateDetail, updateTemplate } from '@/api/template'

const route = useRoute()
const templateId = Number(route.params.id)

const templateName = ref('')
const nodes = ref([])
const edges = ref([])
const nodeTemplates = ref([])  // 节点库（管理员预设，后端加载）
const selectedNodeId = ref(null)
const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) || null)
const saving = ref(false)
const canvasRef = ref(null)

let tempSeq = -1 // 新节点临时 id（负数，避免与数据库 id 冲突）

// ---- 加载 ----
async function loadDetail() {
  const data = await templateDetail(templateId)
  templateName.value = data.templateName
  nodes.value = (data.nodes || []).map((n) => ({
    id: n.id,
    nodeTemplateId: n.nodeTemplateId,
    nodeTitle: n.nodeTitle,
    nodeRemark: n.nodeRemark,
    sort: n.sort,
    posX: n.posX,
    posY: n.posY
  }))
  edges.value = (data.edges || []).map((e) => ({
    id: e.id,
    sourceNodeId: e.sourceNodeId,
    targetNodeId: e.targetNodeId,
    label: e.label
  }))
}

// ---- 本地编辑 ----
function onNodeClick(nodeId) {
  selectedNodeId.value = nodeId
}

// 从节点库点选：附带节点模板预设的建议表单字段（管理员可再编辑）
function onAddPreset(preset) {
  addNodeLocal(preset)
}

function addNodeLocal(preset) {
  const rect = canvasRef.value?.$el?.getBoundingClientRect?.() || { left: 0, top: 0, width: 800, height: 600 }
  const center = canvasRef.value?.screenToFlowCoordinate
    ? canvasRef.value.screenToFlowCoordinate({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
    : { x: 300, y: 300 }
  const maxSort = Math.max(0, ...nodes.value.map((n) => n.sort || 0))
  const newNode = {
    id: tempSeq--,
    nodeTemplateId: preset.id,
    nodeTitle: preset.title,
    nodeRemark: preset.remark || '',
    sort: maxSort + 1,
    posX: Math.round(center.x),
    posY: Math.round(center.y)
  }
  nodes.value = [...nodes.value, newNode]
  selectedNodeId.value = newNode.id
}

function onDeleteNode(nodeId) {
  nodes.value = nodes.value.filter((n) => n.id !== nodeId)
  edges.value = edges.value.filter((e) => e.sourceNodeId !== nodeId && e.targetNodeId !== nodeId)
  if (selectedNodeId.value === nodeId) selectedNodeId.value = null
}

// 键盘 Delete/Backspace 删除节点：本地批量删除（保存时整图提交生效）
function onDeleteNodes(nodeIds) {
  const ids = new Set(nodeIds)
  nodes.value = nodes.value.filter((n) => !ids.has(n.id))
  edges.value = edges.value.filter((e) => !ids.has(e.sourceNodeId) && !ids.has(e.targetNodeId))
  if (ids.has(selectedNodeId.value)) selectedNodeId.value = null
}

function onPositionsChange(positions) {
  // 本地同步坐标，保存时一并提交
  positions.forEach((p) => {
    const n = nodes.value.find((x) => x.id === p.id)
    if (n) { n.posX = p.posX; n.posY = p.posY }
  })
}

function onConnect({ sourceNodeId, targetNodeId }) {
  if (sourceNodeId === targetNodeId) return
  const dup = edges.value.some((e) => e.sourceNodeId === sourceNodeId && e.targetNodeId === targetNodeId)
  if (dup) return
  edges.value = [...edges.value, { id: tempSeq--, sourceNodeId, targetNodeId, label: '' }]
}

// 连线拖拽松开选节点：本地创建节点并连一条线到原节点（V1.4）
function onAddConnected({ sourceNodeId, preset, posX, posY }) {
  const maxSort = Math.max(0, ...nodes.value.map((n) => n.sort || 0))
  const newNode = {
    id: tempSeq--,
    nodeTemplateId: preset.id,
    nodeTitle: preset.title,
    nodeRemark: preset.remark || '',
    sort: maxSort + 1,
    posX,
    posY
  }
  nodes.value = [...nodes.value, newNode]
  edges.value = [...edges.value, { id: tempSeq--, sourceNodeId, targetNodeId: newNode.id, label: '' }]
  selectedNodeId.value = newNode.id
}

function onEdgeRemove(edgeIds) {
  edges.value = edges.value.filter((e) => !edgeIds.includes(e.id))
}

// ---- 整图提交保存 ----
// 端点约定：全部使用 nodes 数组的 1 基序号（后端按序号解析），
// 避免"已有节点 id 与数组序号碰撞"的二义性；整图覆盖本就全量重建。
async function saveGraph() {
  if (!templateName.value.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }
  saving.value = true
  try {
    const idToIndex = new Map(nodes.value.map((n, i) => [n.id, i + 1]))
    const payload = {
      id: templateId,
      templateName: templateName.value.trim(),
      nodes: nodes.value.map((n) => ({
        nodeTemplateId: n.nodeTemplateId,
        nodeTitle: n.nodeTitle,
        nodeRemark: n.nodeRemark,
        sort: n.sort,
        posX: n.posX,
        posY: n.posY
      })),
      edges: edges.value.map((e) => ({
        sourceNodeId: idToIndex.get(e.sourceNodeId),
        targetNodeId: idToIndex.get(e.targetNodeId),
        label: e.label || ''
      }))
    }
    await updateTemplate(payload)
    ElMessage.success('模板已保存')
    loadDetail()
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadDetail()
  const tpls = await listNodeTemplates().catch(() => [])
  nodeTemplates.value = (tpls || []).map((t) => ({
    id: t.id, title: t.nodeTitle, remark: t.nodeRemark, formFields: t.formFields || []
  }))
})
</script>

<style scoped>
.edit-page { height: calc(100vh - 92px); display: flex; flex-direction: column; }
.top-bar { margin-bottom: 8px; }
.top-bar :deep(.el-card__body) { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.top-left { display: flex; align-items: center; gap: 8px; flex: 1; }
.name-input { max-width: 320px; font-weight: bold; }
.content-area { flex: 1; display: flex; gap: 8px; min-height: 0; }
.canvas-area { flex: 7; border-radius: 8px; overflow: hidden; }
.panel-area { flex: 3; min-width: 300px; }
.panel-card { height: 100%; overflow-y: auto; }
.panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.panel-title { font-size: 15px; font-weight: bold; }
.field-item { border: 1px solid #ebeef5; border-radius: 6px; padding: 8px; margin-bottom: 8px; }
.field-head { display: flex; gap: 6px; align-items: center; }
.field-label-input { flex: 1; }
.options-editor { width: 100%; margin-top: 6px; }
.field-sort { margin-top: 6px; width: 100%; }
</style>
