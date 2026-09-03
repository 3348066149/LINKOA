import request from '@/utils/request'

// 客户满意度评价
export const submitEvaluation = (data) => request.post('/evaluation/submit', data)
export const getEvaluation = (projectId) => request.get(`/evaluation/${projectId}`)
export const saveReflection = (data) => request.post('/evaluation/reflection', data)
