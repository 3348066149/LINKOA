import request from '@/utils/request'

// 消息中心
export const myMessages = (params) => request.get('/message/myList', { params })
export const unreadCount = () => request.get('/message/unreadCount')
export const markRead = (data) => request.post('/message/read', data)
export const markReadAll = () => request.post('/message/readAll')
