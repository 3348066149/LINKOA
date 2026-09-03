import request from '@/utils/request'

// 自定义角色（仅管理员）
export const listRoles = () => request.get('/sysRole/list')
export const addRole = (data) => request.post('/sysRole/add', data)
export const deleteRole = (data) => request.post('/sysRole/delete', data)
