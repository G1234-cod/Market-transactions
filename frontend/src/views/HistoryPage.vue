<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold gradient-text">发布历史</h1>
        </div>
        <p class="text-text-muted text-sm mt-2">查看已生成的商品发布记录</p>
      </div>
      
      <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <div class="relative flex-1 sm:flex-none">
          <input 
            v-model="searchText" 
            placeholder="搜索型号…"
            class="w-full sm:w-48 px-4 py-3 pl-10 border border-border rounded-xl text-sm bg-white placeholder:text-text-muted focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
            autocomplete="off"
            aria-label="搜索型号"
          />
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">🔍</span>
        </div>
        <select 
          v-model="filterStatus" 
          class="px-4 py-3 text-sm border border-border rounded-xl bg-white text-text-primary outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all cursor-pointer"
          aria-label="状态筛选"
        >
          <option value="" class="bg-white">全部状态</option>
          <option value="published" class="bg-white">已发布</option>
          <option value="delisted" class="bg-white">已下架</option>
          <option value="sold" class="bg-white">已售出</option>
          <option value="draft" class="bg-white">草稿</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <div class="stat-card">
        <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-primary-100 flex items-center justify-center">
          <span class="text-primary-600 text-sm">📊</span>
        </div>
        <p class="stat-value text-text-primary">{{ items.length }}</p>
        <p class="stat-label">全部记录</p>
      </div>
      <div class="stat-card">
        <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-accent-100 flex items-center justify-center">
          <span class="text-accent-600 text-sm">✅</span>
        </div>
        <p class="stat-value text-accent-600">{{ items.filter(i => i.status === 'published').length }}</p>
        <p class="stat-label">已发布</p>
      </div>
      <div class="stat-card">
        <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-warning-100 flex items-center justify-center">
          <span class="text-warning-600 text-sm">📝</span>
        </div>
        <p class="stat-value text-warning-600">{{ items.filter(i => i.status === 'draft').length }}</p>
        <p class="stat-label">草稿</p>
      </div>
      <div class="stat-card">
        <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-gray-100 flex items-center justify-center">
          <span class="text-gray-600 text-sm">📦</span>
        </div>
        <p class="stat-value text-text-muted">{{ items.filter(i => i.status === 'delisted').length }}</p>
        <p class="stat-label">已下架</p>
      </div>
      <div class="stat-card">
        <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-success-100 flex items-center justify-center">
          <span class="text-success-600 text-sm">✅</span>
        </div>
        <p class="stat-value text-success-600">{{ items.filter(i => i.status === 'sold').length }}</p>
        <p class="stat-label">已售出</p>
      </div>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="glass-card p-5 flex gap-4 animate-pulse">
        <div class="w-24 h-24 bg-surface-tertiary rounded-xl" />
        <div class="flex-1 space-y-3 py-2">
          <div class="h-5 bg-surface-tertiary rounded-lg w-3/4" />
          <div class="h-4 bg-surface-tertiary rounded w-full" />
          <div class="h-4 bg-surface-tertiary rounded w-1/3" />
        </div>
      </div>
    </div>

    <div v-else-if="filteredItems.length === 0 && !loading" class="text-center py-16">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-400/30 to-accent-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-surface-secondary flex items-center justify-center">
          <span class="text-5xl">📦</span>
        </div>
      </div>
      <p class="text-text-secondary font-medium text-lg">还没有发布记录</p>
      <p class="text-text-muted text-sm mt-2">去发布页生成第一条带货文案吧</p>
      <router-link to="/" class="mt-5 inline-block btn-primary">前往发布 →</router-link>
    </div>

    <div v-else class="space-y-4">
      <HistoryCard v-for="item in filteredItems" :key="item.id" :item="item" @delist="doDelist" @publish="doPublish" @markSold="doMarkSold" @reevaluated="loadHistory" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useUser } from '../store/user.js'
import HistoryCard from '../components/HistoryCard.vue'
import { getHistory, delistItem, publishItem, markItemSold } from '../api/index.js'

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

async function loadHistory() {
  try { items.value = await getHistory(userId.value) } catch (e) { console.error('加载历史失败:', e) } finally { loading.value = false }
}
onMounted(loadHistory)

async function doDelist(id) {
  try {
    await delistItem(id)
    toast('已下架', 'success')
    await loadHistory()
  } catch { toast('操作失败', 'error') }
}

async function doPublish(id) {
  try {
    await publishItem(id)
    toast('已发布', 'success')
    await loadHistory()
  } catch { toast('操作失败', 'error') }
}

async function doMarkSold(id) {
  try {
    await markItemSold(id)
    toast('已标记为售出', 'success')
    await loadHistory()
  } catch { toast('操作失败', 'error') }
}
</script>