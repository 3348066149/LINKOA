<template>
  <aside class="conv-list">
    <div class="conv-head">
      <span class="conv-title">对话</span>
      <el-button size="small" type="primary" plain @click="$emit('new')">
        <el-icon><Plus /></el-icon><span>新对话</span>
      </el-button>
    </div>
    <div class="conv-body">
      <div v-if="conversations.length === 0" class="conv-empty">暂无历史对话</div>
      <div
        v-for="c in conversations"
        :key="c.id"
        class="conv-item"
        :class="{ active: c.id === currentId }"
        @click="$emit('select', c.id)"
      >
        <el-icon v-if="c.pinned" class="conv-pin" :size="13"><Top /></el-icon>
        <span class="conv-name" :title="c.title">{{ c.title }}</span>
        <el-dropdown
          trigger="click"
          placement="bottom-end"
          @command="(cmd) => onCommand(c, cmd)"
          @click.stop
        >
          <button class="conv-more" type="button" title="更多操作" @click.stop>
            <el-icon><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item :command="'pin'">
                <el-icon><Top /></el-icon>{{ c.pinned ? '取消置顶' : '置顶' }}
              </el-dropdown-item>
              <el-dropdown-item :command="'rename'">
                <el-icon><EditPen /></el-icon>重命名
              </el-dropdown-item>
              <el-dropdown-item :command="'delete'" divided class="conv-danger-item">
                <el-icon><Delete /></el-icon>删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { Plus, Delete, Top, MoreFilled, EditPen } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

defineProps({
  conversations: { type: Array, default: () => [] },
  currentId: { type: Number, default: null },
})

const emit = defineEmits(['new', 'select', 'remove', 'rename', 'pin'])

async function onCommand(c, cmd) {
  if (cmd === 'pin') {
    emit('pin', c.id, !c.pinned)
  } else if (cmd === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('请输入新的会话标题', '重命名', {
        inputValue: c.title,
        inputPattern: /\S+/,
        inputErrorMessage: '标题不能为空',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
      })
      if (value) emit('rename', c.id, value.trim())
    } catch (e) {
      /* 用户取消 */
    }
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('删除后该会话的所有消息将一并删除，且无法恢复。确定删除吗？', '删除对话', {
        type: 'warning',
        confirmButtonText: '删除',
        confirmButtonClass: 'el-button--danger',
        cancelButtonText: '取消',
      })
      emit('remove', c.id)
    } catch (e) {
      /* 用户取消 */
    }
  }
}
</script>

<style scoped>
.conv-list {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--lk-border-light, #e4e7ed);
  display: flex;
  flex-direction: column;
  background: var(--lk-bg-page, #f5f7fa);
}
.conv-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  border-bottom: 1px solid var(--lk-border-light, #e4e7ed);
}
.conv-title { font-size: 15px; font-weight: 600; color: var(--lk-text-1, #303133); }
.conv-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.conv-empty {
  text-align: center;
  color: var(--lk-text-3, #6f737a);
  font-size: 13px;
  padding: 30px 0;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.conv-item:hover { background: var(--lk-bg-hover, #f5f7fa); }
.conv-item.active { background: var(--lk-primary-lightest, #ecf5ff); }
.conv-pin { color: var(--lk-primary, #409eff); flex-shrink: 0; }
.conv-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--lk-text-2, #606266);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-item.active .conv-name { color: var(--lk-primary, #409eff); font-weight: 500; }
.conv-more {
  border: none;
  background: transparent;
  color: var(--lk-text-3, #6f737a);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: none;
  align-items: center;
  flex-shrink: 0;
}
.conv-item:hover .conv-more,
.conv-item.active .conv-more { display: inline-flex; }
.conv-more:hover { color: var(--lk-text-1, #303133); background: var(--lk-bg-hover, #eef1f5); }
.conv-danger-item { color: var(--lk-danger, #f56c6c) !important; }

/* 触屏设备无 hover，三点按钮必须常驻显示，否则无法重命名/删除会话 */
@media (hover: none) {
  .conv-more { display: inline-flex; }
}
</style>
