<template>
  <div class="mascot-wrap">
    <transition name="bubble">
      <div v-if="showBubble" class="bubble" role="status">
        {{ bubbleText }}
      </div>
    </transition>
    <div class="mascot-float">
      <button
        class="mascot"
        type="button"
        aria-label="打开青青侠 AI 助手"
        @pointerenter="onEnter"
        @pointerleave="onLeave"
        @click="$emit('open')"
      >
        <img src="/ai-mascot/qingqingxia.png" alt="青青侠" draggable="false" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { MASCOT_BUBBLES } from '@/config/mascot'

defineEmits(['open'])

const showBubble = ref(false)
const bubbleText = ref(MASCOT_BUBBLES[0])
let hideTimer = null

function onEnter() {
  // 随机取一条气泡文案
  bubbleText.value = MASCOT_BUBBLES[Math.floor(Math.random() * MASCOT_BUBBLES.length)]
  showBubble.value = true
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

function onLeave() {
  showBubble.value = false
}
</script>

<style scoped>
.mascot-wrap {
  position: fixed;
  right: clamp(16px, 3vw, 28px);
  bottom: clamp(16px, 3vw, 28px);
  /* 常驻形象只需盖过页面内容(<1000)，保持低于 AI 面板(1950)与 Element Plus 弹层(2000+) */
  z-index: 1500;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* 浮动动画放在外层容器（V1.4.9），hover 的 scale 用 transition 作用于内层按钮，
   两者不再争抢 transform，消除 hover 瞬间位移突变 + 反复切换导致的频闪 */
.mascot-float {
  animation: mascot-float 3.2s ease-in-out infinite;
  will-change: transform;
}

.mascot {
  width: 72px;
  height: 72px;
  border: none;
  padding: 0;
  cursor: pointer;
  background: transparent;
  border-radius: 50%;
  transition: transform 0.2s var(--lk-ease, cubic-bezier(0.4, 0, 0.2, 1));
  filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.16));
  animation: mascot-glow 3.2s ease-in-out infinite;
}

@keyframes mascot-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0); }
  50% { box-shadow: 0 0 28px 9px rgba(226, 35, 26, 0.22); }
}

.mascot:hover { transform: scale(1.12); }

.mascot img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.bubble {
  max-width: 210px;
  background: var(--lk-bg-card, #ffffff);
  color: var(--lk-text-1, #303133);
  font-size: 13px;
  line-height: 1.5;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid var(--lk-border-light, #e4e7ed);
  box-shadow: var(--lk-shadow-md, 0 4px 16px rgba(0, 0, 0, 0.08));
  position: relative;
  white-space: nowrap;
  will-change: transform, opacity;
}

.bubble::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 10px;
  height: 10px;
  background: var(--lk-bg-card, #ffffff);
  border-right: 1px solid var(--lk-border-light, #e4e7ed);
  border-bottom: 1px solid var(--lk-border-light, #e4e7ed);
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.bubble-enter-active,
.bubble-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.bubble-enter-from,
.bubble-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (prefers-reduced-motion: reduce) {
  .mascot-float { animation: none; }
}
</style>
