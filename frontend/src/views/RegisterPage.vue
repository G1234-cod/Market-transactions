<template>
  <div class="min-h-screen flex items-center justify-center px-4 py-8">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-2xl"></div>
          <div class="relative w-20 h-20 rounded-2xl gradient-primary inline-flex items-center justify-center text-white text-4xl font-bold shadow-xl shadow-primary-500/40">
            <span>二</span>
          </div>
        </div>
        <h1 class="mt-8 text-2xl font-bold gradient-text">创建账号</h1>
        <p class="text-text-muted text-sm mt-2">加入智能二手交易社区</p>
      </div>

      <div class="glass-card p-8">
        <form @submit.prevent="doRegister" aria-label="注册表单" class="space-y-6">
          <div class="space-y-2">
            <label for="reg-username" class="block text-sm font-medium text-text-secondary">用户名</label>
            <input 
              id="reg-username"
              v-model="username" 
              placeholder="至少 2 个字符…"
              maxlength="30"
              autocomplete="username"
              name="username"
              spellcheck="false"
              class="input-field"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-2">
            <label for="reg-password" class="block text-sm font-medium text-text-secondary">密码</label>
            <input 
              id="reg-password"
              v-model="password" 
              type="password" 
              placeholder="至少 6 位…"
              maxlength="50"
              autocomplete="new-password"
              name="password"
              class="input-field"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
          </div>

          <div class="space-y-2">
            <label for="reg-confirm" class="block text-sm font-medium text-text-secondary">确认密码</label>
            <input 
              id="reg-confirm"
              v-model="confirm" 
              type="password" 
              placeholder="再次输入密码…"
              maxlength="50"
              autocomplete="new-password"
              name="confirm_password"
              class="input-field"
              :class="confirm && password !== confirm ? 'bg-red-50 border-red-300 focus:border-red-400 focus:ring-red-100' : ''"
              :aria-invalid="confirm && password !== confirm"
            />
            <p v-if="confirm && password !== confirm" class="text-sm text-red-500" role="alert">两次密码不一致</p>
          </div>

          <div v-if="error" class="text-sm text-red-500 text-center" role="alert" aria-live="polite">
            {{ error }}
          </div>

          <button 
            type="submit"
            class="btn-primary w-full"
            :disabled="!canSubmit || loading"
          >
            <span v-if="loading" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '注册中…' : '注册' }}
          </button>
        </form>

        <p class="text-center text-sm text-text-muted mt-6">
          已有账号？<router-link to="/login" class="text-primary-600 hover:text-primary-700 hover:underline font-medium transition-colors">去登录</router-link>
        </p>
      </div>

      <div class="mt-8 flex justify-center gap-6 text-xs text-text-muted">
        <span>📱 AI 智能识别</span>
        <span>🔍 瑕疵检测</span>
        <span>💰 智能定价</span>
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