<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold gradient-text">智能搜索</h1>
        </div>
        <p class="text-text-muted text-sm mt-2">以图搜图 · 以文搜图 · 按类别型号查找</p>
      </div>
    </div>

    <!-- 搜索模式切换 -->
    <div class="glass-card p-5">
      <div class="flex gap-2 mb-6">
        <button
          class="px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
          :class="searchMode === 'image' ? 'gradient-primary text-white shadow-lg shadow-primary-500/30' : 'bg-surface-secondary text-text-secondary hover:bg-primary-50 hover:text-primary-600'"
          @click="searchMode = 'image'"
        >
          <span class="mr-2">🖼️</span>以图搜图
        </button>
        <button
          class="px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
          :class="searchMode === 'text' ? 'gradient-primary text-white shadow-lg shadow-primary-500/30' : 'bg-surface-secondary text-text-secondary hover:bg-primary-50 hover:text-primary-600'"
          @click="searchMode = 'text'"
        >
          <span class="mr-2">📝</span>以文搜图
        </button>
        <button
          class="px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
          :class="searchMode === 'filter' ? 'gradient-primary text-white shadow-lg shadow-primary-500/30' : 'bg-surface-secondary text-text-secondary hover:bg-primary-50 hover:text-primary-600'"
          @click="switchToFilterMode"
        >
          <span class="mr-2">🔍</span>按类别型号
        </button>
      </div>

      <!-- 以图搜图 -->
      <div v-if="searchMode === 'image'" class="space-y-4">
        <div class="border-2 border-dashed rounded-2xl p-8 text-center transition-all"
          :class="isDragging ? 'border-primary-400 bg-primary-50/50' : 'border-border hover:border-primary-300'"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <div v-if="!searchImage" class="space-y-4">
            <div class="w-20 h-20 mx-auto rounded-2xl bg-surface-secondary flex items-center justify-center">
              <span class="text-4xl">📷</span>
            </div>
            <div>
              <p class="text-text-secondary font-medium">拖拽图片到这里</p>
              <p class="text-text-muted text-sm mt-1">或点击下方按钮选择文件</p>
            </div>
            <button
              class="btn-outline"
              @click="triggerFileInput"
            >
              选择图片
            </button>
            <input
              ref="fileInput"
              type="file"
              accept="image/*"
              class="hidden"
              @change="handleFileSelect"
            />
          </div>

          <div v-else class="space-y-4">
            <div class="relative inline-block">
              <img
                :src="previewUrl"
                alt="搜索图片预览"
                class="max-h-64 mx-auto rounded-xl shadow-lg"
              />
              <button
                class="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-red-500 text-white flex items-center justify-center shadow-lg hover:bg-red-600 transition-colors"
                @click="clearSearchImage"
              >
                ×
              </button>
            </div>
            <p class="text-text-muted text-sm">{{ searchImage.name }}</p>
            <button
              class="btn-primary"
              @click="performImageSearch"
              :disabled="searching"
            >
              <span v-if="searching" class="loading-spinner mr-2" />
              {{ searching ? '搜索中...' : '🔍 开始搜索' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 以文搜图 (CLIP语义搜索) -->
      <div v-else-if="searchMode === 'text'" class="space-y-4">
        <div class="space-y-3">
          <div>
            <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">搜索描述</label>
            <textarea
              v-model="searchText"
              rows="4"
              placeholder="描述你想要的商品，例如：'iPhone 13 256G 95新 白色' 或 '小米笔记本 Pro 15'"
              class="textarea-field"
              @keydown.ctrl.enter="performTextSearch"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">品类筛选（可选）</label>
              <select v-model="filterCategory" class="input-field cursor-pointer">
                <option value="">全部品类</option>
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">返回数量</label>
              <select v-model="topK" class="input-field cursor-pointer">
                <option value="5">5 条结果</option>
                <option value="10">10 条结果</option>
                <option value="20">20 条结果</option>
              </select>
            </div>
          </div>

          <button
            class="btn-primary w-full"
            @click="performTextSearch"
            :disabled="!searchText.trim() || searching"
          >
            <span v-if="searching" class="loading-spinner mr-2" />
            {{ searching ? '搜索中...' : '🔍 开始搜索' }}
          </button>
        </div>
      </div>

      <!-- 按类别型号搜索 (数据库直查) -->
      <div v-else-if="searchMode === 'filter'" class="space-y-4">
        <div class="bg-gradient-to-r from-accent-50 to-primary-50 rounded-xl p-4 mb-2">
          <p class="text-sm text-accent-700 font-medium">📋 按品类、品牌、型号精确查找商品</p>
          <p class="text-xs text-text-muted mt-1">从数据库直接查询，支持级联筛选</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <!-- 品类选择 -->
          <div>
            <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">
              品类 <span class="text-danger-500">*</span>
            </label>
            <select
              v-model="filterForm.category"
              class="input-field cursor-pointer"
              @change="onCategoryChange"
            >
              <option value="">选择品类</option>
              <option v-for="cat in filterCategories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>

          <!-- 品牌选择 -->
          <div>
            <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">品牌</label>
            <select
              v-model="filterForm.brand"
              class="input-field cursor-pointer"
              :disabled="!filterForm.category"
              @change="onBrandChange"
            >
              <option value="">全部品牌</option>
              <option v-for="b in filterBrands" :key="b" :value="b">{{ b }}</option>
            </select>
          </div>

          <!-- 型号搜索 -->
          <div>
            <label class="block text-xs text-text-muted font-medium uppercase tracking-wider mb-2">型号</label>
            <div class="relative">
              <input
                v-model="filterForm.model"
                placeholder="输入型号关键词..."
                class="input-field"
                autocomplete="off"
                @keydown.enter="performFilterSearch"
              />
              <div v-if="filterForm.model && filteredModelSuggestions.length > 0"
                class="absolute top-full left-0 right-0 bg-white border border-border rounded-xl shadow-lg z-20 max-h-48 overflow-y-auto mt-1">
                <div
                  v-for="m in filteredModelSuggestions"
                  :key="m.model"
                  class="px-4 py-2 text-sm hover:bg-primary-50 cursor-pointer flex items-center justify-between"
                  @click="selectModelSuggestion(m)"
                >
                  <span>{{ m.model }}</span>
                  <span class="text-xs text-text-muted">{{ m.count }}件</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <button
            class="btn-primary flex-1"
            @click="performFilterSearch"
            :disabled="!filterForm.category || searching"
          >
            <span v-if="searching" class="loading-spinner mr-2" />
            {{ searching ? '搜索中...' : '🔍 搜索商品' }}
          </button>
          <button
            class="btn-outline"
            @click="clearFilterSearch"
            :disabled="searching"
          >
            重置
          </button>
        </div>

        <!-- 快速型号选择 -->
        <div v-if="filterSuggestModels.length > 0 && !filterForm.model" class="space-y-2">
          <p class="text-xs text-text-muted font-medium">💡 常见型号快速选择：</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="m in filterSuggestModels.slice(0, 15)"
              :key="m.model"
              class="px-3 py-1 rounded-lg text-xs bg-surface-secondary hover:bg-primary-100 hover:text-primary-700 transition-colors"
              @click="selectModelSuggestion(m)"
            >
              {{ m.model }} ({{ m.count }})
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div v-if="searchResults.length > 0" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-text-primary">
          找到 {{ filterTotal > 0 ? filterTotal : searchResults.length }} 个商品
          <span v-if="filterTotalPages > 1" class="text-sm text-text-muted font-normal ml-2">第 {{ filterPage }} / {{ filterTotalPages }} 页</span>
        </h2>
        <div class="flex gap-2">
          <button
            v-if="searchMode === 'filter' && filterPage > 1"
            class="btn-secondary-sm"
            @click="changeFilterPage(filterPage - 1)"
          >
            ← 上一页
          </button>
          <button
            v-if="searchMode === 'filter' && filterPage < filterTotalPages"
            class="btn-secondary-sm"
            @click="changeFilterPage(filterPage + 1)"
          >
            下一页 →
          </button>
          <button class="btn-secondary-sm" @click="clearResults">
            清空结果
          </button>
        </div>
      </div>

      <!-- 商品网格 -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div
          v-for="item in searchResults"
          :key="item.id"
          class="glass-card-hover group cursor-pointer"
          @click="goToMarket"
        >
          <div class="image-hover-zoom">
            <img
              :src="item.image_url"
              :alt="(item.brand || '') + ' ' + (item.model || '')"
              class="w-full h-48 object-cover"
              @error="handleImageError"
            />
          </div>
          <div class="p-4">
            <div class="flex flex-wrap gap-1.5 mb-2">
              <span v-if="item.category" class="px-2 py-0.5 rounded-md text-xs font-medium bg-accent-100 text-accent-700">{{ item.category }}</span>
              <span v-if="item.brand" class="px-2 py-0.5 rounded-md text-xs font-medium bg-primary-100 text-primary-700">{{ item.brand }}</span>
              <span v-if="item.model" class="px-2 py-0.5 rounded-md text-xs font-medium bg-surface-secondary text-text-secondary">{{ item.model }}</span>
            </div>
            <div v-if="item.reason" class="text-xs text-text-muted mt-1">{{ item.reason }}</div>
            <div class="flex items-center justify-between mt-3">
              <span v-if="item.price" class="text-lg font-bold text-accent-600">
                ¥{{ formatPrice(item.price) }}
              </span>
              <span v-else class="text-sm text-text-muted">价格待定</span>
              <span v-if="item.similarity !== undefined" class="px-2 py-1 rounded-full text-xs bg-primary-100 text-primary-700">
                {{ Math.round(item.similarity * 100) }}% 相似
              </span>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <span v-if="item.category" class="text-xs text-text-muted">{{ item.category }}</span>
              <span v-if="item.brand" class="text-xs text-text-muted">/ {{ item.brand }}</span>
              <span v-if="item.model" class="text-xs text-text-muted">/ {{ item.model }}</span>
              <span v-if="item.username" class="text-xs text-text-muted ml-auto">{{ item.username }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 无结果状态 -->
    <div v-else-if="hasSearched && !searching" class="glass-card p-12 text-center">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-warning-400/30 to-accent-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-surface-secondary flex items-center justify-center">
          <span class="text-5xl">🤔</span>
        </div>
      </div>
      <p class="text-text-secondary font-medium text-lg">全网暂无同款</p>
      <p class="text-text-muted text-sm mt-2">你是第一个发现它的人！</p>
      <router-link to="/" class="mt-5 inline-block btn-primary">
        🚀 去发布赚取第一桶金
      </router-link>
    </div>

    <!-- 加载状态 -->
    <div v-if="searching" class="glass-card p-8 text-center">
      <div class="loading-spinner mx-auto mb-4" style="width: 40px; height: 40px; border-width: 3px;" />
      <p class="text-text-muted">正在搜索商品...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  searchByImage,
  searchByText,
  searchSemantic,
  searchByFilter,
  getCategoriesAndBrands,
  getSearchAvailableModels
} from '../api/index.js'

const router = useRouter()
const route = useRoute()

// ✅ R7: 从 URL 参数读取搜索模式
const searchMode = ref(route.query.mode === 'text' ? 'text' : route.query.mode === 'image' ? 'image' : 'image')
const searchImage = ref(null)
const previewUrl = ref('')
const isDragging = ref(false)
const searching = ref(false)
const hasSearched = ref(false)
const searchResults = ref([])

// 以文搜图
const searchText = ref('')
const filterCategory = ref('')
const topK = ref(10)
const categories = ref(['手机', '笔记本', '平板', '外设', '耳机', '手表', '相机', '游戏机'])

// 按类别型号搜索
const filterForm = ref({ category: '', brand: '', model: '' })
const filterCategories = ref([])
const filterBrands = ref([])
const filterSuggestModels = ref([])
const filterTotal = ref(0)
const filterPage = ref(1)
const filterTotalPages = ref(0)

const fileInput = ref(null)

// 级联：品类变化 → 加载品牌
async function onCategoryChange() {
  filterForm.value.brand = ''
  filterForm.value.model = ''
  filterSuggestModels.value = []

  if (filterForm.value.category) {
    try {
      const data = await getCategoriesAndBrands(filterForm.value.category)
      filterBrands.value = data.brands || []

      // 同时加载该品类的常见型号
      const modelData = await getSearchAvailableModels(filterForm.value.category, null)
      filterSuggestModels.value = modelData.models || []
    } catch (e) {
      console.error('加载品牌失败:', e)
      filterBrands.value = []
    }
  } else {
    filterBrands.value = []
  }
}

// 级联：品牌变化 → 加载型号
async function onBrandChange() {
  filterForm.value.model = ''

  if (filterForm.value.category) {
    try {
      const modelData = await getSearchAvailableModels(
        filterForm.value.category,
        filterForm.value.brand || null
      )
      filterSuggestModels.value = modelData.models || []
    } catch (e) {
      console.error('加载型号失败:', e)
      filterSuggestModels.value = []
    }
  }
}

// 型号建议（已加载的基础上本地过滤）
const filteredModelSuggestions = computed(() => {
  if (!filterForm.value.model)
    return []
  const q = filterForm.value.model.toLowerCase()
  return filterSuggestModels.value.filter(m =>
    m.model.toLowerCase().includes(q)
  )
})

function selectModelSuggestion(m) {
  filterForm.value.model = m.model
}

// 切换到类别型号搜索模式
async function switchToFilterMode() {
  searchMode.value = 'filter'
  // 加载品类列表
  if (filterCategories.value.length === 0) {
    try {
      const data = await getCategoriesAndBrands()
      filterCategories.value = data.categories || []
    } catch (e) {
      console.error('加载品类失败:', e)
    }
  }
}

// 按类别型号搜索
async function performFilterSearch() {
  if (!filterForm.value.category) return

  searching.value = true
  hasSearched.value = true

  try {
    const data = await searchByFilter({
      category: filterForm.value.category || undefined,
      brand: filterForm.value.brand || undefined,
      model: filterForm.value.model || undefined,
      page: filterPage.value,
      pageSize: 20,
    })

    searchResults.value = data.results || []
    filterTotal.value = data.total || 0
    filterTotalPages.value = data.total_pages || 0
  } catch (error) {
    console.error('类别搜索失败:', error)
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function changeFilterPage(page) {
  filterPage.value = page
  performFilterSearch()
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function clearFilterSearch() {
  filterForm.value = { category: '', brand: '', model: '' }
  filterBrands.value = []
  filterSuggestModels.value = []
  filterPage.value = 1
  hasSearched.value = false
  searchResults.value = []
}

// ============================================================
// 原有功能
// ============================================================

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    setSearchImage(file)
  }
}

function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) {
    setSearchImage(file)
  }
}

const _reader = ref(null)  // ✅ 追踪 FileReader 以便清理

function setSearchImage(file) {
  // ✅ 修复：取消旧 reader 防止内存泄漏
  if (_reader.value) {
    _reader.value.abort?.()
    _reader.value = null
  }
  searchImage.value = file
  const reader = new FileReader()
  _reader.value = reader
  reader.onload = (e) => {
    previewUrl.value = e.target.result
    _reader.value = null
  }
  reader.onerror = () => { _reader.value = null }
  reader.readAsDataURL(file)
}

function clearSearchImage() {
  searchImage.value = null
  previewUrl.value = ''
  hasSearched.value = false
  searchResults.value = []
}

async function performImageSearch() {
  if (!searchImage.value) return

  searching.value = true
  hasSearched.value = true

  try {
    const formData = new FormData()
    formData.append('image', searchImage.value)
    formData.append('top_k', topK.value)
    if (filterCategory.value) {
      formData.append('filter_category', filterCategory.value)
    }

    const data = await searchByImage(formData)
    searchResults.value = data.results || []
  } catch (error) {
    console.error('图片搜索失败:', error)
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

async function performTextSearch() {
  if (!searchText.value.trim()) return

  searching.value = true
  hasSearched.value = true

  try {
    // ✅ 优先用 DeepSeek 语义搜索（支持 电风扇→风扇 等模糊匹配）
    const data = await searchSemantic(searchText.value, parseInt(topK.value))
    searchResults.value = data.results || []
  } catch (error) {
    console.error('文本搜索失败:', error)
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function clearResults() {
  hasSearched.value = false
  searchResults.value = []
  searchText.value = ''
  filterTotal.value = 0
  filterPage.value = 1
  filterTotalPages.value = 0
}

function goToMarket() {
  router.push('/market')
}

function formatPrice(value) {
  if (!value || isNaN(value)) return '0'
  return Math.round(value).toLocaleString()
}

function handleImageError(event) {
  event.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect fill="%23f5f5f5" width="400" height="300"/><text x="50%" y="50%" text-anchor="middle" fill="%23999" font-size="14">图片加载失败</text></svg>'
}

onMounted(() => {
  // 预加载品类列表
  getCategoriesAndBrands().then(data => {
    filterCategories.value = data.categories || []
  }).catch(() => {})
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
