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
      
      <!-- ✅ R7: 统一搜索入口（图片搜索 + 文字搜索 + 关键词筛选） -->
      <div class="flex items-center gap-3 w-full sm:w-auto">
        <div class="flex items-center gap-1 bg-white border border-border rounded-xl px-3 py-2.5 shadow-sm">
          <div class="relative flex-1 sm:flex-none">
            <input
              v-model="keyword"
              placeholder="搜索商品…"
              class="w-full sm:w-48 px-2 py-0.5 text-sm bg-transparent placeholder:text-text-muted focus:outline-none"
              autocomplete="off"
              aria-label="搜索商品"
            />
          </div>
          <div class="flex items-center gap-0.5 border-l border-border pl-2 ml-1">
            <button @click="$router.push('/search?mode=image')" title="以图搜图" class="p-1.5 rounded-lg hover:bg-primary-50 text-text-secondary hover:text-primary-600 transition-colors" aria-label="以图搜图">
              📷
            </button>
            <button @click="$router.push('/search?mode=text')" title="以文搜图" class="p-1.5 rounded-lg hover:bg-primary-50 text-text-secondary hover:text-primary-600 transition-colors" aria-label="以文搜图">
              🔍
            </button>
          </div>
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
        <!-- 排序按钮 -->
        <div class="flex items-center gap-1">
          <button @click="toggleSort('price')" class="px-3 py-2.5 rounded-xl text-xs font-medium border transition-all"
            :class="sortBy === 'price' ? 'bg-primary-100 text-primary-700 border-primary-300' : 'bg-white text-text-secondary border-border hover:bg-surface-secondary'">
            💰 {{ sortBy === 'price' ? (sortOrder === 'asc' ? '价格↑' : '价格↓') : '价格' }}
          </button>
          <button @click="toggleSort('created_at')" class="px-3 py-2.5 rounded-xl text-xs font-medium border transition-all"
            :class="sortBy === 'created_at' ? 'bg-primary-100 text-primary-700 border-primary-300' : 'bg-white text-text-secondary border-border hover:bg-surface-secondary'">
            📅 {{ sortBy === 'created_at' ? (sortOrder === 'asc' ? '最早↑' : '最新↓') : '日期' }}
          </button>
        </div>
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
      <router-link v-if="isLoggedIn" to="/home" class="mt-5 inline-block btn-primary">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-5 inline-block btn-primary">登录后发布 →</router-link>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <!-- ✅ R8: 卡片展示：图片 + 发布人/品牌/型号/品类 + 参考价格 -->
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
        </div>
        <div class="p-4 flex-1 flex flex-col">
          <!-- R8: 发布人 + 品类 -->
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-text-muted">
              发布人：<span class="text-text-secondary font-medium">{{ item.username }}</span>
            </span>
            <span v-if="item.category" class="badge badge-success text-[10px]">{{ item.category }}</span>
          </div>
          <!-- R8: 品牌 + 型号 -->
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs text-text-muted">品牌：<span class="text-text-secondary font-medium">{{ item.brand || '—' }}</span></span>
            <span class="text-xs text-text-muted">型号：<span class="text-text-secondary font-medium">{{ item.model || '—' }}</span></span>
          </div>
          <div class="flex items-center justify-between pt-2 border-t border-border-light mt-auto">
            <span v-if="item.suggested_price" class="text-lg font-bold text-danger-600 font-variant-numeric">¥{{ item.suggested_price.toLocaleString() }}</span>
            <span v-else class="text-sm text-text-muted">参考价：议价</span>
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
    // ✅ 修复：传递对象而非位置参数（之前品类筛选完全无效）
    const data = await getMarket({ keyword: keyword.value, category: categoryFilter.value, sortBy: sortBy.value, sortOrder: sortOrder.value })
    items.value = data.items || []
  } catch (e) { console.error('加载商城数据失败:', e) }
  finally { loading.value = false }
}

// ✅ 修复：组件卸载时清理定时器防止内存泄漏
let timer = 0
watch([keyword, categoryFilter, sortBy, sortOrder], () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})

onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>