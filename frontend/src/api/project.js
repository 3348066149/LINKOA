import request from '@/utils/request'

// 项目基础
export const createProject = (data) => request.post('/project/create', data)
export const listProjects = (params) => request.get('/project/list', { params })
export const projectDetail = (id) => request.get(`/project/detail/${id}`)
export const updateProjectBase = (data) => request.post('/project/updateBase', data)
export const archiveProject = (data) => request.post('/project/archive', data)
export const unArchiveProject = (data) => request.post('/project/unArchive', data)
export const deleteProject = (data) => request.post('/project/delete', data)

// 卡片封面图
export const uploadProjectCover = (projectId, file) => {
  const fd = new FormData()
  fd.append('projectId', projectId)
  fd.append('file', file)
  return request.post('/project/cover/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const removeProjectCover = (data) => request.post('/project/cover/remove', data)

// 项目环节（V1.4.19）
export const saveProjectStages = (data) => request.post('/project/stage/save', data)
