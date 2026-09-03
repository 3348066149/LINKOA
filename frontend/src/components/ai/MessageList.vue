<template>
  <div ref="listRef" class="msg-list">
    <!-- 空状态：欢迎 + 推荐问题 -->
    <div v-if="messages.length === 0" class="empty">
      <div class="empty-avatar">
        <img src="/ai-mascot/qingqingxia.png" alt="青青侠" draggable="false" />
      </div>
      <div class="empty-title">你好，我是青青侠～</div>
      <div class="empty-sub">有什么可以帮你的吗？</div>
      <div class="suggest">
        <button
          v-for="q in suggestQuestions"
          :key="q"
          class="suggest-item"
          type="button"
          @click="emit('ask', q)"
        >
          {{ q }}
        </button>
      </div>
    </div>

    <!-- 消息流 -->
    <template v-else>
      <div v-for="(m, i) in messages" :key="m.id ?? `tmp-${i}`" class="msg" :class="m.role">
        <div v-if="m.role === 'assistant'" class="avatar">
          <img src="/ai-mascot/qingqingxia.png" alt="青青侠" draggable="false" />
        </div>
        <div class="bubble">
          <div v-if="m.role === 'assistant'" class="md" v-html="renderMarkdown(m.content)"></div>
          <div v-else class="text">{{ m.content }}</div>

          <!-- 来源引用 -->
          <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="sources">
            <span class="sources-label">引用自系统项目</span>
            <a
              v-for="s in m.sources"
              :key="s.id"
              class="source"
              href="javascript:void(0)"
              @click.prevent="openProject(s.id)"
            >{{ s.projectName }}</a>
          </div>
          <div
            v-else-if="m.role === 'assistant' && m.content && !(streaming && i === messages.length - 1)"
            class="no-source"
          >本回答未引用系统数据</div>

          <!-- 流式输出光标 -->
          <span v-if="m.role === 'assistant' && streaming && i === messages.length - 1" class="cursor"></span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { SUGGEST_QUESTIONS, SUGGEST_QUESTIONS_CLIENT } from '@/config/mascot'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
})
const emit = defineEmits(['ask', 'close'])

const router = useRouter()
const userStore = useUserStore()
const listRef = ref(null)

// 推荐问题按角色区分：客户只看与自己公司相关的问题（V1.4.9）
const suggestQuestions = computed(() =>
  userStore.role === '客户' ? SUGGEST_QUESTIONS_CLIENT : SUGGEST_QUESTIONS
)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

function renderMarkdown(content) {
  try {
    return md.render(content || '')
  } catch {
    return content || ''
  }
}

function openProject(id) {
  if (userStore.role === '客户') {
    router.push(`/client/projects/${id}`)
  } else {
    router.push(`/projects/${id}`)
  }
  // 跳转后关闭 AI 面板，避免面板遮罩盖住项目详情页
  emit('close')
}

// 消息变化或切换会话时滚动到底部
// 依赖同时包含 length：仅比对末条 content 时，切换会话若末条内容相同则不会触发滚动
watch(
  () => [props.messages.length, props.messages[props.messages.length - 1]?.content],
  async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px clamp(12px, 2vw, 24px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty {
  margin: auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px 0;
}
.empty-avatar {
  width: 72px;
  height: 72px;
  margin-bottom: 6px;
}
.empty-avatar img { width: 100%; height: 100%; object-fit: contain; }
.empty-title { font-size: 17px; font-weight: 600; color: var(--lk-text-1, #303133); }
.empty-sub { font-size: 14px; color: var(--lk-text-3, #6f737a); margin-bottom: 14px; }
.suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 420px;
}
.suggest-item {
  border: 1px solid var(--lk-border-light, #e4e7ed);
  background: var(--lk-bg-card, #fff);
  color: var(--lk-text-2, #606266);
  font-size: 13px;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.suggest-item:hover {
  border-color: var(--lk-primary, #409eff);
  color: var(--lk-primary, #409eff);
  background: var(--lk-primary-lightest, #ecf5ff);
}

.msg { display: flex; gap: 10px; }
.msg.user { justify-content: flex-end; }
.avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--lk-bg-card, #fff);
  border: 1px solid var(--lk-border-light, #e4e7ed);
  overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: contain; }
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg.assistant .bubble {
  background: var(--lk-bg-card, #fff);
  color: var(--lk-text-1, #303133);
  border: 1px solid var(--lk-border-light, #e4e7ed);
  border-top-left-radius: 4px;
}
.msg.user .bubble {
  background: var(--lk-primary, #409eff);
  color: #fff;
  border-top-right-radius: 4px;
}
.msg.user .text { white-space: pre-wrap; }

.sources {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--lk-border-light, #e4e7ed);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.sources-label { font-size: 12px; color: var(--lk-text-3, #6f737a); }
.source {
  font-size: 12px;
  color: var(--lk-primary, #409eff);
  text-decoration: none;
  background: var(--lk-primary-lightest, #ecf5ff);
  padding: 2px 8px;
  border-radius: 6px;
}
.source:hover { text-decoration: underline; }

.no-source {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--lk-border-light, #e4e7ed);
  font-size: 12px;
  color: var(--lk-text-4, #a0a3a8);
}

.cursor {
  display: inline-block;
  width: 8px;
  height: 15px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--lk-primary, #409eff);
  animation: blink 0.9s steps(1) infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>

<!-- markdown 渲染内容为 v-html 注入，样式须全局作用 -->
<style>
.msg-list .md > *:first-child { margin-top: 0; }
.msg-list .md > *:last-child { margin-bottom: 0; }
.msg-list .md p { margin: 0.4em 0; }
.msg-list .md h1, .msg-list .md h2, .msg-list .md h3, .msg-list .md h4 { margin: 0.8em 0 0.4em; font-weight: 600; line-height: 1.4; }
.msg-list .md h1 { font-size: 1.3em; }
.msg-list .md h2 { font-size: 1.2em; }
.msg-list .md h3 { font-size: 1.1em; }
.msg-list .md ul, .msg-list .md ol { padding-left: 1.4em; margin: 0.4em 0; }
.msg-list .md li { margin: 0.2em 0; }
.msg-list .md code {
  font-family: 'Consolas', 'Menlo', monospace;
  font-size: 0.9em;
  background: var(--lk-bg-hover, #f5f7fa);
  padding: 1px 5px;
  border-radius: 4px;
}
.msg-list .md pre {
  background: #2d2d2d;
  color: #e6e6e6;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5em 0;
}
.msg-list .md pre code { background: transparent; color: inherit; padding: 0; }
.msg-list .md blockquote {
  border-left: 3px solid var(--lk-border, #dcdfe6);
  padding-left: 10px;
  color: var(--lk-text-3, #6f737a);
  margin: 0.5em 0;
}
.msg-list .md table { border-collapse: collapse; margin: 0.5em 0; font-size: 13px; }
.msg-list .md th, .msg-list .md td { border: 1px solid var(--lk-border-light, #e4e7ed); padding: 5px 10px; }
.msg-list .md th { background: var(--lk-bg-hover, #f5f7fa); }
.msg-list .md a { color: var(--lk-primary, #409eff); }
</style>
