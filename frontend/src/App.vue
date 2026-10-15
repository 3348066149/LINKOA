<template>
  <el-config-provider :locale="zhCn">
    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <!-- 常驻 AI 助手「青青侠」（V1.4.8，全站右下角） -->
    <AiAssistant />
  </el-config-provider>
</template>

<script setup>
// Element Plus 按需引入后，中文 locale 通过 ConfigProvider 注入（等价于原 app.use(ElementPlus, { locale })）
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiAssistant from '@/components/ai/AiAssistant.vue'
import { useUserStore } from '@/stores/user'

// V1.4.19：30 分钟无操作自动登出
const IDLE_TIMEOUT = 30 * 60 * 1000  // 30 分钟
let idleTimer = null
const router = useRouter()
const userStore = useUserStore()

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = setTimeout(() => {
    if (userStore.isLogin) {
      userStore.logout()
      ElMessage.warning('长时间未操作，已自动退出登录')
      router.push('/login')
    }
  }, IDLE_TIMEOUT)
}

const idleEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']

onMounted(() => {
  idleEvents.forEach((evt) => window.addEventListener(evt, resetIdleTimer, { passive: true }))
  resetIdleTimer()
})

onUnmounted(() => {
  idleEvents.forEach((evt) => window.removeEventListener(evt, resetIdleTimer))
  if (idleTimer) clearTimeout(idleTimer)
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }

/* 路由切换过渡（阶段三）：轻量淡入 + 8px 上移，150ms 完成 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* el-descriptions 内容防溢出（V1.4.21）
   背景：客户/我方填写的多行文本可能整段没有任何「断行点」——连续顿号、长英文串、长数字、URL。
   浏览器默认不在这些位置断行，单元格的最小内容宽度会被撑到几千像素（实测 6000px+），
   后果是文本只显示一行、右侧被面板裁掉「后面的根本看不到」，标签列还会被挤成竖排单字。
   统一强制允许任意位置断行，并保留用户输入里的换行（多行文本按多行显示）。 */
.el-descriptions__content {
  word-break: break-all;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.el-descriptions__label {
  white-space: nowrap;
}

/* 动效降级（WCAG 2.3.3）：用户偏好减少动效时关闭过渡 */
@media (prefers-reduced-motion: reduce) {
  .page-fade-enter-active,
  .page-fade-leave-active {
    transition: none;
  }
}
</style>
