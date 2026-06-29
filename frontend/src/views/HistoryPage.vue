<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-500/30 to-primary-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary-200 via-white to-primary-100 bg-clip-text text-transparent relative">发布历史</h1>
        </div>
        <p class="text-primary-400 text-sm mt-2">查看已生成的商品发布记录</p>
      </div>
      <div class="flex gap-3">
        <select 
          v-model="filterStatus" 
          class="px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all cursor-pointer"
          aria-label="状态筛选"
        >
          <option value="" class="bg-primary-800">全部状态</option>
          <option value="published" class="bg-primary-800">已发布</option>
          <option value="delisted" class="bg-primary-800">已下架</option>
          <option value="draft" class="bg-primary-800">草稿</option>
        </select>
        <div class="relative">
          <input 
            v-model="searchText" 
            placeholder="搜索型号…"
            class="w-40 sm:w-48 px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white placeholder:text-primary-500 outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all pl-10"
            autocomplete="off"
            aria-label="搜索型号"
          />
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-primary-400 text-sm">⌕</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div v-for="stat in stats" :key="stat.label"
        class="bg-primary-800/60 backdrop-blur-xl rounded-xl border border-primary-700/50 px-5 py-4 text-center shadow-sm">
        <div class="relative inline-block">
          <p class="text-3xl font-bold" :class="stat.color">{{ stat.count }}</p>
        </div>
        <p class="text-xs text-primary-400 mt-1.5">{{ stat.label }}</p>
      </div>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="bg-primary-800/60 backdrop-blur-xl rounded-xl border border-primary-700/50 p-5 flex gap-4 animate-pulse shadow-sm">
        <div class="w-24 h-24 bg-gradient-to-br from-primary-700/50 to-primary-600/30 rounded-xl" />
        <div class="flex-1 space-y-3 py-2">
          <div class="h-5 bg-primary-700/50 rounded-lg w-3/4" />
          <div class="h-4 bg-primary-700/50 rounded w-full" />
          <div class="h-4 bg-primary-700/50 rounded w-1/3" />
        </div>
      </div>
    </div>

    <div v-else-if="filteredItems.length === 0 && !loading" class="text-center py-20">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-500/30 to-primary-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary-800/80 to-primary-700/80 flex items-center justify-center">
          <span class="text-5xl">📦</span>
        </div>
      </div>
      <p class="text-primary-300 font-medium text-lg">还没有发布记录</p>
      <p class="text-primary-500 text-sm mt-2">去发布页生成第一条带货文案吧</p>
      <router-link to="/home" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">前往发布 →</router-link>
    </div>

    <div v-else class="space-y-4">
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
  { label: '全部', count: items.value.length, color: 'text-white' },
  { label: '已发布', count: items.value.filter(i => i.status === 'published').length, color: 'text-primary-300' },
  { label: '已下架', count: items.value.filter(i => i.status === 'delisted').length, color: 'text-primary-500' },
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