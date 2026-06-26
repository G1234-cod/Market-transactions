<template>
  <div class="bg-white/80 backdrop-blur-md rounded-xl border border-white/50 p-5 flex gap-5 hover:shadow-lg hover:border-primary-200 transition-all duration-300 group">
    <div class="relative w-24 h-24 rounded-xl bg-gradient-to-br from-primary-50 to-accent-50 flex-shrink-0 flex items-center justify-center overflow-hidden">
      <img 
        v-if="item.original_image_url" 
        :src="item.original_image_url" 
        class="w-full h-full object-cover"
        alt="商品图片"
      />
      <span v-else class="text-3xl text-primary-300">📷</span>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-3">
        <h4 class="font-semibold text-gray-800 truncate group-hover:text-primary-600 transition-colors">{{ item.ai_generated_title || '未命名商品' }}</h4>
        <span class="px-3 py-1 rounded-full text-xs font-medium flex-shrink-0"
          :class="statusBadge(item.status)">{{ statusLabel(item.status) }}</span>
      </div>
      <p class="text-sm text-gray-500 mt-2 line-clamp-2 leading-relaxed">{{ item.ai_generated_desc }}</p>
      <div class="flex items-center gap-4 mt-3 text-xs">
        <span v-if="item.suggested_price" class="text-red-500 font-semibold font-variant-numeric">¥{{ item.suggested_price.toLocaleString() }}</span>
        <span class="text-gray-400">{{ formatDate(item.created_at) }}</span>
        <button v-if="item.status === 'published'"
          class="ml-auto px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-all text-xs font-medium focus:ring-2 focus:ring-red-400 focus:outline-none"
          @click.stop="$emit('delist', item.id)"
          aria-label="下架商品">下架</button>
        <button v-if="item.status === 'draft'"
          class="ml-auto px-3 py-1.5 rounded-lg border border-primary-200 text-primary-600 hover:text-primary-700 hover:border-primary-300 hover:bg-primary-50 transition-all text-xs font-medium focus:ring-2 focus:ring-primary-400 focus:outline-none"
          @click.stop="$emit('publish', item.id)"
          aria-label="发布商品">发布</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ item: { type: Object, required: true } })
defineEmits(['delist', 'publish'])

function statusBadge(status) {
  return status === 'published' ? 'bg-blue-100 text-blue-700'
    : status === 'delisted' ? 'bg-gray-100 text-gray-500'
    : 'bg-amber-100 text-amber-700'
}
function statusLabel(status) {
  return { published: '已发布', delisted: '已下架', draft: '草稿' }[status] || status
}
function formatDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleDateString('zh-CN')
}
</script>
