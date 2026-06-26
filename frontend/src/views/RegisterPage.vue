<template>
  <div class="min-h-screen flex items-center justify-center px-4 pt-12 pb-8">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="relative inline-block">
          <span class="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-500 via-primary-600 to-primary-500 inline-flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-accent-500/30 animate-float">二</span>
          <div class="absolute -inset-4 bg-gradient-to-br from-accent-400/20 to-primary-400/20 rounded-3xl blur-xl -z-10"></div>
        </div>
        <h1 class="mt-6 text-2xl font-bold text-gray-800">创建账号</h1>
        <p class="text-gray-400 text-sm mt-2">加入智能二手交易社区</p>
      </div>

      <div class="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 p-6 space-y-5">
        <form @submit.prevent="doRegister" aria-label="注册表单">
          <div class="space-y-1.5">
            <label for="reg-username" class="block text-xs text-gray-500 font-medium uppercase tracking-wider">用户名</label>
            <input 
              id="reg-username"
              v-model="username" 
              placeholder="至少 2 个字符…"
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
            <label for="reg-password" class="block text-xs text-gray-500 font-medium uppercase tracking-wider">密码</label>
            <input 
              id="reg-password"
              v-model="password" 
              type="password" 
              placeholder="至少 6 位…"
              maxlength="50"
              autocomplete="new-password"
              name="password"
              class="w-full px-4 py-3 bg-gray-50/80 border border-gray-200 rounded-xl text-sm text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-1.5">
            <label for="reg-confirm" class="block text-xs text-gray-500 font-medium uppercase tracking-wider">确认密码</label>
            <input 
              id="reg-confirm"
              v-model="confirm" 
              type="password" 
              placeholder="再次输入密码…"
              maxlength="50"
              autocomplete="new-password"
              name="confirm_password"
              class="w-full px-4 py-3 bg-gray-50/80 border rounded-xl text-sm text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
              :class="confirm && password !== confirm ? 'border-red-300 bg-red-50/80 focus:border-red-400 focus:ring-red-100' : 'border-gray-200'"
              :aria-invalid="confirm && password !== confirm"
            />
            <p v-if="confirm && password !== confirm" class="text-xs text-red-500 mt-1 ml-1" role="alert">两次密码不一致</p>
          </div>

          <div v-if="error" class="text-xs text-red-500 text-center mt-2" role="alert" aria-live="polite">{{ error }}</div>

          <button 
            type="submit"
            class="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-accent-500 via-primary-600 to-primary-500 hover:from-accent-600 hover:via-primary-700 hover:to-primary-600 shadow-lg shadow-accent-500/25 hover:shadow-xl hover:shadow-accent-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0"
            :disabled="!canSubmit || loading"
          >
            <span v-if="loading" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '注册中…' : '注册' }}
          </button>
        </form>

        <p class="text-center text-xs text-gray-400 pt-2">
          已有账号？<router-link to="/login" class="text-primary-600 hover:text-primary-700 hover:underline transition-colors">去登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../store/user.js'
import { register as apiRegister } from '../api/index.js'

const router = useRouter()
const { login } = useUser()

const username = ref('')
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() =>
  username.value.trim().length >= 2 &&
  password.value.length >= 6 &&
  password.value === confirm.value
)

async function doRegister() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    const user = await apiRegister(username.value.trim(), password.value)
    login(user)
    router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
