// Axios 实例 + 统一拦截器
// 请求拦截：自动注入 Authorization: Bearer <token>
// 响应拦截：code===200 返回 data；非 200 用 ElMessage 弹窗；401 清除登录态跳 /login
// V1.4.6：支持 { silent: true }，跳过全局错误弹窗，由调用方自行展示（如登录页内联提示）
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

/** 是否静默（不弹全局错误提示） */
const isSilent = (config) => Boolean(config && config.silent)

request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    // 文件流（Excel 导出等）直接放行
    if (response.config.responseType === 'blob') {
      return response
    }
    const { code, msg, data } = response.data
    if (code === 200) {
      return data
    }
    if (code === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
      if (!isSilent(response.config)) {
        ElMessage.error(msg || '登录已过期，请重新登录')
      }
      return Promise.reject(new Error(msg || '401'))
    }
    if (!isSilent(response.config)) {
      ElMessage.error(msg || '操作失败')
    }
    return Promise.reject(new Error(msg || `code=${code}`))
  },
  (error) => {
    if (!isSilent(error.config)) {
      ElMessage.error(error.message || '网络异常')
    }
    return Promise.reject(error)
  }
)

export default request
