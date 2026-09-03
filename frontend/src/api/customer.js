import request from '@/utils/request'

// 客户分类
export const listCategories = () => request.get('/customerCategory/list')
export const addCategory = (data) => request.post('/customerCategory/add', data)
export const updateCategory = (data) => request.post('/customerCategory/update', data)
export const deleteCategory = (data) => request.post('/customerCategory/delete', data)

// 客户库
export const listCustomers = (params) => request.get('/customer/list', { params })
export const customerDetail = (id) => request.get(`/customer/detail/${id}`)
export const addCustomer = (data) => request.post('/customer/add', data)
export const updateCustomer = (data) => request.post('/customer/update', data)
export const deleteCustomer = (data) => request.post('/customer/delete', data)

// 客户卡片封面图
export const uploadCustomerCover = (customerId, file) => {
  const fd = new FormData()
  fd.append('customerId', customerId)
  fd.append('file', file)
  return request.post('/customer/cover/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const removeCustomerCover = (customerId) => request.post('/customer/cover/remove', { customerId })
