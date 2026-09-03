import request from '@/utils/request'

// 项目画布节点
export const addNode = (data) => request.post('/projectNode/add', data)
export const updateNode = (data) => request.post('/projectNode/update', data)
export const batchUpdatePositions = (data) => request.post('/projectNode/batchUpdatePositions', data)
export const deleteNode = (data) => request.post('/projectNode/delete', data)
export const getNodeForm = (projectNodeId) => request.get(`/projectNode/getForm/${projectNodeId}`)
export const saveFormValue = (data) => request.post('/projectNode/saveFormValue', data)

// 节点表单「上传图像」字段（V1.4.3）：multipart，返回相对路径
export const uploadFormImage = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/projectNode/formImage/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 项目节点连线
export const addEdge = (data) => request.post('/projectNodeEdge/add', data)
export const deleteEdge = (data) => request.post('/projectNodeEdge/delete', data)
