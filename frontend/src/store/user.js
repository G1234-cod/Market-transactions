/** 全局用户状态 */
import { reactive, computed } from 'vue'

const state = reactive({
  user: null,
})

export function useUser() {
  function login(user) {
    state.user = user
    // ✅ 修复：同时存储 token 和用户信息，支持刷新后恢复会话
    localStorage.setItem('token', user.access_token || '')
    try {
      localStorage.setItem('user_info', JSON.stringify({
        user_id: user.user_id,
        username: user.username,
        role: user.role || 'user',
      }))
    } catch { /* ignore quota errors */ }
  }

  function logout() {
    state.user = null
    localStorage.removeItem('token')
    localStorage.removeItem('user_info')
  }

  // ✅ 修复：页面加载时从 localStorage 恢复会话
  function init() {
    if (state.user) return  // 已初始化
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const info = JSON.parse(localStorage.getItem('user_info') || '{}')
      if (info.user_id) {
        state.user = {
          user_id: info.user_id,
          username: info.username || '',
          role: info.role || 'user',
          access_token: token,
        }
      }
    } catch {
      // 数据损坏，清除
      localStorage.removeItem('token')
      localStorage.removeItem('user_info')
    }
  }

  const isLoggedIn = computed(() => !!state.user)
  const userId = computed(() => state.user?.user_id || 0)
  const role = computed(() => state.user?.role || 'user')

  return { state, login, logout, init, isLoggedIn, userId, role }
}
