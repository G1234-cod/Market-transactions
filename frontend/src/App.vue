<template>
  <div class="min-h-screen flex flex-col">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 px-4 py-2 bg-primary-600 text-white rounded-lg z-50">
      跳转到主内容
    </a>

    <header v-if="isLoggedIn || routePath === '/market'" class="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-border-light shadow-sm" role="navigation">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-3 group" aria-label="返回首页">
          <div class="relative">
            <div class="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-primary-500/30 group-hover:shadow-xl group-hover:shadow-primary-500/40 transition-all">
              <span>二</span>
            </div>
          </div>
          <span class="text-lg font-bold gradient-text">智能二手发布助手</span>
        </router-link>
        
        <nav class="flex items-center gap-1" aria-label="主导航">
          <template v-if="isLoggedIn">
            <router-link to="/" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-300 focus:outline-none"
              :class="$route.path === '/' ? 'bg-primary-100 text-primary-700' : 'text-text-secondary hover:text-primary-600 hover:bg-primary-50'">发布</router-link>
            <router-link to="/history" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-300 focus:outline-none"
              :class="$route.path === '/history' ? 'bg-primary-100 text-primary-700' : 'text-text-secondary hover:text-primary-600 hover:bg-primary-50'">历史</router-link>
          </template>
          <router-link to="/market" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-300 focus:outline-none"
            :class="$route.path === '/market' ? 'bg-primary-100 text-primary-700' : 'text-text-secondary hover:text-primary-600 hover:bg-primary-50'">商城</router-link>
          
          <div v-if="user" class="ml-4 flex items-center gap-3">
            <div class="hidden sm:block px-3 py-1.5 rounded-full bg-primary-50 text-primary-700 text-xs font-medium">
              {{ user.username }}
            </div>
            <button 
              class="px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50 hover:border-red-300 transition-all focus:ring-2 focus:ring-red-300 focus:outline-none" 
              @click="doLogout" 
              aria-label="退出登录"
            >
              退出
            </button>
          </div>
        </nav>
      </div>
    </header>

    <main id="main-content" class="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="text-center py-6 text-xs text-text-muted bg-white/50" role="contentinfo">
      <p>智能二手商品发布助手 · Qwen-VL-Max + DeepSeek-V4-Pro · FastAPI + Vue 3</p>
    </footer>

    <TransitionGroup name="toast" tag="div" class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80" aria-live="polite">
      <div v-for="msg in toasts" :key="msg.id"
        class="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm backdrop-blur-md animate-slide-up border"
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

const toasts = ref([])
let _id = 0
function showToast(text, type = 'info') {
  const id = ++_id
  toasts.value.push({ id, text, type })
  setTimeout(() => removeToast(id), 3500)
}
function removeToast(id) { toasts.value = toasts.value.filter(t => t.id !== id) }
function toastClass(t) {
  return t === 'success' ? 'bg-accent-500/95 border-accent-400 text-white shadow-lg shadow-accent-500/30'
    : t === 'error' ? 'bg-red-500/95 border-red-400 text-white shadow-lg shadow-red-500/30'
    : t === 'warning' ? 'bg-amber-500/95 border-amber-400 text-white shadow-lg shadow-amber-500/30'
    : 'bg-primary-500/95 border-primary-400 text-white shadow-lg shadow-primary-500/30'
}
function toastIcon(t) { return t === 'success' ? '✓' : t === 'error' ? '✗' : t === 'warning' ? '⚠' : 'ℹ' }
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