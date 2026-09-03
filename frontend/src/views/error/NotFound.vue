<template>
  <div class="not-found">
    <div class="nf-art" aria-hidden="true">
      <span class="nf-code">404</span>
      <el-icon :size="56" class="nf-icon"><Files /></el-icon>
    </div>
    <h1 class="nf-title">页面走丢了</h1>
    <p class="nf-desc">您访问的地址不存在或已被移动，请检查链接是否正确</p>
    <div class="nf-actions">
      <el-button type="primary" :icon="HomeFilled" @click="$router.push('/')">返回首页</el-button>
      <el-button :icon="Back" @click="$router.back()">返回上一页</el-button>
    </div>
  </div>
</template>

<script setup>
import { Back, Files, HomeFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
.not-found {
  min-height: calc(100vh - var(--lk-header-height, 60px));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  background: var(--lk-bg-page, #f5f7fa);
}
.nf-art {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}
.nf-code {
  font-size: 96px;
  font-weight: 800;
  letter-spacing: 6px;
  color: var(--lk-primary-light, #79bbff);
  opacity: 0.55;
  line-height: 1;
}
.nf-icon {
  position: absolute;
  color: var(--lk-primary, #409eff);
}
.nf-title { font-size: 20px; color: var(--lk-text-1, #1f2937); margin-bottom: 8px; }
.nf-desc { font-size: 14px; color: var(--lk-text-3, #909399); margin-bottom: 24px; }
.nf-actions { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }

@media (max-width: 480px) {
  .nf-code { font-size: 72px; }
}
</style>
