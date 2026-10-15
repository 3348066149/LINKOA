<template>
  <!-- 文创卡片节点：序号圆标 + 标题 + 徽章 + 备注摘要（PRD 9.6） -->
  <div class="flow-node" :class="{ selected, 'review-pending': data.isReview && !data.reviewResult, 'review-done': data.reviewResult }">
    <!-- 连线锚点：悬浮淡入 -->
    <Handle type="target" :position="Position.Left" class="node-handle" />
    <Handle type="source" :position="Position.Right" class="node-handle" />

    <!-- 节点头部（V1.3：去掉序号圆标，加节点类型图标） -->
    <div class="node-header">
      <span class="node-icon">
        <el-image v-if="isImageIcon(data.icon)" :src="iconUrl(data.icon)" fit="cover" class="node-icon-img" />
        <el-icon v-else :size="15"><component :is="ICON_MAP[data.icon] || MessageBox" /></el-icon>
      </span>
      <span class="node-title" :title="data.nodeTitle">{{ data.nodeTitle }}</span>
      <el-icon
        v-if="data.showDelete"
        class="delete-icon"
        title="删除节点"
        @click.stop="emit('delete', id)"
      >
        <Close />
      </el-icon>
    </div>

    <!-- 节点体：创建/更新时间 + 信息徽章（说明不再展示，仅在节点库悬停时提示） -->
    <div v-if="data.createTime || data.hasForm || data.attachmentCount > 0 || data.isReview" class="node-body">
      <div v-if="data.createTime" class="node-created">🕐 创建：{{ formatNodeTime(data.createTime) }}</div>
      <div v-if="data.isReview" class="review-badge" :class="data.reviewResult ? 'done' : 'pending'">
        {{ data.reviewResult ? `✓ 已审：${data.reviewResult.option || ''}` : '⏳ 待客户审核' }}
      </div>
      <div v-if="data.hasForm || data.attachmentCount > 0" class="badges">
        <span v-if="data.hasForm" class="badge form-badge" :class="{ filled: data.formFilled }">
          🏷️ 表单({{ data.formFilled ? '已填' : '未填' }})
        </span>
        <el-tooltip v-if="data.attachmentCount > 0" content="含附件" placement="top">
          <span class="badge attach-badge">📎 {{ data.attachmentCount }}个附件</span>
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Close, MessageBox } from '@element-plus/icons-vue'
import { Handle, Position } from '@vue-flow/core'
import { ICON_MAP, iconUrl, isImageIcon } from '@/utils/nodeIcon'

defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['delete'])

// 2026-10-13T07:49:00 / 2026-10-13 07:49:00 → 2026-10-13 07:49
function formatNodeTime(t) {
  if (!t) return ''
  return String(t).replace('T', ' ').slice(0, 16)
}

</script>

<style scoped>
.flow-node {
  width: 200px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
  overflow: visible;
}
/* 选中节点：品牌色柔和发光投影 */
.flow-node.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.25), 0 4px 16px rgba(64, 158, 255, 0.35);
}
.node-handle {
  /* 锚点常显（不依赖悬浮），拖拽连线入口清晰可见 */
  opacity: 0.85;
  transition: opacity 0.2s, transform 0.2s;
  width: 12px;
  height: 12px;
  background: #409eff;
  border: 2px solid #fff;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.6);
}
.flow-node:hover .node-handle { opacity: 1; transform: scale(1.25); }

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 6px;
}
.node-icon-img { width: 100%; height: 100%; border-radius: 6px; }
.node-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  background: #f0f2f5;
  border-radius: 6px;
}
.node-title {
  flex: 1;
  font-weight: bold;
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.delete-icon {
  flex-shrink: 0;
  color: #f56c6c;
  cursor: pointer;
  font-size: 14px;
}
.delete-icon:hover { transform: scale(1.2); }

.node-body { padding: 0 12px 10px; }
.node-created { font-size: 11px; color: #a0a6b0; margin-bottom: 4px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; }
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}
.form-badge { background: #fdf6ec; color: #e6a23c; }
.form-badge.filled { background: #f0f9eb; color: #67c23a; }
.attach-badge { background: #ecf5ff; color: #409eff; }

/* 审核节点状态（V1.4.19） */
.flow-node.review-pending {
  border-color: #f56c6c;
  box-shadow: 0 0 0 3px rgba(245, 108, 108, 0.25), 0 0 12px rgba(245, 108, 108, 0.4);
  animation: review-pulse 1.6s ease-in-out infinite;
}
.flow-node.review-done { border-color: #67c23a; }
@keyframes review-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(245, 108, 108, 0.25), 0 0 8px rgba(245, 108, 108, 0.3); }
  50% { box-shadow: 0 0 0 5px rgba(245, 108, 108, 0.35), 0 0 16px rgba(245, 108, 108, 0.55); }
}
.review-badge {
  font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-bottom: 4px;
  display: inline-block; white-space: nowrap;
}
.review-badge.pending { background: #fef0f0; color: #f56c6c; }
.review-badge.done { background: #f0f9eb; color: #67c23a; }
</style>
