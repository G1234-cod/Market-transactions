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
        <h1 class="mt-8 text-2xl font-bold gradient-text">智能二手商品发布助手</h1>
        <p class="text-text-muted text-sm mt-2">登录您的账号，开始发布二手商品</p>
      </div>

      <div class="glass-card p-8">
        <form @submit.prevent="doLogin" aria-label="登录表单" class="space-y-6">
          <div class="space-y-2">
            <label for="username" class="block text-sm font-medium text-text-secondary">用户名</label>
            <input 
              id="username"
              v-model="username" 
              placeholder="请输入用户名…"
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
            <label for="password" class="block text-sm font-medium text-text-secondary">密码</label>
            <input 
              id="password"
              v-model="password" 
              type="password" 
              placeholder="请输入密码…"
              maxlength="50"
              autocomplete="current-password"
              name="password"
              class="input-field"
              aria-required="true"
              :aria-invalid="error !== ''"
            />
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
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="text-center text-sm text-text-muted mt-6">
          还没有账号？<router-link to="/register" class="text-primary-600 hover:text-primary-700 hover:underline font-medium transition-colors">注册新账号</router-link>
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
    // ✅ 根据角色跳转：管理员 → 管理页，普通用户 → 发布页
    if (user.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/home')
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>