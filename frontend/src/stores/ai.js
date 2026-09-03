// AI 助手 Pinia 状态：会话列表 + 当前会话消息 + 流式缓冲
import { defineStore } from 'pinia'
import {
  listConversations,
  createConversation,
  getMessages,
  renameConversation,
  pinConversation,
  deleteConversation,
  chatStream,
} from '@/api/ai'

export const useAiStore = defineStore('ai', {
  state: () => ({
    conversations: [],
    currentConversationId: null,
    messages: [],
    streaming: false,
    abortController: null,
  }),

  getters: {
    // 是否为全新空会话（无任何消息）
    isNewConversation: (state) => !state.currentConversationId || state.messages.length === 0,
  },

  actions: {
    async fetchConversations() {
      this.conversations = await listConversations()
    },

    async openConversation(id) {
      // 切换前先中断进行中的流式请求，否则 streaming 会卡在 true
      //（输入框持续禁用、一直显示"停止生成"），且旧请求仍占用连接
      this.stopStreaming()
      this.currentConversationId = id
      this.messages = await getMessages(id)
    },

    async newConversation() {
      this.stopStreaming()
      const { id } = await createConversation()
      this.currentConversationId = id
      this.messages = []
      await this.fetchConversations()
    },

    async removeConversation(id) {
      // 删除的若是正在流式输出的会话，先中断请求再删
      if (this.currentConversationId === id) {
        this.stopStreaming()
      }
      await deleteConversation(id)
      if (this.currentConversationId === id) {
        this.currentConversationId = null
        this.messages = []
      }
      await this.fetchConversations()
    },

    async renameConversation(id, title) {
      await renameConversation(id, title)
      await this.fetchConversations()
    },

    async togglePin(id, pinned) {
      await pinConversation(id, pinned)
      await this.fetchConversations()
    },

    /**
     * 发送消息并流式接收。本地先插入用户消息 + 空 assistant 占位，
     * 流式过程中不断追加占位内容，结束时回填来源引用。
     * @param {string} message 用户输入
     */
    sendMessage(message) {
      if (this.streaming) return
      this.streaming = true

      this.messages.push({ id: null, role: 'user', content: message, sources: [] })
      const assistant = { id: null, role: 'assistant', content: '', sources: [] }
      this.messages.push(assistant)

      this.abortController = chatStream({
        conversationId: this.currentConversationId,
        message,
        onDelta: (delta) => {
          assistant.content += delta
        },
        onDone: (evt) => {
          assistant.id = evt.messageId || null
          assistant.sources = evt.sources || []
          if (evt.conversationId && !this.currentConversationId) {
            this.currentConversationId = evt.conversationId
            this.fetchConversations()
          } else {
            this.fetchConversations()
          }
          this.streaming = false
          this.abortController = null
        },
        onError: (msg) => {
          if (!assistant.content) assistant.content = msg
          this.streaming = false
          this.abortController = null
        },
      })
    },

    stopStreaming() {
      if (this.abortController) {
        this.abortController.abort()
        this.abortController = null
      }
      // 停止时若最后一条 assistant 还没内容，补占位避免空白气泡（V1.4.9）
      const last = this.messages[this.messages.length - 1]
      if (last && last.role === 'assistant' && !last.content) {
        last.content = '（已停止生成）'
      }
      this.streaming = false
    },
  },
})
