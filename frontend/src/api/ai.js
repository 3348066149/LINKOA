// AI 助手接口封装：会话 CRUD 走 axios，流式对话走 fetch 读流
import request from '@/utils/request'
import { getToken } from '@/utils/auth'

// ---- 会话 CRUD ----
export const listConversations = () => request.get('/ai/conversations')
export const createConversation = () => request.post('/ai/conversations')
export const getMessages = (conversationId) => request.get(`/ai/conversations/${conversationId}/messages`)
export const renameConversation = (conversationId, title) => request.patch(`/ai/conversations/${conversationId}`, { title })
export const pinConversation = (conversationId, pinned) => request.post(`/ai/conversations/${conversationId}/pin`, { pinned })
export const deleteConversation = (conversationId) => request.delete(`/ai/conversations/${conversationId}`)

// ---- 管理员 AI 配置 ----
export const getAiConfig = () => request.get('/ai/config')
export const updateAiConfig = (data) => request.put('/ai/config', data)

/**
 * 流式对话：使用 fetch 读取 SSE 流（后端 media_type=text/event-stream）。
 * 返回 AbortController，调用方可通过 .abort() 停止生成。
 *
 * @param {object} params
 * @param {number|null} params.conversationId 会话ID，为空则后端新建
 * @param {string} params.message 用户输入
 * @param {(delta:string)=>void} params.onDelta 增量文本回调
 * @param {(evt:object)=>void} params.onDone 结束回调（evt 含 conversationId/messageId/sources）
 * @param {(msg:string)=>void} params.onError 出错回调
 * @returns {AbortController}
 */
export function chatStream({ conversationId, message, onDelta, onDone, onError }) {
  const controller = new AbortController()

  fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ conversationId, message }),
    signal: controller.signal,
  })
    .then(async (res) => {
      const contentType = res.headers.get('content-type') || ''
      // 非流式响应（如鉴权失败的业务 JSON）直接按错误处理
      if (contentType.includes('application/json')) {
        let msg = '请求失败'
        try {
          const data = await res.json()
          msg = data.msg || msg
        } catch (e) { /* ignore */ }
        onError && onError(msg)
        return
      }
      if (!res.body) {
        onError && onError('当前浏览器不支持流式响应')
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let settled = false // 是否已收到 done / error（用于流异常中断兜底）

      // 逐块读取，按 \n\n 切分 SSE 事件
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const line = raw.trim()
          if (!line.startsWith('data:')) continue
          let evt
          try {
            evt = JSON.parse(line.slice(5).trim())
          } catch (e) {
            continue
          }
          if (evt.type === 'delta') onDelta && onDelta(evt.content)
          else if (evt.type === 'error') {
            settled = true
            onError && onError(evt.message)
          } else if (evt.type === 'done') {
            settled = true
            onDone && onDone(evt)
          }
        }
      }

      // 兜底：流读到结尾却没收到 done/error（连接被提前关闭或代理超时），
      // 仍结束本次生成，避免前端「生成中」状态永久卡住、已生成内容丢失。
      if (!settled) {
        onDone && onDone({})
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError && onError(err.message || '网络异常')
      }
    })

  return controller
}
