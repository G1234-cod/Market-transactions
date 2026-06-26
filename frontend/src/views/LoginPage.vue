<template>
  <div class="min-h-screen flex items-center justify-center px-4 pt-12 pb-8">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="relative inline-block">
          <span class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 via-primary-600 to-accent-500 inline-flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-primary-500/30 animate-float">二</span>
          <div class="absolute -inset-4 bg-gradient-to-br from-primary-400/20 to-accent-400/20 rounded-3xl blur-xl -z-10"></div>
        </div>
        <h1 class="mt-6 text-2xl font-bold text-gray-800">智能二手商品发布助手</h1>
        <p class="text-gray-400 text-sm mt-2">登录您的账号，开始发布二手商品</p>
      </div>

      <div class="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 p-6 space-y-5">
        <form @submit.prevent="doLogin" aria-label="登录表单">
          <div class="space-y-1.5">
            <label for="username" class="block text-xs text-gray-500 font-medium uppercase tracking-wider">用户名</label>
            <input 
              id="username"
              v-model="username" 
              placeholder="请输入用户名…"
              maxlength="30"
              autocomplete="username"
              name="username"
              spellcheck="false"
              class="w-full px-4 py-3 bg-gray-50/80 border border-gray-200 rounded-xl text-sm text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-1.5">
            <label for="password" class="block text-xs text-gray-500 font-medium uppercase tracking-wider">密码</label>
            <input 
              id="password"
              v-model="password" 
              type="password" 
              placeholder="请输入密码…"
              maxlength="50"
              autocomplete="current-password"
              name="password"
              class="w-full px-4 py-3 bg-gray-50/80 border border-gray-200 rounded-xl text-sm text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div v-if="error" class="text-xs text-red-500 text-center mt-2" role="alert" aria-live="polite">{{ error }}</div>

          <button 
            type="submit"
            class="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-primary-500 via-primary-600 to-accent-500 hover:from-primary-600 hover:via-primary-700 hover:to-accent-600 shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0"
            :disabled="!canSubmit || loading"
          >
            <span v-if="loading" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="text-center text-xs text-gray-400 pt-2">
          还没有账号？<router-link to="/register" class="text-primary-600 hover:text-primary-700 hover:underline transition-colors">注册新账号</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../store/user.js'
import { login as apiLogin } from '../api/index.js'

const router = useRouter()
const { login } = useUser()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() => username.value.trim() && password.value)

async function doLogin() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    const user = await apiLogin(username.value.trim(), password.value)
    login(user)
    router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
