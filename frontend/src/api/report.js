import request from '@/utils/request'

// 报表导出（blob 文件流，响应拦截器直接放行）
export const exportProjects = (params) =>
  request.get('/report/exportProject', { params, responseType: 'blob' })
