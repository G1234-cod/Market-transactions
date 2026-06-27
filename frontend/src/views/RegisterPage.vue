<template>
  <div class="min-h-screen flex items-center justify-center px-4 pt-12 pb-8 bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-br from-primary-400/30 to-primary-600/30 rounded-3xl blur-2xl animate-pulse"></div>
          <div class="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-400 via-primary-500 to-primary-600 inline-flex items-center justify-center text-white text-4xl font-bold shadow-2xl shadow-primary-500/40">二</div>
        </div>
        <h1 class="mt-8 text-2xl font-bold text-white">创建账号</h1>
        <p class="text-primary-300 text-sm mt-2">加入智能二手交易社区</p>
      </div>

      <div class="bg-primary-800/60 backdrop-blur-xl rounded-2xl shadow-2xl border border-primary-700/50 p-7 space-y-6">
        <form @submit.prevent="doRegister" aria-label="注册表单">
          <div class="space-y-2">
            <label for="reg-username" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">用户名</label>
            <input 
              id="reg-username"
              v-model="username" 
              placeholder="至少 2 个字符…"
              maxlength="30"
              autocomplete="username"
              name="username"
              spellcheck="false"
              class="w-full px-4 py-3 bg-primary-900/50 border border-primary-600 rounded-xl text-sm text-white placeholder:text-primary-400 focus:bg-primary-900 focus:border-primary-400 focus:ring-2 focus:ring-primary-500/30 focus:outline-none transition-all"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-2">
            <label for="reg-password" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">密码</label>
            <input 
              id="reg-password"
              v-model="password" 
              type="password" 
              placeholder="至少 6 位…"
              maxlength="50"
              autocomplete="new-password"
              name="password"
              class="w-full px-4 py-3 bg-primary-900/50 border border-primary-600 rounded-xl text-sm text-white placeholder:text-primary-400 focus:bg-primary-900 focus:border-primary-400 focus:ring-2 focus:ring-primary-500/30 focus:outline-none transition-all"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-2">
            <label for="reg-confirm" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">确认密码</label>
            <input 
              id="reg-confirm"
              v-model="confirm" 
              type="password" 
              placeholder="再次输入密码…"
              maxlength="50"
              autocomplete="new-password"
              name="confirm_password"
              class="w-full px-4 py-3 bg-primary-900/50 border rounded-xl text-sm text-white placeholder:text-primary-400 focus:bg-primary-900 focus:outline-none transition-all"
              :class="confirm && password !== confirm ? 'border-red-500 bg-red-900/30 focus:border-red-400 focus:ring-red-500/30' : 'border-primary-600 focus:border-primary-400 focus:ring-primary-500/30'"
              :aria-invalid="confirm && password !== confirm"
            />
            <p v-if="confirm && password !== confirm" class="text-xs text-red-400 mt-1 ml-1" role="alert">两次密码不一致</p>
          </div>

          <div v-if="error" class="text-xs text-red-400 text-center mt-3" role="alert" aria-live="polite">{{ error }}</div>

          <button 
            type="submit"
            class="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0"
            :disabled="!canSubmit || loading"
          >
            <span v-if="loading" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '注册中…' : '注册' }}
          </button>
        </form>

        <p class="text-center text-xs text-primary-400 pt-3">
          已有账号？<router-link to="/login" class="text-primary-200 hover:text-white hover:underline transition-colors">去登录</router-link>
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