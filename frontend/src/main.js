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
  { path: '/login',         component: LoginPage,    meta: { guest: true } },
  { path: '/register',      component: RegisterPage,  meta: { guest: true } },
  { path: '/',              component: HomePage,      meta: { auth: true } },
  { path: '/history',       component: HistoryPage,   meta: { auth: true } },
  { path: '/market',        component: MarketPage,    meta: { public: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

const { restoreUser, isLoggedIn } = useUser()
restoreUser()

router.beforeEach((to) => {
  if (to.meta.auth && !isLoggedIn.value) return '/login'
  if (to.meta.guest && isLoggedIn.value) return '/'
})

const app = createApp(App)
app.use(router)
app.mount('#app')
