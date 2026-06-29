<template>
  <div class="min-h-screen flex items-center justify-center px-4 py-8 relative overflow-hidden">
    <div class="orb orb-primary w-[500px] h-[500px] -top-[100px] -left-[100px] animate-float-slow"></div>
    <div class="orb orb-accent w-[400px] h-[400px] -bottom-[50px] -right-[50px] animate-float-medium"></div>
    <div class="orb orb-amber w-[300px] h-[300px] top-1/2 left-1/4 -translate-y-1/2 animate-float-fast opacity-20"></div>

    <div class="w-full max-w-lg relative z-10">
      <div class="text-center mb-10 animate-fade-in-up-1">
        <div class="relative inline-block">
          <div class="absolute -inset-6 bg-gradient-to-r from-primary-500/30 to-accent-500/30 rounded-3xl blur-3xl"></div>
          <div class="relative w-24 h-24 rounded-2xl gradient-primary inline-flex items-center justify-center text-white text-5xl font-bold shadow-2xl shadow-primary-500/40 animate-scale-in">
            <span>二</span>
          </div>
        </div>
        <h1 class="mt-10 text-3xl sm:text-4xl font-extrabold gradient-text animate-fade-in-up-2">智能二手商品发布助手</h1>
        <p class="text-text-secondary text-base mt-3 animate-fade-in-up-3">登录您的账号，开始发布二手商品</p>
      </div>

      <div class="glass-card p-10 card-glow-hover animate-fade-in-up-4">
        <form @submit.prevent="doLogin" aria-label="登录表单" class="space-y-7">
          <div class="space-y-3">
            <label for="username" class="block text-sm font-semibold text-text-secondary">用户名</label>
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

          <div class="space-y-3">
            <label for="password" class="block text-sm font-semibold text-text-secondary">密码</label>
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

          <div v-if="error" class="text-sm text-danger-400 text-center py-2 px-4 rounded-xl bg-danger-500/10 border border-danger-500/20" role="alert" aria-live="polite">
            {{ error }}
          </div>

          <button 
            type="submit"
            class="btn-primary w-full text-lg py-4 ripple-container"
            :disabled="!canSubmit || loading"
          >
            <span v-if="loading" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="text-center text-base text-text-secondary mt-8 animate-fade-in-up-5">
          还没有账号？<router-link to="/register" class="text-primary-400 hover:text-primary-300 font-semibold transition-colors">注册新账号</router-link>
        </p>
      </div>

      <div class="mt-10 flex justify-center gap-8 text-sm text-text-muted animate-fade-in-up-6">
        <div class="flex items-center gap-2 px-4 py-2 rounded-xl bg-space-card/50 border border-border/30">
          <span class="text-lg">📱</span>
          <span>AI 智能识别</span>
        </div>
        <div class="flex items-center gap-2 px-4 py-2 rounded-xl bg-space-card/50 border border-border/30">
          <span class="text-lg">🔍</span>
          <span>瑕疵检测</span>
        </div>
        <div class="flex items-center gap-2 px-4 py-2 rounded-xl bg-space-card/50 border border-border/30">
          <span class="text-lg">💰</span>
          <span>智能定价</span>
        </div>
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