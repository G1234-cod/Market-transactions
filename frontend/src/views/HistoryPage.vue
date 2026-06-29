<template>
  <div class="space-y-10 relative">
    <div class="hero-section relative py-12 sm:py-16 overflow-hidden">
      <div class="orb orb-primary w-72 h-72 -top-5 -left-5 animate-float-slow"></div>
      <div class="orb orb-accent w-56 h-56 bottom-0 -right-5 animate-float-medium"></div>
      
      <div class="relative z-10">
        <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div>
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-medium mb-4 animate-fade-in-up-1">
              <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse"></span>
              我的记录
            </div>
            
            <h1 class="text-4xl sm:text-5xl font-extrabold gradient-text animate-fade-in-up-2">发布历史</h1>
            <p class="text-text-secondary text-base mt-3 max-w-lg animate-fade-in-up-3">查看已生成的商品发布记录</p>
          </div>
          
          <div class="flex flex-col sm:flex-row gap-3 w-full lg:w-auto animate-fade-in-up-4">
            <div class="relative flex-1 sm:flex-none">
              <input 
                v-model="searchText" 
                placeholder="搜索型号…"
                class="w-full sm:w-56 px-5 py-3 pl-12 border border-border rounded-xl text-sm bg-space-card/80 text-text-primary placeholder:text-text-muted focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/10 focus:outline-none transition-all"
                autocomplete="off"
                aria-label="搜索型号"
              />
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">🔍</span>
            </div>
            <select 
              v-model="filterStatus" 
              class="px-5 py-3 text-sm border border-border rounded-xl bg-space-card/80 text-text-primary outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/10 transition-all cursor-pointer"
              aria-label="状态筛选"
            >
              <option value="" class="bg-space-card">全部状态</option>
              <option value="published" class="bg-space-card">已发布</option>
              <option value="delisted" class="bg-space-card">已下架</option>
              <option value="sold" class="bg-space-card">已售出</option>
              <option value="draft" class="bg-space-card">草稿</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-5 animate-fade-in-up-2">
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center">
          <span class="text-primary-400 text-xl">📊</span>
        </div>
        <p class="stat-value text-text-primary text-3xl">{{ items.length }}</p>
        <p class="stat-label text-sm">全部记录</p>
      </div>
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 flex items-center justify-center">
          <span class="text-accent-400 text-xl">✅</span>
        </div>
        <p class="stat-value text-accent-400 text-3xl">{{ items.filter(i => i.status === 'published').length }}</p>
        <p class="stat-label text-sm">已发布</p>
      </div>
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/20 flex items-center justify-center">
          <span class="text-amber-400 text-xl">📝</span>
        </div>
        <p class="stat-value text-amber-400 text-3xl">{{ items.filter(i => i.status === 'draft').length }}</p>
        <p class="stat-label text-sm">草稿</p>
      </div>
      <div class="stat-card card-glow-hover">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-success-500/20 to-success-600/20 flex items-center justify-center">
          <span class="text-success-400 text-xl">✅</span>
        </div>
        <p class="stat-value text-success-400 text-3xl">{{ items.filter(i => i.status === 'sold').length }}</p>
        <p class="stat-label text-sm">已售出</p>
      </div>
    </div>

    <div v-if="loading" class="space-y-5 animate-fade-in-up-3">
      <div v-for="i in 3" :key="i" class="glass-card p-6 flex gap-5 animate-pulse">
        <div class="w-28 h-28 bg-space-lighter/50 rounded-2xl" />
        <div class="flex-1 space-y-4 py-2">
          <div class="h-6 bg-space-lighter/50 rounded-lg w-3/4" />
          <div class="h-4 bg-space-lighter/50 rounded w-full" />
          <div class="h-4 bg-space-lighter/50 rounded w-1/3" />
        </div>
      </div>
    </div>

    <div v-else-if="filteredItems.length === 0 && !loading" class="text-center py-24 animate-fade-in-up-3">
      <div class="relative inline-block mb-8">
        <div class="absolute -inset-6 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-3xl blur-xl -z-10"></div>
        <div class="w-32 h-32 rounded-full bg-space-card/80 flex items-center justify-center border border-border/50">
          <span class="text-6xl">📦</span>
        </div>
      </div>
      <p class="text-text-secondary font-semibold text-xl">还没有发布记录</p>
      <p class="text-text-muted text-base mt-3">去发布页生成第一条带货文案吧</p>
      <router-link to="/home" class="mt-6 inline-block btn-primary ripple-container">前往发布 →</router-link>
    </div>

    <div v-else class="space-y-5 animate-fade-in-up-3">
      <HistoryCard v-for="(item, index) in filteredItems" :key="item.id" :item="item" 
        @delist="doDelist" @publish="doPublish" @markSold="doMarkSold" @reevaluated="loadHistory"
        :style="{ animationDelay: `${0.1 + index * 0.08}s` }" />
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
