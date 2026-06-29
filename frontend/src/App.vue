<template>
  <div class="min-h-screen flex flex-col bg-space">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 px-4 py-2 bg-primary-600 text-white rounded-lg z-50">
      跳转到主内容
    </a>

    <header v-if="isLoggedIn" class="sticky top-0 z-50 bg-space-card/80 backdrop-blur-xl border-b border-border/50 shadow-lg shadow-black/20" role="navigation">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <router-link to="/home" class="flex items-center gap-3 group" aria-label="返回首页">
          <div class="relative">
            <div class="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-primary-500/30 group-hover:shadow-xl group-hover:shadow-primary-500/40 transition-all duration-300">
              <span>二</span>
            </div>
            <div class="absolute -inset-1 gradient-primary rounded-xl blur-lg opacity-0 group-hover:opacity-30 transition-opacity duration-300 -z-10"></div>
          </div>
          <span class="text-lg font-bold gradient-text">智能二手发布助手</span>
        </router-link>
        
        <nav class="flex items-center gap-1" aria-label="主导航">
          <template v-if="isLoggedIn">
            <router-link to="/home" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-500/30 focus:outline-none relative overflow-hidden"
              :class="$route.path === '/home' ? 'bg-primary-500/20 text-primary-400' : 'text-text-secondary hover:text-primary-400 hover:bg-primary-500/10'">
              <span>发布</span>
              <div v-if="$route.path === '/home'" class="absolute inset-0 bg-gradient-to-r from-primary-500/0 via-primary-500/10 to-primary-500/0 animate-shimmer"></div>
            </router-link>
            <router-link to="/history" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-500/30 focus:outline-none relative overflow-hidden"
              :class="$route.path === '/history' ? 'bg-primary-500/20 text-primary-400' : 'text-text-secondary hover:text-primary-400 hover:bg-primary-500/10'">
              <span>历史</span>
              <div v-if="$route.path === '/history'" class="absolute inset-0 bg-gradient-to-r from-primary-500/0 via-primary-500/10 to-primary-500/0 animate-shimmer"></div>
            </router-link>
            <router-link to="/notifications" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-500/30 focus:outline-none relative overflow-hidden"
              :class="$route.path === '/notifications' ? 'bg-primary-500/20 text-primary-400' : 'text-text-secondary hover:text-primary-400 hover:bg-primary-500/10'">
              🔔
              <span v-if="unreadCount > 0" class="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-space font-bold text-xs rounded-full flex items-center justify-center shadow-lg shadow-amber-500/30 animate-pulse-slow">{{ unreadCount }}</span>
            </router-link>
            <router-link v-if="isAdmin" to="/admin" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-amber-500/30 focus:outline-none relative overflow-hidden"
              :class="$route.path === '/admin' ? 'bg-amber-500/20 text-amber-400' : 'text-text-secondary hover:text-amber-400 hover:bg-amber-500/10'">
              <span>管理</span>
            </router-link>
          </template>
          <router-link to="/market" class="px-4 py-2 rounded-lg text-sm font-medium transition-all focus:ring-2 focus:ring-primary-500/30 focus:outline-none relative overflow-hidden"
            :class="$route.path === '/market' ? 'bg-primary-500/20 text-primary-400' : 'text-text-secondary hover:text-primary-400 hover:bg-primary-500/10'">
            <span>商城</span>
            <div v-if="$route.path === '/market'" class="absolute inset-0 bg-gradient-to-r from-primary-500/0 via-primary-500/10 to-primary-500/0 animate-shimmer"></div>
          </router-link>

          <div v-if="user" class="ml-4 flex items-center gap-3">
            <div class="hidden sm:block px-3 py-1.5 rounded-full bg-primary-500/10 text-primary-400 text-xs font-medium border border-primary-500/20">
              {{ user.username }}
            </div>
            <button 
              class="px-3 py-1.5 rounded-lg text-xs font-medium text-danger-400 border border-danger-500/30 hover:bg-danger-500/10 hover:border-danger-500/50 transition-all focus:ring-2 focus:ring-danger-500/30 focus:outline-none ripple-container" 
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

    <footer class="text-center py-6 text-xs text-text-muted bg-space-card/50 border-t border-border/30" role="contentinfo">
      <p class="flex items-center justify-center gap-2">
        <span>智能二手商品发布助手</span>
        <span class="text-border">·</span>
        <span>Qwen-VL-Max + DeepSeek-V4-Pro</span>
        <span class="text-border">·</span>
        <span>FastAPI + Vue 3</span>
      </p>
    </footer>

    <TransitionGroup name="toast" tag="div" class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80" aria-live="polite">
      <div v-for="msg in toasts" :key="msg.id"
        class="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm backdrop-blur-xl animate-slide-up border"
        :class="toastClass(msg.type)">
        <span class="text-lg">{{ toastIcon(msg.type) }}</span>
        <span class="flex-1">{{ msg.text }}</span>
        <button class="opacity-50 hover:opacity-100 focus:ring-2 focus:ring-white/30 focus:outline-none" @click="removeToast(msg.id)" aria-label="关闭提示">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, provide, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUser } from './store/user.js'
import { getNotifications } from './api/index.js'

const route = useRoute()
const router = useRouter()
const { state: userState, isLoggedIn, logout } = useUser()

const user = computed(() => userState.user)
const isAdmin = computed(() => user.value?.role === 'admin')
const unreadCount = ref(0)

async function loadUnreadCount() {
  if (!isLoggedIn.value) return
  try {
    const result = await getNotifications()
    unreadCount.value = (result.notifications || []).filter(n => !n.is_read).length
  } catch (e) {
    if (e?.response?.status !== 401) {
      console.error('加载未读通知失败:', e)
    }
  }
}

function doLogout() {
  logout()
  router.push('/login')
}

import { watch } from 'vue'
watch(() => route.path, () => {
  if (isLoggedIn.value) loadUnreadCount()
})

onMounted(() => {
  loadUnreadCount()
})

const toasts = ref([])
let _id = 0
function showToast(text, type = 'info') {
  const id = ++_id
  toasts.value.push({ id, text, type })
  setTimeout(() => removeToast(id), 3500)
}
function removeToast(id) { toasts.value = toasts.value.filter(t => t.id !== id) }
function toastClass(t) {
  return t === 'success' ? 'bg-success-500/90 border-success-500/50 text-white shadow-lg shadow-success-500/30'
    : t === 'error' ? 'bg-danger-500/90 border-danger-500/50 text-white shadow-lg shadow-danger-500/30'
    : t === 'warning' ? 'bg-amber-500/90 border-amber-500/50 text-space shadow-lg shadow-amber-500/30'
    : 'bg-primary-500/90 border-primary-500/50 text-white shadow-lg shadow-primary-500/30'
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
