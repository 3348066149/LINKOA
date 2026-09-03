import request from '@/utils/request'

// 节点模板（读取全角色；写操作仅管理员）
export const listNodeTemplates = () => request.get('/nodeTemplate/list')
export const addNodeTemplate = (data) => request.post('/nodeTemplate/add', data)
export const updateNodeTemplate = (data) => request.post('/nodeTemplate/update', data)
export const deleteNodeTemplate = (data) => request.post('/nodeTemplate/delete', data)

// 自定义图标上传（管理员）：multipart，返回相对路径
export const uploadNodeIcon = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/nodeTemplate/icon/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
