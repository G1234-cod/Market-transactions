<template>
  <div class="min-h-screen flex items-center justify-center px-4 py-8 relative overflow-hidden">
    <div class="orb orb-accent w-[500px] h-[500px] -top-[100px] -right-[100px] animate-float-slow"></div>
    <div class="orb orb-primary w-[400px] h-[400px] -bottom-[50px] -left-[50px] animate-float-medium"></div>
    <div class="orb orb-amber w-[300px] h-[300px] top-1/3 right-1/4 animate-float-fast opacity-20"></div>

    <div class="w-full max-w-lg relative z-10">
      <div class="text-center mb-10 animate-fade-in-up-1">
        <div class="relative inline-block">
          <div class="absolute -inset-6 bg-gradient-to-r from-accent-500/30 to-primary-500/30 rounded-3xl blur-3xl"></div>
          <div class="relative w-24 h-24 rounded-2xl gradient-accent inline-flex items-center justify-center text-white text-5xl font-bold shadow-2xl shadow-accent-500/40 animate-scale-in">
            <span>二</span>
          </div>
        </div>
        <h1 class="mt-10 text-3xl sm:text-4xl font-extrabold gradient-text animate-fade-in-up-2">创建账号</h1>
        <p class="text-text-secondary text-base mt-3 animate-fade-in-up-3">加入智能二手交易社区</p>
      </div>

      <div class="glass-card p-10 card-glow-hover animate-fade-in-up-4">
        <form aria-label="注册表单" class="space-y-7" @submit.prevent>
          <div class="space-y-3">
            <label for="reg-username" class="block text-sm font-semibold text-text-secondary">用户名</label>
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
              :disabled="loading"
              @input="error = ''"
            />
          </div>

          <div class="space-y-3">
            <label for="reg-password" class="block text-sm font-semibold text-text-secondary">密码</label>
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
              :disabled="loading"
              @input="error = ''"
            />
          </div>

          <!-- 角色选择 -->
          <div class="space-y-3">
            <label class="block text-sm font-semibold text-text-secondary">注册身份</label>
            <div class="flex gap-3">
              <label class="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl border-2 cursor-pointer transition-all"
                :class="role === 'user' ? 'border-primary-500/50 bg-primary-500/15 text-primary-400 shadow-lg shadow-primary-500/10' : 'border-border bg-space-lighter/30 text-text-muted hover:border-primary-500/30'">
                <input type="radio" v-model="role" value="user" class="sr-only" />
                <span class="text-lg">👤</span> 普通用户
              </label>
              <label class="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl border-2 cursor-pointer transition-all"
                :class="role === 'admin' ? 'border-amber-500/50 bg-amber-500/15 text-amber-400 shadow-lg shadow-amber-500/10' : 'border-border bg-space-lighter/30 text-text-muted hover:border-amber-500/30'">
                <input type="radio" v-model="role" value="admin" class="sr-only" />
                <span class="text-lg">🔧</span> 管理员
              </label>
            </div>
          </div>

          <div class="space-y-3">
            <label for="reg-confirm" class="block text-sm font-semibold text-text-secondary">确认密码</label>
            <input
              id="reg-confirm"
              v-model="confirm"
              type="password"
              placeholder="再次输入密码…"
              maxlength="50"
              autocomplete="new-password"
              name="confirm_password"
              class="input-field"
              :class="confirm && password !== confirm ? 'bg-danger-500/10 border-danger-500/50 focus:border-danger-500/70 focus:ring-danger-500/20' : ''"
              :disabled="loading"
              @input="error = ''"
            />
            <p v-if="confirm && password !== confirm" class="text-sm text-danger-400" role="alert">两次密码不一致</p>
          </div>

          <!-- 成功提示 -->
          <div v-if="successMsg" class="text-sm text-success-400 text-center bg-success-500/15 border border-success-500/30 rounded-xl py-4 px-4" role="status" aria-live="polite">
            {{ successMsg }}
          </div>

          <!-- 错误提示 -->
          <div v-if="error" class="text-sm text-danger-400 text-center bg-danger-500/15 border border-danger-500/30 rounded-xl py-4 px-4" role="alert" aria-live="polite">
            {{ error }}
          </div>

          <button
            type="button"
            class="btn-primary w-full text-lg py-4 ripple-container"
            :disabled="!canSubmit || loading || !!successMsg"
            @click="doRegister"
          >
            <span v-if="loading" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '注册中…' : successMsg ? '注册成功，跳转中…' : '注册' }}
          </button>
        </form>

        <p class="text-center text-base text-text-secondary mt-8 animate-fade-in-up-5">
          已有账号？<router-link to="/login" class="text-primary-400 hover:text-primary-300 font-semibold transition-colors">去登录</router-link>
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
import { register as apiRegister } from '../api/index.js'

const router = useRouter()

const username = ref('')
const password = ref('')
const confirm = ref('')
const role = ref('user')
const loading = ref(false)
const error = ref('')
const successMsg = ref('')

const canSubmit = computed(() =>
  username.value.trim().length >= 2 &&
  password.value.length >= 6 &&
  password.value === confirm.value &&
  !loading.value
)

async function doRegister() {
  console.log('[Register] 按钮点击，canSubmit =', canSubmit.value, { username: username.value, passwordLen: password.value.length, confirmMatch: password.value === confirm.value })
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    console.log('[Register] 开始请求 /api/v1/register ...')
    const data = await apiRegister(username.value.trim(), password.value, role.value)
    console.log('[Register] 响应:', data)
    // 注册成功
    if (data.success || data.user_id) {
      successMsg.value = '注册成功！即将跳转至登录页面…'
      // 1.5 秒后跳转到登录页
      setTimeout(() => {
        router.push('/login')
      }, 1500)
    } else {
      error.value = data.detail || '注册失败，请重试'
    }
  } catch (e) {
    console.error('[Register] 请求失败:', e)
    // 提取后端返回的错误信息
    const detail = e?.response?.data?.detail
    if (typeof detail === 'string') {
      error.value = detail
    } else if (typeof detail === 'object' && detail?.error) {
      error.value = detail.error
    } else {
      error.value = '注册失败，请检查网络后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
