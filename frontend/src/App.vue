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
import AiAssistant from '@/components/ai/AiAssistant.vue'
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

/* 动效降级（WCAG 2.3.3）：用户偏好减少动效时关闭过渡 */
@media (prefers-reduced-motion: reduce) {
  .page-fade-enter-active,
  .page-fade-leave-active {
    transition: none;
  }
}
</style>
