import request from '@/utils/request'

// 客户审核节点（V1.4.19）
export const listPendingReviews = () => request.get('/review/pending')
export const submitReview = (data) => request.post('/review/submit', data)
// 管理员重置审核（V1.4.20）
export const resetReview = (projectNodeId) => request.post('/review/reset', { projectNodeId })

// 客户审核反馈文件上传（V1.4.22）：客户专用，支持图片/PDF/视频等，返回相对路径。
// 客户账号无权限调用设计师侧的 /projectNode/formImage/upload（会被 403 拦截）。
export const uploadReviewFile = (file, projectNodeId) => {
  const form = new FormData()
  form.append('file', file)
  form.append('projectNodeId', String(projectNodeId))
  return request.post('/review/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
