import request from '@/utils/request'

// 客户审核节点（V1.4.19）
export const listPendingReviews = () => request.get('/review/pending')
export const submitReview = (data) => request.post('/review/submit', data)
// 管理员重置审核（V1.4.20）
export const resetReview = (projectNodeId) => request.post('/review/reset', { projectNodeId })
