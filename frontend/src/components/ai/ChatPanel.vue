<template>
  <div class="chat-panel">
    <!-- 头部 -->
    <header class="panel-head">
      <div class="head-left">
        <el-icon v-if="isMobile" class="head-menu" :size="20" @click="drawerVisible = true">
          <ChatDotRound />
        </el-icon>
        <img class="head-avatar" src="/ai-mascot/qingqingxia.png" alt="青青侠" draggable="false" />
        <div class="head-title">
          <div class="head-name">青青侠</div>
          <div class="head-desc">智能助手 · 在线</div>
        </div>
      </div>
      <button class="head-close" type="button" title="关闭" @click="$emit('close')">
        <el-icon :size="18"><Close /></el-icon>
      </button>
    </header>

    <!-- 主体 -->
    <div class="panel-body">
      <!-- 桌面端：左侧会话列表 -->
      <ConversationList
        v-if="!isMobile"
        :conversations="aiStore.conversations"
        :current-id="aiStore.currentConversationId"
        @new="onNew"
        @select="onSelect"
        @remove="onRemove"
        @rename="onRename"
        @pin="onPin"
      />
      <div class="panel-main">
        <MessageList :messages="aiStore.messages" :streaming="aiStore.streaming" @ask="onSend" @close="$emit('close')" />
        <ChatInput :streaming="aiStore.streaming" @send="onSend" @stop="aiStore.stopStreaming" />
      </div>
    </div>

    <!-- 移动端：会话列表抽屉 -->
    <el-drawer v-model="drawerVisible" direction="ltr" size="75%" :with-header="false" class="conv-drawer">
      <ConversationList
        :conversations="aiStore.conversations"
        :current-id="aiStore.currentConversationId"
        @new="onNew"
        @select="(id) => { onSelect(id); drawerVisible = false }"
        @remove="onRemove"
        @rename="onRename"
        @pin="onPin"
      />
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ChatDotRound, Close } from '@element-plus/icons-vue'
import { useAiStore } from '@/stores/ai'
import { useIsMobile } from '@/composables/useIsMobile'
import ConversationList from './ConversationList.vue'
import MessageList from './MessageList.vue'
import ChatInput from './ChatInput.vue'

defineEmits(['close'])

const aiStore = useAiStore()
const { isMobile } = useIsMobile(768)
const drawerVisible = ref(false)

onMounted(() => {
  aiStore.fetchConversations()
})

async function onNew() {
  await aiStore.newConversation()
  drawerVisible.value = false
}

async function onSelect(id) {
  await aiStore.openConversation(id)
}

async function onRemove(id) {
  await aiStore.removeConversation(id)
  // 移动端：删除后关抽屉，否则停留在已失效的列表上
  drawerVisible.value = false
}

async function onRename(id, title) {
  await aiStore.renameConversation(id, title)
  // 移动端：重命名后关抽屉回到对话
  drawerVisible.value = false
}

async function onPin(id, pinned) {
  await aiStore.togglePin(id, pinned)
}

function onSend(message) {
  aiStore.sendMessage(message)
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  width: min(1100px, 66vw);
  height: min(760px, 80vh);
  max-width: 94vw;
  max-height: 92vh;
  background: var(--lk-bg-card, #fff);
  border-radius: var(--lk-radius-xl, 16px);
  box-shadow: var(--lk-shadow-lg, 0 12px 32px rgba(0, 0, 0, 0.12));
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--lk-border-light, #e4e7ed);
  background: var(--lk-bg-card, #fff);
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.head-menu {
  cursor: pointer;
  color: var(--lk-text-2, #606266);
}
.head-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: contain;
  border: 1px solid var(--lk-border-light, #e4e7ed);
  background: #fff;
}
.head-title { display: flex; flex-direction: column; gap: 1px; }
.head-name { font-size: 15px; font-weight: 600; color: var(--lk-text-1, #303133); }
.head-desc { font-size: 12px; color: var(--lk-text-3, #6f737a); }
.head-close {
  border: none;
  background: transparent;
  color: var(--lk-text-3, #6f737a);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
}
.head-close:hover { background: var(--lk-bg-hover, #f5f7fa); color: var(--lk-text-1, #303133); }

.panel-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.panel-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

@media (max-width: 767px) {
  .chat-panel {
    width: 100vw;
    /* dvh 解决 iOS Safari 地址栏收缩时 100vh 溢出屏幕的问题（不支持时回退 vh） */
    height: 100vh;
    height: 100dvh;
    max-width: 100vw;
    max-height: 100vh;
    max-height: 100dvh;
    border-radius: 0;
  }
}
</style>
