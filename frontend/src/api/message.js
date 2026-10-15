import request from '@/utils/request'

// 消息中心
export const myMessages = (params) => request.get('/message/myList', { params })
export const unreadCount = () => request.get('/message/unreadCount')
export const markRead = (data) => request.post('/message/read', data)
// 一键已读（V1.4.21）：不传参数 = 全部；传 { projectId } = 只标记该项目
export const markReadAll = (data = {}) => request.post('/message/readAll', data)
