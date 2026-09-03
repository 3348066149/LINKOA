import request from '@/utils/request'

// 审计日志
export const globalLogs = (params) => request.get('/sysOperationLog/globalList', { params })
export const projectLogs = (projectId) => request.get('/sysOperationLog/projectLog', { params: { projectId } })
