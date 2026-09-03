import request from '@/utils/request'

// 用户管理（仅管理员）
export const listUsers = () => request.get('/sysUser/list')
export const createUser = (data) => request.post('/sysUser/create', data)
export const updateUser = (data) => request.post('/sysUser/update', data)
export const resetPwd = (data) => request.post('/sysUser/resetPwd', data)
export const setEnable = (data) => request.post('/sysUser/setEnable', data)
export const deleteUser = (data) => request.post('/sysUser/delete', data)
// V1.4.6 登录防暴力破解：管理员手动解锁被锁定的账号
export const unlockUser = (data) => request.post('/sysUser/unlock', data)
