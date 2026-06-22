<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">发布历史</h1>
        <p class="text-gray-400 text-sm mt-1">查看已生成的商品发布记录</p>
      </div>
      <div class="flex gap-2">
        <select v-model="filterStatus" class="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white outline-none focus:ring-2 focus:ring-blue-400 transition-all">
          <option value="">全部状态</option>
          <option value="published">已发布</option>
          <option value="delisted">已下架</option>
          <option value="draft">草稿</option>
        </select>
        <div class="relative">
          <input v-model="searchText" placeholder="搜索型号..."
            class="w-40 px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white outline-none focus:ring-2 focus:ring-blue-400 transition-all pl-8" />
          <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">⌕</span>
        </div>
      </div>
    </div>

    <!-- 统计概览 -->
    <div class="grid grid-cols-3 gap-3">
      <div v-for="stat in stats" :key="stat.label"
        class="bg-white rounded-xl border border-gray-100 px-4 py-3 text-center shadow-sm">
        <p class="text-2xl font-bold" :class="stat.color">{{ stat.count }}</p>
        <p class="text-xs text-gray-400 mt-0.5">{{ stat.label }}</p>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-gray-100 p-4 flex gap-4 animate-pulse">
        <div class="w-20 h-20 bg-gray-100 rounded-xl" />
        <div class="flex-1 space-y-2 py-1">
          <div class="h-4 bg-gray-100 rounded w-3/4" /><div class="h-3 bg-gray-100 rounded w-full" /><div class="h-3 bg-gray-100 rounded w-1/3" />
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredItems.length === 0 && !loading" class="text-center py-20">
      <div class="mx-auto w-20 h-20 rounded-full bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center mb-4">
        <span class="text-4xl">📦</span>
      </div>
      <p class="text-gray-400 font-medium">还没有发布记录</p>
      <p class="text-gray-300 text-sm mt-1">去发布页生成第一条带货文案吧</p>
      <router-link to="/" class="mt-4 inline-block px-5 py-2 rounded-xl bg-blue-50 text-blue-600 text-sm font-medium hover:bg-blue-100 transition-colors">前往发布 →</router-link>
    </div>

    <!-- 列表 -->
    <div v-else class="space-y-3">
      <HistoryCard v-for="item in filteredItems" :key="item.id" :item="item" @delist="doDelist" @publish="doPublish" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useUser } from '../store/user.js'
import HistoryCard from '../components/HistoryCard.vue'
import { getHistory, delistItem, publishItem } from '../api/index.js'

const toast = inject('toast', () => {})
const { userId } = useUser()
const items = ref([])
const loading = ref(true)
const filterStatus = ref('')
const searchText = ref('')

const filteredItems = computed(() => {
  let list = items.value
  if (filterStatus.value) list = list.filter(i => i.status === filterStatus.value)
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(i => (i.ai_generated_title || '').toLowerCase().includes(q) || (i.ai_generated_desc || '').toLowerCase().includes(q))
  }
  return list
})

const stats = computed(() => [
  { label: '全部', count: items.value.length, color: 'text-gray-700' },
  { label: '已发布', count: items.value.filter(i => i.status === 'published').length, color: 'text-blue-600' },
  { label: '已下架', count: items.value.filter(i => i.status === 'delisted').length, color: 'text-gray-400' },
])

async function loadHistory() {
  try { items.value = await getHistory(userId.value) } catch {} finally { loading.value = false }
}
onMounted(loadHistory)

async function doDelist(id) {
  await delistItem(id)
  toast('已下架', 'success')
  loadHistory()
}

async function doPublish(id) {
  await publishItem(id)
  toast('已发布', 'success')
  loadHistory()
}
</script>
