import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'
import { useUser } from './store/user.js'

import LoginPage from './views/LoginPage.vue'
import RegisterPage from './views/RegisterPage.vue'
import HomePage from './views/HomePage.vue'
import HistoryPage from './views/HistoryPage.vue'
import MarketPage from './views/MarketPage.vue'
import PriceHistoryPage from './views/PriceHistoryPage.vue'
import SearchPage from './views/SearchPage.vue'
import AdminPanel from './views/AdminPanel.vue'
import NotificationPage from './views/NotificationPage.vue'

const routes = [
  { path: '/login',         component: LoginPage },
  { path: '/register',      component: RegisterPage },
  { path: '/home',          component: HomePage,      meta: { auth: true } },
  { path: '/history',       component: HistoryPage,   meta: { auth: true } },
  { path: '/market',        component: MarketPage,    meta: { public: true } },
  { path: '/price-history', component: PriceHistoryPage, meta: { public: true } },
  { path: '/search',        component: SearchPage,     meta: { public: true } },
  { path: '/admin',         component: AdminPanel,    meta: { auth: true, role: 'admin' } },
  { path: '/notifications', component: NotificationPage, meta: { auth: true } },
  { path: '/',              redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

const { isLoggedIn, logout, role } = useUser()

// ✅ 进入系统先清除旧会话，强制到登录页
logout()

router.beforeEach((to, from) => {
  console.log(`[Router] ${from.path} → ${to.path} | auth=${!!to.meta.auth} | loggedIn=${isLoggedIn.value} | role=${role.value}`)
  if (to.meta.auth && !isLoggedIn.value) {
    console.warn(`[Router] 🚫 未登录，拦截导航到 ${to.path}，重定向 /login`)
    return '/login'
  }
  // ✅ 管理员路由额外校验角色，防止非管理员用户直接访问 /admin
  if (to.meta.role === 'admin' && role.value !== 'admin') {
    console.warn(`[Router] 🚫 非管理员用户尝试访问 ${to.path}，重定向 /home`)
    return '/home'
  }
})

const app = createApp(App)
app.use(router)

// ✅ 全局错误捕获 —— 防止未处理异常导致界面"假死"
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', err)
  console.error('  组件:', instance?.$?.type?.name || instance?.$options?.name || '未知')
  console.error('  来源:', info)
}
// ✅ 未捕获 Promise 拒绝
window.addEventListener('unhandledrejection', (event) => {
  console.error('[未捕获 Promise 拒绝]', event.reason)
})

app.mount('#app')
