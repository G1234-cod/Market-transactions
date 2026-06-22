<template>
  <div class="max-w-sm mx-auto pt-16">
    <div class="text-center mb-8">
      <span class="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 inline-flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-blue-500/25">二</span>
      <h1 class="mt-4 text-2xl font-bold text-gray-800">创建账号</h1>
      <p class="text-gray-400 text-sm mt-1">加入二手交易社区</p>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
      <label class="block">
        <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">用户名</span>
        <input v-model="username" placeholder="至少 2 个字符"
          maxlength="30"
          class="w-full mt-1 px-3 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all text-sm" />
      </label>

      <label class="block">
        <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">密码</span>
        <input v-model="password" type="password" placeholder="至少 6 位"
          maxlength="50"
          class="w-full mt-1 px-3 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all text-sm"
          @keydown.enter="doRegister" />
      </label>

      <label class="block">
        <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">确认密码</span>
        <input v-model="confirm" type="password" placeholder="再次输入密码"
          maxlength="50"
          class="w-full mt-1 px-3 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all text-sm"
          :class="confirm && password !== confirm ? 'border-red-300 bg-red-50' : ''"
          @keydown.enter="doRegister" />
        <p v-if="confirm && password !== confirm" class="text-xs text-red-400 mt-1 ml-1">两次密码不一致</p>
      </label>

      <button class="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 shadow-lg shadow-blue-500/25 transition-all disabled:opacity-50"
        :disabled="!canSubmit || loading" @click="doRegister">
        <span v-if="loading" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
        {{ loading ? '注册中...' : '注册' }}
      </button>

      <p v-if="error" class="text-xs text-red-400 text-center">{{ error }}</p>

      <p class="text-center text-xs text-gray-400">
        已有账号？<router-link to="/login" class="text-blue-600 hover:underline">去登录</router-link>
      </p>
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
