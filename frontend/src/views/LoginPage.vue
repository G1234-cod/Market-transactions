<template>
  <div class="min-h-screen flex bg-white">
    <!-- 左侧品牌区 - 浅色调 -->
    <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center"
      style="background: linear-gradient(160deg, #EEF2FF 0%, #E0E7FF 30%, #EDE9FE 60%, #F5F3FF 100%)">
      <!-- 装饰元素 -->
      <div class="absolute -top-20 -right-20 w-96 h-96 rounded-full" style="background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)" />
      <div class="absolute -bottom-32 -left-20 w-[500px] h-[500px] rounded-full" style="background: radial-gradient(circle, rgba(139,92,246,0.10) 0%, transparent 70%)" />
      <div class="absolute top-1/2 right-1/4 w-64 h-64 rounded-full" style="background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)" />
      <!-- 几何装饰线 -->
      <div class="absolute top-20 right-16 w-32 h-32 rounded-full border border-primary-200/40" />
      <div class="absolute bottom-32 left-20 w-20 h-20 rounded-full border border-accent-200/40" />

      <div class="relative z-10 max-w-lg px-12 py-16">
        <!-- Logo -->
        <div class="relative inline-block mb-8">
          <div class="absolute -inset-4 rounded-3xl blur-2xl" style="background: rgba(99,102,241,0.15)"></div>
          <div class="relative w-20 h-20 rounded-2xl inline-flex items-center justify-center text-white text-4xl font-bold shadow-xl shadow-primary-400/30"
            style="background: linear-gradient(135deg, #818CF8, #6366F1, #8B5CF6)">
            <span>二</span>
          </div>
        </div>

        <h1 class="text-3xl font-extrabold tracking-tight mb-3" style="color: #312E81">智能二手发布助手</h1>
        <p class="text-base leading-relaxed mb-10" style="color: #6366F1">
          AI 驱动的商品识别、智能定价、文案生成，让二手交易更简单
        </p>

        <!-- 功能卡片 -->
        <div class="space-y-3">
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(99,102,241,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #EEF2FF, #E0E7FF)">
              <span>📱</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #312E81">AI 智能识别</div>
              <div class="text-xs" style="color: #818CF8">拍照即识别品类、品牌、型号</div>
            </div>
          </div>
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(139,92,246,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #EDE9FE, #DDD6FE)">
              <span>🔍</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #312E81">瑕疵检测</div>
              <div class="text-xs" style="color: #818CF8">自动标注损伤区域与成色分级</div>
            </div>
          </div>
          <div class="flex items-center gap-4 rounded-xl px-5 py-4 transition-all hover:scale-[1.02]"
            style="background: rgba(255,255,255,0.75); box-shadow: 0 2px 12px rgba(99,102,241,0.08); backdrop-filter: blur(8px)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #F5F3FF, #EDE9FE)">
              <span>💰</span>
            </div>
            <div>
              <div class="font-semibold text-sm" style="color: #312E81">智能定价</div>
              <div class="text-xs" style="color: #818CF8">市场行情参考 + AI 建议售价</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="flex-1 flex items-center justify-center px-6 sm:px-12 py-8">
      <div class="w-full max-w-md">
        <!-- 移动端显示logo -->
        <div class="text-center mb-6 lg:hidden">
          <div class="relative inline-block">
            <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-2xl"></div>
            <div class="relative w-16 h-16 rounded-2xl gradient-primary inline-flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-primary-500/40">
              <span>二</span>
            </div>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-text-primary mb-1">欢迎回来</h2>
        <p class="text-text-muted text-sm mb-8">登录您的账号，开始发布二手商品</p>

        <form @submit.prevent="doLogin" aria-label="登录表单" class="space-y-5">
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

          <div v-if="error" class="text-sm text-red-500 text-center bg-red-50 border border-red-200 rounded-xl py-3 px-4" role="alert" aria-live="polite">
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