import request from '@/utils/request'

// 部门管理（仅管理员）
export const listDepts = () => request.get('/sysDept/list')
export const addDept = (data) => request.post('/sysDept/add', data)
export const updateDept = (data) => request.post('/sysDept/update', data)
export const deleteDept = (data) => request.post('/sysDept/delete', data)
