<template>
  <div class="space-y-10 relative">
    <div class="hero-section relative py-12 sm:py-16 overflow-hidden">
      <div class="orb orb-primary w-80 h-80 -top-10 -right-10 animate-float-slow"></div>
      <div class="orb orb-accent w-64 h-64 bottom-0 -left-10 animate-float-medium"></div>
      
      <div class="relative z-10">
        <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div>
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-medium mb-4 animate-fade-in-up-1">
              <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse"></span>
              实时更新
            </div>
            
            <h1 class="text-4xl sm:text-5xl font-extrabold gradient-text animate-fade-in-up-2">二手商城</h1>
            <p class="text-text-secondary text-base mt-3 max-w-lg animate-fade-in-up-3">浏览所有用户发布的商品，找到心仪好物</p>
          </div>
          
          <div class="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto animate-fade-in-up-4">
            <div class="flex items-center gap-1 bg-space-card/80 border border-border rounded-xl px-4 py-3 shadow-lg shadow-black/10 w-full sm:w-auto">
              <div class="relative flex-1 sm:flex-none">
                <input
                  v-model="keyword"
                  placeholder="搜索商品…"
                  class="w-full sm:w-48 px-3 py-1.5 text-sm bg-transparent placeholder:text-text-muted focus:outline-none text-text-primary"
                  autocomplete="off"
                  aria-label="搜索商品"
                />
              </div>
              <div class="flex items-center gap-0.5 border-l border-border pl-3 ml-1">
                <button @click="$router.push('/search?mode=image')" title="以图搜图" class="p-2 rounded-lg hover:bg-primary-500/10 text-text-secondary hover:text-primary-400 transition-all" aria-label="以图搜图">
                  📷
                </button>
                <button @click="$router.push('/search?mode=text')" title="以文搜图" class="p-2 rounded-lg hover:bg-primary-500/10 text-text-secondary hover:text-primary-400 transition-all" aria-label="以文搜图">
                  🔍
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-3 mt-6 animate-fade-in-up-5">
          <select
            v-model="categoryFilter"
            class="px-4 py-2.5 text-sm border border-border rounded-xl bg-space-card/80 text-text-primary outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/10 transition-all cursor-pointer"
            aria-label="分类筛选"
          >
            <option value="" class="bg-space-card">全部分类</option>
            <option value="手机" class="bg-space-card">手机</option>
            <option value="笔记本" class="bg-space-card">笔记本</option>
            <option value="平板" class="bg-space-card">平板</option>
            <option value="外设" class="bg-space-card">外设</option>
            <option value="耳机" class="bg-space-card">耳机</option>
          </select>
          <div class="flex items-center gap-2">
            <button @click="toggleSort('price')" class="px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ripple-container"
              :class="sortBy === 'price' ? 'bg-primary-500/20 text-primary-400 border-primary-500/30' : 'bg-space-card/80 text-text-secondary border-border hover:bg-space-lighter/50'">
              💰 {{ sortBy === 'price' ? (sortOrder === 'asc' ? '价格↑' : '价格↓') : '价格' }}
            </button>
            <button @click="toggleSort('created_at')" class="px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ripple-container"
              :class="sortBy === 'created_at' ? 'bg-primary-500/20 text-primary-400 border-primary-500/30' : 'bg-space-card/80 text-text-secondary border-border hover:bg-space-lighter/50'">
              📅 {{ sortBy === 'created_at' ? (sortOrder === 'asc' ? '最早↑' : '最新↓') : '日期' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 animate-fade-in-up-2">
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center">
          <span class="text-primary-400 text-2xl">📦</span>
        </div>
        <p class="stat-value text-text-primary text-4xl"><AnimatedNumber :value="items.length" /></p>
        <p class="stat-label text-sm">全部商品</p>
      </div>
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 flex items-center justify-center">
          <span class="text-accent-400 text-2xl">🏷️</span>
        </div>
        <p class="stat-value text-accent-400 text-4xl"><AnimatedNumber :value="categories.length" /></p>
        <p class="stat-label text-sm">商品分类</p>
      </div>
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/20 flex items-center justify-center">
          <span class="text-amber-400 text-2xl">💰</span>
        </div>
        <p class="stat-value text-amber-400 text-4xl">¥<AnimatedNumber :value="Math.floor(items.reduce((sum, i) => sum + (i.suggested_price || 0), 0) / Math.max(1, items.length))" /></p>
        <p class="stat-label text-sm">均价</p>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in-up-3">
      <div v-for="i in 6" :key="i" class="glass-card p-6 animate-pulse">
        <div class="w-full h-56 bg-space-lighter/50 rounded-2xl mb-5" />
        <div class="h-6 bg-space-lighter/50 rounded-lg w-3/4 mb-3" />
        <div class="h-4 bg-space-lighter/50 rounded w-full mb-3" />
        <div class="h-5 bg-space-lighter/50 rounded w-1/2" />
      </div>
    </div>

    <div v-else-if="items.length === 0" class="text-center py-24 animate-fade-in-up-3">
      <div class="relative inline-block mb-8">
        <div class="absolute -inset-6 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-3xl blur-xl -z-10"></div>
        <div class="w-32 h-32 rounded-full bg-space-card/80 flex items-center justify-center border border-border/50">
          <span class="text-6xl">🛒</span>
        </div>
      </div>
      <p class="text-text-secondary font-semibold text-xl">暂无商品</p>
      <p v-if="isLoggedIn" class="text-text-muted text-base mt-3">去发布页上架第一件商品吧</p>
      <router-link v-if="isLoggedIn" to="/home" class="mt-6 inline-block btn-primary ripple-container">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-6 inline-block btn-primary ripple-container">登录后发布 →</router-link>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="(item, index) in items"
        :key="item.id"
        :class="[
          'glass-card-hover overflow-hidden h-full flex flex-col card-glow-hover',
          index === 0 && 'lg:col-span-2 lg:row-span-2'
        ]"
        :style="{ animationDelay: `${0.1 + index * 0.08}s` }"
      >
        <div :class="[
          'relative flex-shrink-0 overflow-hidden group',
          index === 0 ? 'h-72 lg:h-full' : 'h-56'
        ]">
          <img
            v-if="item.original_image_url"
            :src="item.original_image_url"
            :class="[
              'w-full h-full object-cover transition-transform duration-700',
              index === 0 ? 'group-hover:scale-105' : 'group-hover:scale-110'
            ]"
            alt="商品图片"
          />
          <span v-else :class="['flex items-center justify-center text-text-muted', index === 0 ? 'text-7xl' : 'text-5xl']">📷</span>
          <div class="absolute inset-0 bg-gradient-to-t from-space-card via-space-card/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div v-if="index === 0" class="absolute top-4 left-4 px-4 py-2 rounded-full bg-gradient-to-r from-primary-500 to-accent-500 text-white text-xs font-bold">
            🔥 精选推荐
          </div>
        </div>
        <div :class="['p-6 flex-1 flex flex-col', index === 0 ? 'lg:p-8' : '']">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-text-muted">
              发布人：<span class="text-text-secondary font-medium">{{ item.username }}</span>
            </span>
            <span v-if="item.category" class="badge badge-success">{{ item.category }}</span>
          </div>
          <div class="flex items-center gap-2 mb-3 flex-wrap">
            <span v-if="item.brand" class="text-xs px-3 py-1 rounded-md bg-primary-500/15 text-primary-400 font-medium">品牌：{{ item.brand }}</span>
            <span v-if="item.model" class="text-xs px-3 py-1 rounded-md bg-space-lighter/50 text-text-secondary">型号：{{ item.model }}</span>
          </div>
          <div class="flex items-center justify-between pt-4 border-t border-border/30 mt-auto">
            <span v-if="item.suggested_price" class="text-xl font-bold text-amber-400 font-variant-numeric">¥{{ item.suggested_price.toLocaleString() }}</span>
            <span v-else class="text-base text-text-muted">参考价：议价</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useUser } from '../store/user.js'
import { getMarket } from '../api/index.js'
import AnimatedNumber from '../components/AnimatedNumber.vue'

const { isLoggedIn } = useUser()

const items = ref([])
const loading = ref(true)
const keyword = ref('')
const categoryFilter = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

function toggleSort(field) {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortOrder.value = 'desc'
  }
}

const categories = computed(() => {
  const cats = new Set(items.value.map(i => i.category))
  return Array.from(cats).filter(Boolean)
})

async function load() {
  loading.value = true
  try {
    const data = await getMarket({ keyword: keyword.value, category: categoryFilter.value, sortBy: sortBy.value, sortOrder: sortOrder.value })
    items.value = data.items || []
  } catch (e) { console.error('加载商城数据失败:', e) }
  finally { loading.value = false }
}

let timer = 0
watch([keyword, categoryFilter, sortBy, sortOrder], () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})

onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>
