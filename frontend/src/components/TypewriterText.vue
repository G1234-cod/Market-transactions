<template>
  <div class="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-white/50 p-6">
    <div v-if="!text && !active" class="text-center py-12 text-gray-400">
      <div class="relative inline-block mb-4">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-200/30 to-accent-200/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center">
          <span class="text-4xl">✨</span>
        </div>
      </div>
      <p class="text-sm">点击上方 "确认并生成文案" 按钮开始</p>
    </div>

    <div v-else-if="active && !text" class="flex items-center justify-center gap-3 text-gray-400 py-8">
      <span class="flex gap-1.5">
        <span class="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay:0s" />
        <span class="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style="animation-delay:0.15s" />
        <span class="w-2.5 h-2.5 bg-accent-400 rounded-full animate-bounce" style="animation-delay:0.3s" />
      </span>
      <span class="text-sm">AI 正在为您撰写文案…</span>
    </div>

    <div v-if="text" class="relative">
      <div class="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap min-h-[120px]"
        :class="{ 'cursor-blink': active }">
        {{ text }}
      </div>

      <div v-if="done" class="mt-6 pt-5 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <div class="relative">
            <div class="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 text-xs font-bold">✓</div>
            <div class="absolute -inset-1 bg-emerald-200 rounded-full blur opacity-30 -z-10"></div>
          </div>
          <span class="text-sm text-emerald-700 font-medium">生成完成</span>
        </div>
        <div class="flex gap-2">
          <button
            class="px-5 py-2.5 rounded-xl text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-all focus:ring-2 focus:ring-gray-400 focus:outline-none"
            @click="copyText"
            aria-label="复制文案"
          >
            {{ copied ? '✓ 已复制' : '📋 复制文案' }}
          </button>
          <button
            class="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-500 hover:from-emerald-600 hover:via-emerald-700 hover:to-teal-600 shadow-md shadow-emerald-500/20 hover:shadow-lg hover:shadow-emerald-500/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:ring-2 focus:ring-emerald-400 focus:outline-none"
            @click="$emit('save')"
            aria-label="保存到记录"
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
