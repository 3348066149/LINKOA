// Pinia 用户状态：token + userInfo，持久化到 localStorage
import { defineStore } from 'pinia'
import { clearAuth, getToken, getUserInfo, setToken, setUserInfo } from '@/utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    userInfo: getUserInfo()
  }),
  getters: {
    isLogin: (state) => !!state.token,
    role: (state) => state.userInfo?.role || '',
    realName: (state) => state.userInfo?.realName || ''
  },
  actions: {
    setLogin(token, userInfo) {
      this.token = token
      this.userInfo = userInfo
      setToken(token)
      setUserInfo(userInfo)
    },
    logout() {
      this.token = ''
      this.userInfo = null
      clearAuth()
    },
    // 是否有权访问指定角色集合
    hasRole(roles) {
      if (!roles || roles.length === 0) return true
      return roles.includes(this.role)
    }
  }
})
