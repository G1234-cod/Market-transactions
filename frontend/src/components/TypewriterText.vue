<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
    <!-- 空状态 -->
    <div v-if="!text && !active" class="text-center py-8 text-gray-400">
      <span class="text-4xl block mb-3">✨</span>
      <p class="text-sm">点击上方 "确认并生成文案" 按钮开始</p>
    </div>

    <!-- 生成中 -->
    <div v-else-if="active && !text" class="flex items-center gap-3 text-gray-400 py-4">
      <span class="flex gap-1">
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay:0s" />
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay:0.15s" />
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay:0.3s" />
      </span>
      <span class="text-sm">AI 正在为您撰写文案...</span>
    </div>

    <!-- 有内容 -->
    <div v-if="text" class="relative">
      <div class="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap"
        :class="{ 'cursor-blink': active }">
        {{ text }}
      </div>

      <!-- 生成完成工具栏 -->
      <div v-if="done" class="mt-6 pt-5 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <span class="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 text-xs">✓</span>
          <span class="text-sm text-emerald-700 font-medium">生成完成</span>
        </div>
        <div class="flex gap-2">
          <button
            class="px-4 py-2 rounded-xl text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            @click="copyText"
          >
            {{ copied ? '✓ 已复制' : '📋 复制文案' }}
          </button>
          <button
            class="px-4 py-2 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 shadow-md shadow-emerald-500/20 transition-all"
            @click="$emit('save')"
          >
            💾 保存到记录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  text: { type: String, default: '' },
  active: { type: Boolean, default: false },
  done: { type: Boolean, default: false },
})
defineEmits(['save'])

const copied = ref(false)

async function copyText() {
  try {
    await navigator.clipboard.writeText(document.querySelector('.prose')?.innerText || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // fallback
  }
}
</script>
