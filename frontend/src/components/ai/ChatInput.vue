<template>
  <div class="chat-input">
    <el-input
      v-model="text"
      type="textarea"
      :rows="1"
      :autosize="{ minRows: 1, maxRows: 5 }"
      placeholder="输入问题，Enter 发送，Shift+Enter 换行"
      resize="none"
      :disabled="streaming"
      @keydown.enter.exact="onEnter"
    />
    <div class="input-actions">
      <div class="spacer"></div>

      <el-button v-if="streaming" type="danger" plain @click="$emit('stop')">
        <el-icon><VideoPause /></el-icon><span>停止生成</span>
      </el-button>
      <el-button v-else type="primary" :disabled="!text.trim()" @click="submit">
        <el-icon><Promotion /></el-icon><span>发送</span>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'

defineProps({
  streaming: { type: Boolean, default: false },
})
const emit = defineEmits(['send', 'stop'])

const text = ref('')

// Enter 发送，但必须跳过输入法组词阶段：
// 中文/日文拼写时按 Enter 是「确认候选词」，此时 isComposing 为 true（部分浏览器为 keyCode 229）。
// 若不拦截，会把尚未组词完成的半成品直接发送出去。
function onEnter(e) {
  if (e.isComposing || e.keyCode === 229) return
  e.preventDefault()
  submit()
}

function submit() {
  const val = text.value.trim()
  if (!val) return
  emit('send', val)
  text.value = ''
}
</script>

<style scoped>
.chat-input {
  border-top: 1px solid var(--lk-border-light, #e4e7ed);
  padding: 12px clamp(12px, 2vw, 16px);
  background: var(--lk-bg-card, #fff);
}
.chat-input :deep(.el-textarea__inner) {
  box-shadow: none;
  border-radius: 10px;
  background: var(--lk-bg-page, #f5f7fa);
}
.input-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.spacer { flex: 1; }
</style>
