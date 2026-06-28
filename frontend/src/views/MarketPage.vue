<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold gradient-text">二手商城</h1>
        </div>
        <p class="text-text-muted text-sm mt-2">浏览所有用户发布的商品，找到心仪好物</p>
      </div>
      
      <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <div class="relative flex-1 sm:flex-none">
          <input 
            v-model="keyword" 
            placeholder="搜索商品…"
            class="w-full sm:w-64 px-4 py-3 pl-10 border border-border rounded-xl text-sm bg-white placeholder:text-text-muted focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
            autocomplete="off"
            aria-label="搜索商品"
          />
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">🔍</span>
        </div>
        <select 
          v-model="categoryFilter" 
          class="px-4 py-3 text-sm border border-border rounded-xl bg-white text-text-primary outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all cursor-pointer"
          aria-label="分类筛选"
        >
          <option value="" class="bg-white">全部分类</option>
          <option value="手机" class="bg-white">手机</option>
          <option value="笔记本" class="bg-white">笔记本</option>
          <option value="平板" class="bg-white">平板</option>
          <option value="外设" class="bg-white">外设</option>
          <option value="耳机" class="bg-white">耳机</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="stat-card">
        <p class="stat-value text-text-primary">{{ items.length }}</p>
        <p class="stat-label">全部商品</p>
      </div>
      <div class="stat-card">
        <p class="stat-value text-accent-600">{{ categories.length }}</p>
        <p class="stat-label">商品分类</p>
      </div>
      <div class="stat-card">
        <p class="stat-value text-primary-600">{{ Math.floor(items.reduce((sum, i) => sum + (i.suggested_price || 0), 0) / Math.max(1, items.length)) }}</p>
        <p class="stat-label">均价(元)</p>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="glass-card p-4 animate-pulse">
        <div class="w-full h-48 bg-gradient-to-br from-surface-secondary to-surface-tertiary rounded-xl mb-4" />
        <div class="h-5 bg-surface-tertiary rounded-lg w-3/4 mb-2" />
        <div class="h-4 bg-surface-tertiary rounded w-full mb-2" />
        <div class="h-4 bg-surface-tertiary rounded w-1/2" />
      </div>
    </div>

    <div v-else-if="items.length === 0" class="text-center py-16">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-400/30 to-accent-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-surface-secondary flex items-center justify-center">
          <span class="text-5xl">🛒</span>
        </div>
      </div>
      <p class="text-text-secondary font-medium text-lg">暂无商品</p>
      <p v-if="isLoggedIn" class="text-text-muted text-sm mt-2">去发布页上架第一件商品吧</p>
      <router-link v-if="isLoggedIn" to="/" class="mt-5 inline-block btn-primary">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-5 inline-block btn-primary">登录后发布 →</router-link>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="item in items" :key="item.id"
        class="glass-card-hover overflow-hidden h-full flex flex-col">
        <div class="relative w-full h-48 bg-surface-secondary flex items-center justify-center overflow-hidden flex-shrink-0">
          <img 
            v-if="item.original_image_url" 
            :src="item.original_image_url" 
            class="w-full h-full object-cover"
            alt="商品图片"
          />
          <span v-else class="text-5xl text-text-muted">📷</span>
          <div class="absolute top-3 right-3">
            <span class="badge badge-success">{{ item.category }}</span>
          </div>
        </div>
        <div class="p-5 flex-1 flex flex-col">
          <h3 class="font-semibold text-text-primary line-clamp-2 mb-2 flex-1">{{ item.ai_generated_title || 'AI 生成商品' }}</h3>
          <p class="text-sm text-text-muted line-clamp-2 mb-4">{{ item.ai_generated_desc }}</p>
          <div class="flex items-center justify-between">
            <div>
              <span v-if="item.suggested_price" class="text-xl font-bold text-danger-600 font-variant-numeric">¥{{ item.suggested_price.toLocaleString() }}</span>
              <span v-else class="text-sm text-text-muted">议价</span>
            </div>
            <span class="text-xs text-text-muted">by {{ item.username }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useUser } from '../store/user.js'
import { getMarket } from '../api/index.js'

const { isLoggedIn } = useUser()

const items = ref([])
const loading = ref(true)
const keyword = ref('')
const categoryFilter = ref('')

const categories = computed(() => {
  const cats = new Set(items.value.map(i => i.category))
  return Array.from(cats).filter(Boolean)
})

async function load() {
  loading.value = true
  try { items.value = await getMarket(keyword.value, categoryFilter.value) } catch {}
  finally { loading.value = false }
}

let timer = 0
watch([keyword, categoryFilter], () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})

onMounted(load)
</script>