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

const routes = [
  { path: '/login',         component: LoginPage },
  { path: '/register',      component: RegisterPage },
  { path: '/home',          component: HomePage,      meta: { auth: true } },
  { path: '/history',       component: HistoryPage,   meta: { auth: true } },
  { path: '/market',        component: MarketPage,    meta: { public: true } },
  { path: '/',              redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

const { isLoggedIn } = useUser()

router.beforeEach((to) => {
  if (to.meta.auth && !isLoggedIn.value) return '/login'
})

const app = createApp(App)
app.use(router)
app.mount('#app')
