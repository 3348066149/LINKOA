import request from '@/utils/request'

// 评论
export const listComments = (projectId) => request.get('/comment/list', { params: { projectId } })
export const addComment = (data) => request.post('/comment/add', data)
export const deleteComment = (data) => request.post('/comment/delete', data)
