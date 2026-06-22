<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4 flex gap-4 hover:shadow-md hover:border-gray-200 transition-all group">
    <!-- 图片占位 -->
    <div class="w-20 h-20 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 flex-shrink-0 flex items-center justify-center overflow-hidden">
      <img v-if="item.original_image_url" :src="item.original_image_url" class="w-full h-full object-cover" />
      <span v-else class="text-2xl text-blue-300">📷</span>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-2">
        <h4 class="font-semibold text-gray-800 truncate group-hover:text-blue-600 transition-colors">{{ item.ai_generated_title || '未命名商品' }}</h4>
        <span class="px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0"
          :class="statusBadge(item.status)">{{ statusLabel(item.status) }}</span>
      </div>
      <p class="text-sm text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">{{ item.ai_generated_desc }}</p>
      <div class="flex items-center gap-3 mt-2.5 text-xs">
        <span v-if="item.suggested_price" class="text-red-500 font-semibold">¥{{ item.suggested_price }}</span>
        <span class="text-gray-400">{{ formatDate(item.created_at) }}</span>
        <!-- 操作按钮 -->
        <button v-if="item.status === 'published'"
          class="ml-auto px-2.5 py-1 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-all text-[11px]"
          @click.stop="$emit('delist', item.id)">下架</button>
        <button v-if="item.status === 'draft'"
          class="ml-auto px-2.5 py-1 rounded-lg border border-gray-200 text-gray-400 hover:text-blue-500 hover:border-blue-200 hover:bg-blue-50 transition-all text-[11px]"
          @click.stop="$emit('publish', item.id)">发布</button>
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
