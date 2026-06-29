<template>
  <div class="glass-card p-5 flex gap-5 hover:shadow-card-hover transition-all duration-300 group">
    <div class="relative w-24 h-24 rounded-xl bg-gradient-to-br from-surface-secondary to-surface-tertiary flex-shrink-0 flex items-center justify-center overflow-hidden">
      <img
        v-if="item.original_image_url"
        :src="item.original_image_url"
        class="w-full h-full object-cover"
        alt="商品图片"
      />
      <span v-else class="text-3xl text-text-muted">📷</span>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-3">
        <h4 class="font-semibold text-text-primary truncate group-hover:text-primary-600 transition-colors">
          {{ item.ai_generated_title || '未命名商品' }}
        </h4>
        <span class="pill-button flex-shrink-0"
          :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
      </div>
      <p class="text-sm text-text-muted mt-2 line-clamp-2 leading-relaxed">{{ item.ai_generated_desc }}</p>

      <!-- 商品分类信息 -->
      <div v-if="item.category || item.brand || item.model" class="flex items-center gap-2 mt-2 text-xs text-text-muted">
        <span v-if="item.category">{{ item.category }}</span>
        <span v-if="item.brand">/ {{ item.brand }}</span>
        <span v-if="item.model">/ {{ item.model }}</span>
        <span v-if="item.condition" class="text-text-light">· {{ item.condition }}</span>
      </div>

      <div class="flex items-center gap-4 mt-3 text-xs">
        <span v-if="item.suggested_price" class="text-danger-600 font-semibold font-variant-numeric">¥{{ formatPrice(item.suggested_price) }}</span>
        <span class="text-text-muted">{{ formatDate(item.created_at) }}</span>

        <!-- 查看次数 -->
        <span v-if="item.views > 0" class="text-text-muted flex items-center gap-1">
          <span>👁</span> {{ item.views }}
        </span>

        <div class="ml-auto flex gap-2">
          <!-- 重新评估按钮（支持已发布和草稿状态） -->
          <button
            v-if="item.status === 'published' || item.status === 'draft'"
            class="btn-warning-sm text-xs flex items-center gap-1"
            :disabled="reevaluating === item.id"
            @click.stop="handleReevaluate(item.id)"
            title="使用DeepSeek重新评估商品信息和价格"
          >
            <span v-if="reevaluating === item.id" class="loading-spinner" style="width:12px;height:12px;border-width:2px" />
            {{ reevaluating === item.id ? '评估中...' : '🔄 重新评估' }}
          </button>

          <button v-if="item.status === 'published'"
            class="btn-danger-sm"
            @click.stop="$emit('delist', item.id)"
            aria-label="下架商品">下架</button>
          <button v-if="item.status === 'published'"
            class="btn-primary-sm text-xs"
            @click.stop="$emit('markSold', item.id)"
            aria-label="标记已售出">已售出</button>
          <button v-if="item.status === 'draft'"
            class="btn-primary-sm text-xs"
            @click.stop="$emit('publish', item.id)"
            aria-label="发布商品">发布</button>
          <button v-if="item.status === 'delisted'"
            class="btn-primary-sm text-xs"
            @click.stop="$emit('publish', item.id)"
            aria-label="重新发布">重新发布</button>
        </div>
      </div>

      <!-- 重新评估结果提示 -->
      <div v-if="reevaluateResult && reevaluateItemId === item.id"
        class="mt-3 bg-accent-50 border border-accent-200 rounded-xl p-3">
        <p class="text-xs text-accent-700 font-medium mb-1">✅ 重新评估完成</p>
        <p class="text-xs text-text-secondary">新标题：{{ reevaluateResult.title }}</p>
        <p v-if="reevaluateResult.suggested_price" class="text-xs text-accent-600 font-semibold mt-1">
          新建议价：¥{{ formatPrice(reevaluateResult.suggested_price) }}
        </p>
        <p class="text-xs text-text-muted mt-1">请刷新页面查看更新</p>
      </div>

      <!-- 错误提示 -->
      <div v-if="reevaluateError && reevaluateItemId === item.id"
        class="mt-3 bg-danger-50 border border-danger-200 rounded-xl p-3">
        <p class="text-xs text-danger-600">❌ 重新评估失败：{{ reevaluateError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { reevaluateItem } from '../api/index.js'

const props = defineProps({ item: { type: Object, required: true } })
const emit = defineEmits(['delist', 'publish', 'markSold', 'reevaluated'])

const toast = inject('toast', () => {})

const reevaluating = ref(null)
const reevaluateResult = ref(null)
const reevaluateItemId = ref(null)
const reevaluateError = ref('')

async function handleReevaluate(itemId) {
  reevaluating.value = itemId
  reevaluateResult.value = null
  reevaluateItemId.value = null
  reevaluateError.value = ''

  try {
    const data = await reevaluateItem(itemId)
    if (data.success) {
      reevaluateResult.value = data.result
      reevaluateItemId.value = itemId
      toast('重新评估完成！', 'success')
      // ✅ 修复：emit 事件让父组件刷新数据，而非整页重载
      emit('reevaluated', { itemId, result: data.result })
    } else {
      reevaluateError.value = data.message || '评估失败'
      toast('重新评估失败', 'error')
    }
  } catch (e) {
    reevaluateError.value = e.message || '请求失败'
    toast('重新评估失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    reevaluating.value = null
  }
}

function statusClass(status) {
  return status === 'published' ? 'pill-button-active bg-accent-100 text-accent-700'
    : status === 'delisted' ? 'pill-button-inactive bg-gray-100 text-gray-600'
    : status === 'sold' ? 'pill-button-active bg-success-100 text-success-700'
    : 'pill-button-inactive bg-warning-100 text-warning-700'
}
function statusLabel(status) {
  return { published: '已发布', delisted: '已下架', draft: '草稿', sold: '已售出' }[status] || status
}
function formatDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleDateString('zh-CN')
}
function formatPrice(value) {
  if (!value || isNaN(value)) return '0'
  return Math.round(value).toLocaleString()
}
</script>
