<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-500/30 to-primary-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary-200 via-white to-primary-100 bg-clip-text text-transparent relative">二手商城</h1>
        </div>
        <p class="text-primary-400 text-sm mt-2">浏览所有用户发布的商品，找到心仪好物</p>
      </div>
      <div class="flex gap-3">
        <select 
          v-model="categoryFilter" 
          class="px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all cursor-pointer"
          aria-label="分类筛选"
        >
          <option value="" class="bg-primary-800">全部分类</option>
          <option value="手机" class="bg-primary-800">手机</option>
          <option value="笔记本" class="bg-primary-800">笔记本</option>
          <option value="平板" class="bg-primary-800">平板</option>
          <option value="外设" class="bg-primary-800">外设</option>
          <option value="耳机" class="bg-primary-800">耳机</option>
        </select>
        <div class="relative">
          <input 
            v-model="keyword" 
            placeholder="搜索商品…"
            class="w-48 sm:w-64 px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white placeholder:text-primary-500 outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all pl-10"
            autocomplete="off"
            aria-label="搜索商品"
          />
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-primary-400 text-sm">⌕</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="bg-primary-800/60 backdrop-blur-xl rounded-xl border border-primary-700/50 p-4 animate-pulse shadow-sm">
        <div class="w-full h-44 bg-gradient-to-br from-primary-700/50 to-primary-600/30 rounded-xl mb-3" />
        <div class="h-4 bg-primary-700/50 rounded-lg w-3/4 mb-2" />
        <div class="h-3 bg-primary-700/50 rounded w-full mb-2" />
        <div class="h-3 bg-primary-700/50 rounded w-1/2" />
      </div>
    </div>

    <div v-else-if="items.length === 0" class="text-center py-20">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-500/30 to-primary-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary-800/80 to-primary-700/80 flex items-center justify-center">
          <span class="text-5xl">🛒</span>
        </div>
      </div>
      <p class="text-primary-300 font-medium text-lg">暂无商品</p>
      <p v-if="isLoggedIn" class="text-primary-500 text-sm mt-2">去发布页上架第一件商品吧</p>
      <router-link v-if="isLoggedIn" to="/home" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">登录后发布 →</router-link>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="item in items" :key="item.id"
        class="bg-primary-800/60 backdrop-blur-xl rounded-xl border border-primary-700/50 overflow-hidden hover:shadow-xl hover:border-primary-500 transition-all duration-300 group cursor-pointer transform hover:-translate-y-1">
        <div class="relative w-full h-48 bg-gradient-to-br from-primary-900/50 to-primary-800/50 flex items-center justify-center overflow-hidden">
          <img 
            v-if="item.original_image_url" 
            :src="item.original_image_url" 
            class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
            alt="商品图片"
          />
          <span v-else class="text-5xl text-primary-500">📷</span>
          <div class="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div class="p-5 space-y-3">
          <div class="flex items-start justify-between gap-2">
            <h3 class="font-semibold text-white truncate group-hover:text-primary-200 transition-colors flex-1 min-w-0">{{ item.ai_generated_title || 'AI 生成商品' }}</h3>
          </div>
          <p class="text-xs text-primary-400 line-clamp-2 leading-relaxed">{{ item.ai_generated_desc }}</p>
          <div class="flex items-center justify-between pt-2 border-t border-primary-700/50">
            <div>
              <span v-if="item.suggested_price" class="text-xl font-bold text-red-400 font-variant-numeric">¥{{ item.suggested_price.toLocaleString() }}</span>
              <span v-else class="text-sm text-primary-500">议价</span>
            </div>
            <span class="text-xs text-primary-500">by {{ item.username }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useUser } from '../store/user.js'
import { getMarket } from '../api/index.js'

const { isLoggedIn } = useUser()

const items = ref([])
const loading = ref(true)
const keyword = ref('')
const categoryFilter = ref('')

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