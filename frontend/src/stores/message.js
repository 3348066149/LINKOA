// Pinia 消息未读数（顶部栏铃铛红点）
import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useMessageStore = defineStore('message', {
  state: () => ({
    unreadCount: 0
  }),
  actions: {
    async fetchUnread() {
      try {
        const data = await request.get('/message/unreadCount')
        this.unreadCount = data?.count ?? 0
      } catch {
        // 未登录或网络异常时静默，不打断页面
      }
    }
  }
})
