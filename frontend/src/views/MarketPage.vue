<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">二手商城</h1>
        <p class="text-gray-400 text-sm mt-1">浏览所有用户发布的商品，找到心仪好物</p>
      </div>
      <div class="flex gap-2">
        <select v-model="categoryFilter" class="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white outline-none focus:ring-2 focus:ring-blue-400 transition-all">
          <option value="">全部分类</option>
          <option value="手机">手机</option>
          <option value="笔记本">笔记本</option>
          <option value="平板">平板</option>
          <option value="外设">外设</option>
          <option value="耳机">耳机</option>
        </select>
        <div class="relative">
          <input v-model="keyword" placeholder="搜索商品..."
            class="w-48 px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white outline-none focus:ring-2 focus:ring-blue-400 transition-all pl-8" />
          <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">⌕</span>
        </div>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="bg-white rounded-xl border border-gray-100 p-4 animate-pulse">
        <div class="w-full h-40 bg-gray-100 rounded-lg mb-3" />
        <div class="h-4 bg-gray-100 rounded w-3/4 mb-2" />
        <div class="h-3 bg-gray-100 rounded w-full mb-2" />
        <div class="h-3 bg-gray-100 rounded w-1/2" />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="items.length === 0" class="text-center py-20">
      <div class="mx-auto w-20 h-20 rounded-full bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center mb-4">
        <span class="text-4xl">🛒</span>
      </div>
      <p class="text-gray-400 font-medium">暂无商品</p>
      <p v-if="isLoggedIn" class="text-gray-300 text-sm mt-1">去发布页上架第一件商品吧</p>
      <router-link v-if="isLoggedIn" to="/" class="mt-4 inline-block px-5 py-2 rounded-xl bg-blue-50 text-blue-600 text-sm font-medium hover:bg-blue-100 transition-colors">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-4 inline-block px-5 py-2 rounded-xl bg-blue-50 text-blue-600 text-sm font-medium hover:bg-blue-100 transition-colors">登录后发布 →</router-link>
    </div>

    <!-- 商品网格 -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="item in items" :key="item.id"
        class="bg-white rounded-xl border border-gray-100 overflow-hidden hover:shadow-lg hover:border-gray-200 transition-all group cursor-pointer">
        <!-- 图片 -->
        <div class="w-full h-44 bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center overflow-hidden">
          <img v-if="item.original_image_url" :src="item.original_image_url" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
          <span v-else class="text-4xl text-blue-300">📷</span>
        </div>
        <!-- 信息 -->
        <div class="p-4 space-y-2">
          <h3 class="font-semibold text-gray-800 truncate group-hover:text-blue-600 transition-colors">{{ item.ai_generated_title || 'AI 生成商品' }}</h3>
          <p class="text-xs text-gray-400 line-clamp-2 leading-relaxed">{{ item.ai_generated_desc }}</p>
          <div class="flex items-center justify-between pt-1">
            <span v-if="item.suggested_price" class="text-lg font-bold text-red-500">¥{{ item.suggested_price }}</span>
            <span v-else class="text-sm text-gray-300">议价</span>
            <span class="text-xs text-gray-400">by {{ item.username }}</span>
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
