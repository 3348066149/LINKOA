import request from '@/utils/request'

// 附件（上传走 multipart/form-data）
export const uploadAttachment = (file, projectId, projectNodeId) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('projectId', projectId)
  fd.append('projectNodeId', projectNodeId)
  return request.post('/attachment/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0 // 大文件不限时
  })
}
export const listAttachments = (projectNodeId) => request.get('/attachment/list', { params: { projectNodeId } })
export const listByProject = (projectId) => request.get('/attachment/listByProject', { params: { projectId } })
export const deleteAttachment = (data) => request.post('/attachment/delete', data)
export const downloadUrl = (attachmentId) => `/api/attachment/download/${attachmentId}`
