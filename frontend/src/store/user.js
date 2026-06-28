/** 全局用户状态 */
import { reactive, computed } from 'vue'

const state = reactive({
  user: null,
})

export function useUser() {
  function login(user) {
    state.user = user
    localStorage.setItem('token', user.access_token || '')
  }

  function logout() {
    state.user = null
    localStorage.removeItem('token')
  }

  const isLoggedIn = computed(() => !!state.user)
  const userId = computed(() => state.user?.user_id || 0)

  return { state, login, logout, isLoggedIn, userId }
}
