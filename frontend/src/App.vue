<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-white">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 px-4 py-2 bg-primary-600 text-white rounded-lg z-50">
      跳转到主内容
    </a>

    <header v-if="isLoggedIn || routePath === '/market'" class="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-gray-200/60 shadow-sm" role="navigation">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-2.5 group" aria-label="返回首页">
          <span class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-primary-500/25">二</span>
          <span class="text-lg font-bold bg-gradient-to-r from-primary-600 via-accent-500 to-primary-800 bg-clip-text text-transparent">智能二手商品发布助手</span>
        </router-link>
        <nav class="flex items-center gap-1" aria-label="主导航">
          <template v-if="isLoggedIn">
            <router-link to="/" class="px-4 py-1.5 rounded-full text-sm font-medium transition-all focus:ring-2 focus:ring-primary-400 focus:outline-none"
              :class="$route.path === '/' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:text-primary-600'">发布</router-link>
            <router-link to="/history" class="px-4 py-1.5 rounded-full text-sm font-medium transition-all focus:ring-2 focus:ring-primary-400 focus:outline-none"
              :class="$route.path === '/history' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:text-primary-600'">历史</router-link>
          </template>
          <router-link to="/market" class="px-4 py-1.5 rounded-full text-sm font-medium transition-all focus:ring-2 focus:ring-primary-400 focus:outline-none"
            :class="$route.path === '/market' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:text-primary-600'">商城</router-link>
          <span v-if="user" class="ml-3 text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">{{ user.username }}</span>
          <button v-if="isLoggedIn" class="ml-1 px-3 py-1 text-xs text-gray-400 hover:text-red-500 transition-colors focus:ring-2 focus:ring-red-400 focus:outline-none rounded-full" @click="doLogout" aria-label="退出登录">退出</button>
        </nav>
      </div>
    </header>

    <main id="main-content" class="max-w-5xl mx-auto px-4 py-8">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="text-center py-6 text-xs text-gray-400" role="contentinfo">
      智能二手商品发布助手 · Qwen-VL-Max + DeepSeek-V4-Pro · FastAPI + Vue 3
    </footer>

    <TransitionGroup name="toast" tag="div" class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80" aria-live="polite">
      <div v-for="msg in toasts" :key="msg.id"
        class="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm backdrop-blur-md animate-slide-up"
        :class="toastClass(msg.type)">
        <span class="text-lg">{{ toastIcon(msg.type) }}</span>
        <span class="flex-1">{{ msg.text }}</span>
        <button class="opacity-50 hover:opacity-100 focus:ring-2 focus:ring-gray-400 focus:outline-none" @click="removeToast(msg.id)" aria-label="关闭提示">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, provide, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUser } from './store/user.js'

const route = useRoute()
const router = useRouter()
const { state: userState, isLoggedIn, logout } = useUser()

const routePath = computed(() => route.path)
const user = computed(() => userState.user)

function doLogout() {
  logout()
  router.push('/login')
}

// ---- Toast ----
const toasts = ref([])
let _id = 0
function showToast(text, type = 'info') {
  const id = ++_id
  toasts.value.push({ id, text, type })
  setTimeout(() => removeToast(id), 3500)
}
function removeToast(id) { toasts.value = toasts.value.filter(t => t.id !== id) }
function toastClass(t) {
  return t === 'success' ? 'bg-emerald-50/95 border border-emerald-200 text-emerald-800'
    : t === 'error' ? 'bg-red-50/95 border border-red-200 text-red-800'
    : t === 'warning' ? 'bg-amber-50/95 border border-amber-200 text-amber-800'
    : 'bg-white/95 border border-gray-200 text-gray-700'
}
function toastIcon(t) { return t === 'success' ? '✓' : t === 'error' ? '✗' : t === 'warning' ? '!' : 'i' }
provide('toast', showToast)
</script>

<style scoped>
@keyframes slide-up {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.animate-slide-up { animation: slide-up 0.3s ease; }
.toast-enter-active { animation: slide-up 0.3s ease; }
.toast-leave-active  { transition: all 0.2s ease; }
.toast-leave-to { opacity: 0; transform: translateX(40px); }
</style>
