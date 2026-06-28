<template>
  <div class="space-y-6">
    <!-- ============================================================ -->
    <!-- 标题栏 -->
    <!-- ============================================================ -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-500/30 to-primary-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary-200 via-white to-primary-100 bg-clip-text text-transparent relative">二手商城</h1>
        </div>
        <p class="text-primary-400 text-sm mt-2">浏览所有用户发布的商品，找到心仪好物</p>
      </div>
    </div>

    <!-- ============================================================ -->
    <!-- 筛选栏 — 第一行：搜索 + 品类 + 成色 -->
    <!-- ============================================================ -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="relative flex-1 min-w-[180px] max-w-xs">
        <input
          v-model="keyword"
          placeholder="搜索商品…"
          class="w-full px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white placeholder:text-primary-500 outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all pl-10"
          autocomplete="off"
          aria-label="搜索商品"
        />
        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-primary-400 text-sm">⌕</span>
      </div>
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
        <option value="手表" class="bg-primary-800">手表</option>
      </select>
      <select
        v-model="conditionFilter"
        class="px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all cursor-pointer"
        aria-label="成色筛选"
      >
        <option value="" class="bg-primary-800">全部成色</option>
        <option value="99新" class="bg-primary-800">99新</option>
        <option value="95新" class="bg-primary-800">95新</option>
        <option value="9成新" class="bg-primary-800">9成新</option>
        <option value="85新" class="bg-primary-800">85新</option>
        <option value="8成新" class="bg-primary-800">8成新</option>
      </select>
    </div>

    <!-- ============================================================ -->
    <!-- 筛选栏 — 第二行：价格区间 + 排序 -->
    <!-- ============================================================ -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-2">
        <span class="text-xs text-primary-400 whitespace-nowrap">价格</span>
        <input
          v-model.number="priceMin"
          type="number"
          min="0"
          placeholder="最低"
          class="w-24 px-3 py-2 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white placeholder:text-primary-500 outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all"
          aria-label="最低价"
        />
        <span class="text-primary-500 text-xs">—</span>
        <input
          v-model.number="priceMax"
          type="number"
          min="0"
          placeholder="最高"
          class="w-24 px-3 py-2 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white placeholder:text-primary-500 outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all"
          aria-label="最高价"
        />
      </div>
      <select
        v-model="sortBy"
        class="px-4 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-white outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all cursor-pointer"
        aria-label="排序方式"
      >
        <option value="created_at" class="bg-primary-800">最新发布</option>
        <option value="price" class="bg-primary-800">价格排序</option>
      </select>
      <button
        @click="toggleSortOrder"
        class="px-3 py-2.5 text-sm border border-primary-600 rounded-xl bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500 transition-all cursor-pointer flex items-center gap-1"
        :title="sortOrder === 'desc' ? '降序排列' : '升序排列'"
      >
        <span>{{ sortOrder === 'desc' ? '↓ 降序' : '↑ 升序' }}</span>
      </button>
      <button
        v-if="hasActiveFilters"
        @click="clearFilters"
        class="px-4 py-2.5 text-sm border border-red-800 rounded-xl bg-red-900/30 text-red-300 hover:bg-red-900/50 hover:border-red-700 transition-all cursor-pointer"
      >
        清除筛选
      </button>
    </div>

    <!-- ============================================================ -->
    <!-- 结果统计 -->
    <!-- ============================================================ -->
    <div v-if="!loading && total > 0" class="text-xs text-primary-500">
      共 <span class="text-primary-300 font-medium">{{ total }}</span> 件商品
      <span v-if="hasActiveFilters">（已筛选）</span>
    </div>

    <!-- ============================================================ -->
    <!-- Loading 骨架屏 -->
    <!-- ============================================================ -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="bg-primary-800/60 backdrop-blur-xl rounded-xl border border-primary-700/50 p-4 animate-pulse shadow-sm">
        <div class="w-full h-44 bg-gradient-to-br from-primary-700/50 to-primary-600/30 rounded-xl mb-3" />
        <div class="h-4 bg-primary-700/50 rounded-lg w-3/4 mb-2" />
        <div class="h-3 bg-primary-700/50 rounded w-full mb-2" />
        <div class="h-3 bg-primary-700/50 rounded w-1/2" />
      </div>
    </div>

    <!-- ============================================================ -->
    <!-- 空状态 -->
    <!-- ============================================================ -->
    <div v-else-if="items.length === 0" class="text-center py-20">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-500/30 to-primary-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary-800/80 to-primary-700/80 flex items-center justify-center">
          <span class="text-5xl">🛒</span>
        </div>
      </div>
      <p v-if="hasActiveFilters" class="text-primary-300 font-medium text-lg">没有找到匹配的商品</p>
      <p v-else class="text-primary-300 font-medium text-lg">暂无商品</p>
      <p v-if="isLoggedIn && !hasActiveFilters" class="text-primary-500 text-sm mt-2">去发布页上架第一件商品吧</p>
      <button v-if="hasActiveFilters" @click="clearFilters" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">清除筛选条件</button>
      <router-link v-else-if="isLoggedIn" to="/home" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">前往发布 →</router-link>
      <router-link v-else to="/login" class="mt-5 inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 text-white text-sm font-medium hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5">登录后发布 →</router-link>
    </div>

    <!-- ============================================================ -->
    <!-- 商品卡片网格 -->
    <!-- ============================================================ -->
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
          <!-- 成色标签 -->
          <span v-if="item.condition" class="absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs bg-primary-900/70 text-primary-200 backdrop-blur-sm border border-primary-600/40">{{ item.condition }}</span>
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

    <!-- ============================================================ -->
    <!-- 分页控件 -->
    <!-- ============================================================ -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-4">
      <button
        @click="goToPage(1)"
        :disabled="page === 1"
        class="px-3 py-2 text-xs border border-primary-600 rounded-lg bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="首页"
      >« 首页</button>
      <button
        @click="goToPage(page - 1)"
        :disabled="page === 1"
        class="px-3 py-2 text-xs border border-primary-600 rounded-lg bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="上一页"
      >‹ 上页</button>

      <!-- 页码按钮 -->
      <template v-for="p in visiblePages" :key="p">
        <button
          v-if="p !== '...'"
          @click="goToPage(p)"
          :class="[
            'px-3 py-2 text-xs border rounded-lg transition-all',
            p === page
              ? 'bg-primary-500/30 border-primary-400 text-white font-semibold'
              : 'border-primary-600 bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500'
          ]"
        >{{ p }}</button>
        <span v-else class="px-2 text-primary-500 text-xs">…</span>
      </template>

      <button
        @click="goToPage(page + 1)"
        :disabled="page >= totalPages"
        class="px-3 py-2 text-xs border border-primary-600 rounded-lg bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="下一页"
      >下页 ›</button>
      <button
        @click="goToPage(totalPages)"
        :disabled="page >= totalPages"
        class="px-3 py-2 text-xs border border-primary-600 rounded-lg bg-primary-800/50 text-primary-300 hover:text-white hover:border-primary-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="末页"
      >末页 »</button>

      <span class="text-xs text-primary-500 ml-3">
        {{ page }} / {{ totalPages }} 页
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useUser } from '../store/user.js'
import { getMarket } from '../api/index.js'

const { isLoggedIn } = useUser()

// ============================================================
// 筛选状态
// ============================================================
const keyword = ref('')
const categoryFilter = ref('')
const conditionFilter = ref('')
const priceMin = ref(null)
const priceMax = ref(null)
const sortBy = ref('created_at')
const sortOrder = ref('desc')

// ============================================================
// 分页 & 数据
// ============================================================
const items = ref([])
const loading = ref(true)
const page = ref(1)
const total = ref(0)
const totalPages = ref(0)

// ============================================================
// 计算属性
// ============================================================
const hasActiveFilters = computed(() => {
  return keyword.value || categoryFilter.value || conditionFilter.value
    || priceMin.value != null || priceMax.value != null
})

// 可见的页码按钮（最多显示 5 个）
const visiblePages = computed(() => {
  const tp = totalPages.value
  if (tp <= 7) {
    return Array.from({ length: tp }, (_, i) => i + 1)
  }
  const p = page.value
  if (p <= 4) return [1, 2, 3, 4, 5, '...', tp]
  if (p >= tp - 3) return [1, '...', tp - 4, tp - 3, tp - 2, tp - 1, tp]
  return [1, '...', p - 1, p, p + 1, '...', tp]
})

// ============================================================
// 数据加载
// ============================================================
async function load() {
  loading.value = true
  try {
    const data = await getMarket({
      keyword: keyword.value,
      category: categoryFilter.value,
      condition: conditionFilter.value,
      priceMin: priceMin.value != null && priceMin.value >= 0 ? priceMin.value : null,
      priceMax: priceMax.value != null && priceMax.value >= 0 ? priceMax.value : null,
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
      page: page.value,
      pageSize: 20,
    })
    items.value = data.items || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || 0
  } catch {
    items.value = []
    total.value = 0
    totalPages.value = 0
  }
  finally { loading.value = false }
}

// ============================================================
// 交互
// ============================================================
function toggleSortOrder() {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

function goToPage(p) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function clearFilters() {
  keyword.value = ''
  categoryFilter.value = ''
  conditionFilter.value = ''
  priceMin.value = null
  priceMax.value = null
  sortBy.value = 'created_at'
  sortOrder.value = 'desc'
}

// ============================================================
// 监听筛选变化 → 重置到第 1 页 + 防抖加载
// ============================================================
let timer = 0
watch([
  keyword, categoryFilter, conditionFilter,
  priceMin, priceMax, sortBy, sortOrder,
], () => {
  page.value = 1
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})

// 监听页码变化 → 立即加载
watch(page, () => {
  clearTimeout(timer)
  load()
})

onMounted(load)
</script>