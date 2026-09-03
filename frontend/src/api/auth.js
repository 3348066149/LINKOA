import request from '@/utils/request'

// 登录 / 修改密码
export const login = (data) => request.post('/login', data)
export const updateMyPwd = (data) => request.post('/user/updateMyPwd', data)
