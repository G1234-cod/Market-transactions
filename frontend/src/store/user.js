/** 全局用户状态（简单响应式共享） */
import { reactive, computed } from 'vue'

const state = reactive({
  user: null, // { id, username }
})

export function useUser() {
  function login(user) {
    state.user = user
    localStorage.setItem('user', JSON.stringify(user))
  }

  function logout() {
    state.user = null
    localStorage.removeItem('user')
  }

  function restoreUser() {
    const raw = localStorage.getItem('user')
    if (raw) {
      try { state.user = JSON.parse(raw) } catch { state.user = null }
    }
  }

  const isLoggedIn = computed(() => !!state.user)
  const userId = computed(() => state.user?.id || 1)

  return { state, login, logout, restoreUser, isLoggedIn, userId }
}
