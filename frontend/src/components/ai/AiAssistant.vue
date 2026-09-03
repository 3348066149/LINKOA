<template>
  <template v-if="visible">
    <!-- 常驻形象（关闭态显示） -->
    <transition name="mascot">
      <MascotFloat v-if="!open" @open="open = true" />
    </transition>

    <!-- 遮罩 -->
    <transition name="mask">
      <div v-if="open" class="ai-mask" @click="close"></div>
    </transition>

    <!-- 对话弹窗（从右下角平滑展开到居中） -->
    <transition name="panel">
      <div v-if="open" class="panel-anchor">
        <ChatPanel @close="close" />
      </div>
    </transition>
  </template>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import MascotFloat from './MascotFloat.vue'
import ChatPanel from './ChatPanel.vue'

const route = useRoute()
const userStore = useUserStore()
const open = ref(false)

// 仅登录后展示，登录页/未登录不显示
const visible = computed(() => userStore.isLogin && route.path !== '/login')

function close() {
  open.value = false
}
</script>

<style scoped>
.ai-mask {
  position: fixed;
  inset: 0;
  z-index: 1900;
  background: rgba(0, 0, 0, 0.32);
}

.panel-anchor {
  position: fixed;
  inset: 0;
  /* 面板 1950 < Element Plus 弹层默认 2000，保证面板内的 dropdown/tooltip/MessageBox
     确认框能盖过面板，不被遮挡（V1.4.10 BUG 修复） */
  z-index: 1950;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.panel-anchor > :deep(*) {
  pointer-events: auto;
}

/* ---- 形象淡入淡出 ---- */
.mascot-enter-active,
.mascot-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}
.mascot-enter-from,
.mascot-leave-to {
  opacity: 0;
  transform: scale(0.4);
}

/* ---- 遮罩淡入淡出 ---- */
.mask-enter-active,
.mask-leave-active {
  transition: opacity 0.3s ease;
}
.mask-enter-from,
.mask-leave-to {
  opacity: 0;
}

/* ---- 弹窗从右下角平滑缩放展开 ---- */
.panel-enter-active {
  transition: opacity 0.3s ease, transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: bottom right;
}
.panel-leave-active {
  transition: opacity 0.25s ease, transform 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: bottom right;
}
.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: scale(0.4);
}

@media (prefers-reduced-motion: reduce) {
  .mascot-enter-active, .mascot-leave-active,
  .mask-enter-active, .mask-leave-active,
  .panel-enter-active, .panel-leave-active {
    transition: opacity 0.15s ease;
  }
}
</style>
