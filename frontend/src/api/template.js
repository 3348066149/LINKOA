import request from '@/utils/request'

// 流程模板
export const listTemplates = () => request.get('/flowTemplate/list')
export const templateDetail = (id) => request.get(`/flowTemplate/detail/${id}`)
export const addTemplate = (data) => request.post('/flowTemplate/add', data)
export const updateTemplate = (data) => request.post('/flowTemplate/update', data)
export const deleteTemplate = (data) => request.post('/flowTemplate/delete', data)
