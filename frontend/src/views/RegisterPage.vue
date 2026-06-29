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
        <form aria-label="注册表单" class="space-y-6" @submit.prevent>
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
              :disabled="loading"
              @input="error = ''"
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
              :disabled="loading"
              @input="error = ''"
            />
          </div>

          <!-- 角色选择 -->
          <div class="space-y-2">
            <label class="block text-sm font-medium text-text-secondary">注册身份</label>
            <div class="flex gap-3">
              <label class="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
                :class="role === 'user' ? 'border-primary-400 bg-primary-50 text-primary-700' : 'border-border bg-white text-text-muted hover:border-primary-200'">
                <input type="radio" v-model="role" value="user" class="sr-only" />
                <span>👤</span> 普通用户
              </label>
              <label class="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
                :class="role === 'admin' ? 'border-warning-400 bg-warning-50 text-warning-700' : 'border-border bg-white text-text-muted hover:border-warning-200'">
                <input type="radio" v-model="role" value="admin" class="sr-only" />
                <span>🔧</span> 管理员
              </label>
            </div>
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
              :disabled="loading"
              @input="error = ''"
            />
            <p v-if="confirm && password !== confirm" class="text-sm text-red-500" role="alert">两次密码不一致</p>
          </div>

          <!-- 成功提示 -->
          <div v-if="successMsg" class="text-sm text-green-600 text-center bg-green-50 border border-green-200 rounded-xl py-3 px-4" role="status" aria-live="polite">
            {{ successMsg }}
          </div>

          <!-- 错误提示 -->
          <div v-if="error" class="text-sm text-red-500 text-center bg-red-50 border border-red-200 rounded-xl py-3 px-4" role="alert" aria-live="polite">
            {{ error }}
          </div>

          <button
            type="button"
            class="btn-primary w-full"
            :disabled="!canSubmit || loading || !!successMsg"
            @click="doRegister"
          >
            <span v-if="loading" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
            {{ loading ? '注册中…' : successMsg ? '注册成功，跳转中…' : '注册' }}
          </button>
        </form>

        <p class="text-center text-sm text-text-muted mt-6">
          已有账号？<router-link to="/login" class="text-primary-600 hover:text-primary-700 hover:underline font-medium transition-colors">去登录</router-link>
        </p>
      </div>

      <div class="mt-8 flex justify-center gap-6 text-xs text-text-muted">
        <span>AI 智能识别</span>
        <span>瑕疵检测</span>
        <span>智能定价</span>
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
