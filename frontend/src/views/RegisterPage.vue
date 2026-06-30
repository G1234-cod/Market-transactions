<template>
  <div class="min-h-screen flex bg-white">
    <!-- 左侧品牌区 - 浅色调 -->
    <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center"
      style="background: linear-gradient(160deg, #F0FDF4 0%, #ECFEFF 30%, #F0F9FF 60%, #EEF2FF 100%)">
      <!-- 装饰元素 -->
      <div class="absolute -top-20 -left-20 w-96 h-96 rounded-full" style="background: radial-gradient(circle, rgba(16,185,129,0.10) 0%, transparent 70%)" />
      <div class="absolute -bottom-32 -right-20 w-[500px] h-[500px] rounded-full" style="background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)" />
      <div class="absolute top-1/3 left-1/3 w-64 h-64 rounded-full" style="background: radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)" />
      <!-- 几何装饰 -->
      <div class="absolute top-24 right-20 w-28 h-28 rounded-full border border-emerald-200/40" />
      <div class="absolute bottom-28 left-16 w-16 h-16 rounded-full border border-primary-200/40" />

      <div class="relative z-10 max-w-lg px-12 py-16">
        <div class="relative inline-block mb-8">
          <div class="absolute -inset-4 rounded-3xl blur-2xl" style="background: rgba(16,185,129,0.12)"></div>
          <div class="relative w-20 h-20 rounded-2xl inline-flex items-center justify-center text-white text-4xl font-bold shadow-xl shadow-emerald-400/30"
            style="background: linear-gradient(135deg, #34D399, #10B981, #6366F1)">
            <span>二</span>
          </div>
        </div>

        <h1 class="text-3xl font-extrabold tracking-tight mb-3" style="color: #064E3B">加入二手交易社区</h1>
        <p class="text-base leading-relaxed mb-10" style="color: #059669">
          注册账号，体验 AI 驱动的智能二手商品发布
        </p>

        <div class="space-y-3">
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(16,185,129,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #ECFDF5, #D1FAE5)">
              <span>🤖</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #064E3B">AI 一键识别</div>
              <div class="text-xs" style="color: #34D399">上传照片自动获取商品信息</div>
            </div>
          </div>
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(99,102,241,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #EEF2FF, #E0E7FF)">
              <span>📝</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #064E3B">自动生成文案</div>
              <div class="text-xs" style="color: #34D399">DeepSeek 专业带货文案</div>
            </div>
          </div>
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(139,92,246,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #F5F3FF, #EDE9FE)">
              <span>🏪</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #064E3B">一键发布到商城</div>
              <div class="text-xs" style="color: #34D399">商品直达潜在买家</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧注册表单 -->
    <div class="flex-1 flex items-center justify-center px-6 sm:px-12 py-8">
      <div class="w-full max-w-md">
        <div class="text-center mb-6 lg:hidden">
          <div class="relative inline-block">
            <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-2xl"></div>
            <div class="relative w-16 h-16 rounded-2xl gradient-primary inline-flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-primary-500/40">
              <span>二</span>
            </div>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-text-primary mb-1">创建账号</h2>
        <p class="text-text-muted text-sm mb-8">加入智能二手交易社区</p>

        <form aria-label="注册表单" class="space-y-5" @submit.prevent>
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

          <div class="bg-surface-secondary rounded-xl p-3 text-xs text-text-muted text-center">
            管理员账号只能由管理员在后台用户管理中创建
          </div>

          <div v-if="successMsg" class="text-sm text-green-600 text-center bg-green-50 border border-green-200 rounded-xl py-3 px-4" role="status" aria-live="polite">
            {{ successMsg }}
          </div>

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
    const data = await apiRegister(username.value.trim(), password.value)
    console.log('[Register] 响应:', data)
    // 注册成功
    if (data.success || data.user_id) {
      successMsg.value = '注册成功！即将跳转至登录页面…'
      // ✅ 清除所有旧的登录状态，防止残留 admin session 混入新注册用户
      localStorage.removeItem('token')
      localStorage.removeItem('user_info')
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
