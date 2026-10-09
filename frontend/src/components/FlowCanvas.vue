<template>
  <!-- @vue-flow 画布封装：项目详情页与模板编辑页复用（PRD 9.5/9.7） -->
  <div ref="wrapperRef" class="flow-canvas-wrapper">
    <VueFlow
      v-model:nodes="vfNodes"
      v-model:edges="vfEdges"
      :nodes-draggable="!readonly"
      :nodes-connectable="!readonly"
      :nodes-focusable="!readonly"
      :edges-focusable="!readonly"
      :delete-key-code="readonly ? null : ['Backspace', 'Delete']"
      fit-view-on-init
      class="flow-canvas"
      @node-click="onNodeClick"
      @pane-click="onPaneClick"
      @node-drag-stop="onNodeDragStop"
      @nodes-delete="onNodesDelete"
      @connect="onConnect"
      @connect-start="onConnectStart"
      @connect-end="onConnectEnd"
      @edge-click="onEdgeClick"
      @edges-remove="onEdgesRemove"
    >
      <Background pattern-color="#d0d7e2" :gap="20" />

      <!-- 自定义节点 -->
      <template #node-custom="nodeProps">
        <CustomFlowNode v-bind="nodeProps" @delete="(id) => emit('node-delete', Number(id))" />
      </template>

      <!-- 悬浮工具条：左上角（RAGFlow 式：节点库 / 自适应 / 全屏） -->
      <Panel position="top-left" class="toolbar">
        <el-tooltip v-if="!readonly" content="节点库（点击加入画布）" placement="right">
          <el-button
            size="small"
            :type="paletteVisible ? 'primary' : 'default'"
            :icon="Grid"
            circle
            aria-label="节点库"
            @click="paletteVisible = !paletteVisible"
          />
        </el-tooltip>
        <el-tooltip content="自适应居中" placement="right">
          <el-button size="small" :icon="Aim" circle aria-label="自适应居中" @click="fitView()" />
        </el-tooltip>
        <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏模式'" placement="right">
          <el-button size="small" :icon="FullScreen" circle aria-label="全屏模式" @click="toggleFullscreen" />
        </el-tooltip>
      </Panel>

      <!-- 移动端操作提示 -->
      <div v-if="isMobile" class="touch-hint">双指缩放 · 单指平移</div>

      <!-- 节点库面板（仅管理员预设的节点类型，不支持自由创建） -->
      <Panel v-if="!readonly && paletteVisible" position="top-left" class="palette-panel">
        <div class="palette-title">节点库</div>
        <el-input
          v-model="paletteKeyword"
          size="small"
          placeholder="搜索节点类型"
          clearable
          :prefix-icon="Search"
          class="palette-search"
        />
        <el-empty v-if="filteredPresets.length === 0" description="暂无匹配节点，请联系管理员预设" :image-size="50" />
        <el-tooltip
          v-for="(p, idx) in filteredPresets"
          :key="idx"
          :content="p.remark"
          placement="right"
          :disabled="!p.remark"
          :show-after="400"
        >
          <div class="palette-item" @click="onPickPreset(p)">
            <span class="palette-item-icon">
              <el-image v-if="isImageIcon(p.icon)" :src="iconUrl(p.icon)" fit="cover" class="palette-icon-img" />
              <el-icon v-else :size="16"><component :is="ICON_MAP[p.icon] || MessageBox" /></el-icon>
            </span>
            <div class="palette-item-body">
              <div class="palette-item-title">{{ p.title }}</div>
            </div>
          </div>
        </el-tooltip>
      </Panel>

      <!-- 右下角：可折叠小地图 + 缩放比例 -->
      <Panel position="bottom-right" class="minimap-panel">
        <div class="zoom-display">{{ Math.round(viewport.zoom * 100) }}%</div>
        <el-icon class="minimap-toggle" @click="minimapVisible = !minimapVisible">
          <ArrowDown v-if="minimapVisible" />
          <ArrowUp v-else />
        </el-icon>
        <MiniMap v-show="minimapVisible" :width="160" :height="110" />
      </Panel>
    </VueFlow>

    <!-- 连线拖拽松开后弹出的快速节点库（V1.4：拖出 handle 松开空白处时显示） -->
    <div
      v-if="quickPalette.visible"
      class="quick-palette"
      :style="{ left: quickPalette.x + 'px', top: quickPalette.y + 'px' }"
      @click.stop
    >
      <div class="qp-head">
        <span>选择要连接的节点</span>
        <el-icon class="qp-close" @click="quickPalette.visible = false"><Close /></el-icon>
      </div>
      <el-input v-model="quickKeyword" size="small" placeholder="搜索节点" clearable :prefix-icon="Search" class="qp-search" />
      <div class="qp-list">
        <div
          v-for="(p, idx) in filteredQuickPresets"
          :key="idx"
          class="qp-item"
          @click="onQuickPick(p)"
        >
          <span class="qp-icon">
            <el-image v-if="isImageIcon(p.icon)" :src="iconUrl(p.icon)" fit="cover" class="palette-icon-img" />
            <el-icon v-else :size="14"><component :is="ICON_MAP[p.icon] || MessageBox" /></el-icon>
          </span>
          <span class="qp-title">{{ p.title }}</span>
        </div>
        <el-empty v-if="filteredQuickPresets.length === 0" description="暂无节点" :image-size="40" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ArrowDown, ArrowUp, Aim, Close, FullScreen, Grid, MessageBox, Search } from '@element-plus/icons-vue'
import { Panel, VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import CustomFlowNode from './CustomFlowNode.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { ICON_MAP, iconUrl, isImageIcon } from '@/utils/nodeIcon'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'

const props = defineProps({
  // 业务节点数组：[{id, nodeTitle, nodeRemark, sort, posX, posY, createTime, updateTime, hasForm, formFilled, attachmentCount}]
  nodes: { type: Array, default: () => [] },
  // 业务连线数组：[{id, sourceNodeId, targetNodeId, label}]
  edges: { type: Array, default: () => [] },
  // 只读（已归档）：禁用拖拽/连线/聚焦
  readonly: { type: Boolean, default: false },
  // 节点是否显示快速删除图标
  deletable: { type: Boolean, default: true },
  // 当前选中节点ID（外部控制高亮）
  selectedNodeId: { type: [Number, String], default: null },
  // 预设节点库：[{title, remark, formFields?}]
  presets: { type: Array, default: () => [] }
})

// 移动端：显示触摸操作提示
const { isMobile } = useIsMobile(768)

const emit = defineEmits([
  'node-click',      // (nodeId) 选中节点
  'pane-click',      // 点击空白处（取消选中）
  'add-node',        // 工具条新增空白节点
  'add-preset',      // (preset) 从预设库点选节点
  'add-connected',   // ({sourceNodeId, preset, posX, posY}) 拖拽连线松开选节点：创建并连线
  'node-delete',     // (nodeId) 节点快速删除（✕ 图标）
  'nodes-delete',    // ([nodeId]) 键盘 Delete/Backspace 删除节点
  'positions-change',// ([{id, posX, posY}]) 拖拽结束批量坐标（父级防抖提交）
  'connect',         // ({sourceNodeId, targetNodeId}) 新建连线
  'edge-remove'      // ([edgeId]) 删除连线
])

const { fitView, viewport, screenToFlowCoordinate } = useVueFlow()

// ---- 业务数据 -> vue-flow 数据 ----
function toVfNode(n) {
  return {
    id: String(n.id),
    type: 'custom',
    position: { x: Number(n.posX), y: Number(n.posY) },
    data: {
      nodeTitle: n.nodeTitle,
      nodeRemark: n.nodeRemark,
      sort: n.sort,
      hasForm: n.hasForm,
      formFilled: n.formFilled,
      attachmentCount: n.attachmentCount ?? 0,
      createTime: n.createTime,
      updateTime: n.updateTime,
      showDelete: props.deletable && !props.readonly
    },
    selected: String(props.selectedNodeId) === String(n.id)
  }
}

function toVfEdge(e) {
  return {
    id: String(e.id),
    source: String(e.sourceNodeId),
    target: String(e.targetNodeId),
    label: e.label || '',
    type: 'smoothstep',  // RAGFlow 式直角圆滑连线
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 1.5 }
  }
}

const vfNodes = ref(props.nodes.map(toVfNode))
const vfEdges = ref(props.edges.map(toVfEdge))

// 外部数据变化时同步（接口刷新后重绘）
watch(() => props.nodes, (val) => { vfNodes.value = val.map(toVfNode) }, { deep: true })
watch(() => props.edges, (val) => { vfEdges.value = val.map(toVfEdge) }, { deep: true })
watch(() => props.selectedNodeId, () => {
  vfNodes.value = vfNodes.value.map((n) => ({ ...n, selected: String(props.selectedNodeId) === n.id }))
})

// ---- 事件 ----
function onNodeClick({ node }) {
  emit('node-click', Number(node.id))
}

// 键盘 Delete/Backspace 删除节点：vue-flow 已移除本地视图，这里同步给父组件持久化
function onNodesDelete(nodes) {
  if (props.readonly) return
  emit('nodes-delete', (nodes || []).map((n) => Number(n.id)))
}

function onNodeDragStop() {
  // 拖拽结束收集全部节点坐标，由父级防抖批量提交
  const positions = vfNodes.value.map((n) => ({
    id: Number(n.id),
    posX: Math.round(n.position.x * 100) / 100,
    posY: Math.round(n.position.y * 100) / 100
  }))
  emit('positions-change', positions)
}

function onConnect(connection) {
  emit('connect', {
    sourceNodeId: Number(connection.source),
    targetNodeId: Number(connection.target)
  })
}

function onPaneClick() {
  quickPalette.visible = false
  emit('pane-click')
}

// ---- 连线拖拽松开弹快速节点库（V1.4） ----
const quickPalette = reactive({
  visible: false,
  x: 0,
  y: 0,
  sourceNodeId: null,
  flowX: 0,
  flowY: 0
})
const quickKeyword = ref('')

function onConnectStart() {
  // 连接开始钩子（保留事件监听）
}

function onConnectEnd(event) {
  const conn = event.connection
  // 从 handle 拖出、在空白处松开（没有 target）→ 弹快速节点库
  if (conn && conn.source && !conn.target) {
    const rect = wrapperRef.value?.getBoundingClientRect?.() || { left: 0, top: 0 }
    const relX = event.event.clientX - rect.left
    const relY = event.event.clientY - rect.top
    const flowPos = screenToFlowCoordinate({ x: event.event.clientX, y: event.event.clientY })
    quickPalette.visible = true
    quickPalette.x = relX
    quickPalette.y = relY
    quickPalette.sourceNodeId = conn.source
    quickPalette.flowX = flowPos.x
    quickPalette.flowY = flowPos.y
    quickKeyword.value = ''
  }
}

const filteredQuickPresets = computed(() => {
  const kw = quickKeyword.value.trim()
  if (!kw) return props.presets
  return props.presets.filter((p) => (p.title || '').includes(kw))
})

function onQuickPick(preset) {
  const sourceNodeId = quickPalette.sourceNodeId
  const posX = quickPalette.flowX
  const posY = quickPalette.flowY
  quickPalette.visible = false
  quickKeyword.value = ''
  emit('add-connected', {
    sourceNodeId: Number(sourceNodeId),
    preset,
    posX: Math.round(posX),
    posY: Math.round(posY)
  })
}

function onEdgeClick({ edge }) {
  if (props.readonly) return
  emit('edge-remove', [Number(edge.id)])
}

function onEdgesRemove(edges) {
  emit('edge-remove', edges.map((e) => Number(e.id)))
}

// ---- 全屏 ----
const wrapperRef = ref(null)
const isFullscreen = ref(false)

async function toggleFullscreen() {
  if (!document.fullscreenElement) {
    await wrapperRef.value?.requestFullscreen()
    isFullscreen.value = true
  } else {
    await document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 同步全屏状态（ESC 退出等场景按钮不会自动感知），保持图标与实际一致
function onFsChange() {
  isFullscreen.value = !!document.fullscreenElement
}
onMounted(() => document.addEventListener('fullscreenchange', onFsChange))
onBeforeUnmount(() => document.removeEventListener('fullscreenchange', onFsChange))

// ---- 小地图 ----
const minimapVisible = ref(true)

// ---- 预设节点库 ----
const paletteVisible = ref(false)
const paletteKeyword = ref('')
const filteredPresets = computed(() => {
  const kw = paletteKeyword.value.trim()
  if (!kw) return props.presets
  return props.presets.filter((p) => (p.title || '').includes(kw) || (p.remark || '').includes(kw))
})

function onPickPreset(preset) {
  paletteVisible.value = false
  paletteKeyword.value = ''
  emit('add-preset', preset)
}

// 暴露视口坐标换算（父级"新增节点在视口中央"用）
defineExpose({ screenToFlowCoordinate, fitView })
</script>

<style scoped>
.flow-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  background: #f7f9fc;
}
.flow-canvas { width: 100%; height: 100%; }
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.palette-panel {
  margin-left: 56px;
  width: 210px;
  max-height: 70%;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.97);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 10px;
}
.palette-title {
  font-size: 13px;
  font-weight: bold;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 8px;
}
.palette-search { margin-bottom: 8px; }
.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.palette-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
  transform: translateX(2px);
}
.palette-icon-img { width: 100%; height: 100%; border-radius: 6px; }
.palette-item-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: #f0f2f5;
  border-radius: 6px;
}
.palette-item:hover .palette-item-icon { background: #d9ecff; }
.palette-item-body { flex: 1; min-width: 0; }
.palette-item-title { font-size: 13px; font-weight: bold; color: #303133; }
.minimap-panel {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.zoom-display {
  font-size: 12px;
  color: #606266;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 8px;
  border-radius: 4px;
}
.minimap-toggle {
  cursor: pointer;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px;
  border-radius: 4px;
}
.quick-palette {
  position: absolute;
  width: 220px;
  max-height: 300px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  padding: 10px;
  z-index: 200;
}
.qp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}
.qp-close { cursor: pointer; color: var(--lk-text-3); }
.qp-close:hover { color: #303133; }
.qp-search { margin-bottom: 8px; }
.qp-list { overflow-y: auto; max-height: 220px; }
.qp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
}
.qp-item:hover { background: #ecf5ff; }
.qp-icon { font-size: 16px; }
.qp-title { font-size: 13px; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ---- 移动端适配 ---- */
.touch-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(30, 41, 59, 0.72);
  color: #fff;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  pointer-events: none;
  z-index: 50;
  white-space: nowrap;
  animation: touch-hint-fade 4s ease forwards;
}
@keyframes touch-hint-fade {
  0% { opacity: 0; }
  15% { opacity: 1; }
  75% { opacity: 1; }
  100% { opacity: 0; }
}
@media (max-width: 767px) {
  .palette-panel { width: 180px; margin-left: 48px; }
  .quick-palette { max-width: calc(100vw - 24px); }
  .minimap-panel { display: none; }
}
</style>
