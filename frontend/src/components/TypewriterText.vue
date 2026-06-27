<template>
  <div class="bg-primary-800/60 backdrop-blur-xl rounded-2xl shadow-xl border border-primary-700/50 p-6">
    <div v-if="!text && !active" class="text-center py-12">
      <div class="relative inline-block mb-4">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-500/30 to-primary-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-700/80 to-primary-600/80 flex items-center justify-center">
          <span class="text-4xl">✨</span>
        </div>
      </div>
      <p class="text-sm text-primary-400">点击上方 "确认并生成文案" 按钮开始</p>
    </div>

    <div v-else-if="active && !text" class="flex items-center justify-center gap-3 py-8">
      <span class="flex gap-1.5">
        <span class="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay:0s" />
        <span class="w-2.5 h-2.5 bg-primary-300 rounded-full animate-bounce" style="animation-delay:0.15s" />
        <span class="w-2.5 h-2.5 bg-primary-200 rounded-full animate-bounce" style="animation-delay:0.3s" />
      </span>
      <span class="text-sm text-primary-400">AI 正在为您撰写文案…</span>
    </div>

    <div v-if="text" class="relative">
      <div class="prose prose-sm max-w-none text-primary-100 leading-relaxed whitespace-pre-wrap min-h-[120px]"
        :class="{ 'cursor-blink': active }">
        {{ text }}
      </div>

      <div v-if="done" class="mt-6 pt-5 border-t border-primary-700/50 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <div class="relative">
            <div class="w-5 h-5 rounded-full bg-success-900/50 flex items-center justify-center text-success-400 text-xs font-bold">✓</div>
            <div class="absolute -inset-1 bg-success-500/30 rounded-full blur opacity-40 -z-10"></div>
          </div>
          <span class="text-sm text-success-300 font-medium">生成完成</span>
        </div>
        <div class="flex gap-2">
          <button
            class="px-5 py-2.5 rounded-xl text-sm font-medium border border-primary-600 text-primary-200 hover:bg-primary-700/50 hover:border-primary-500 transition-all focus:ring-2 focus:ring-primary-500 focus:outline-none"
            @click="copyText"
            aria-label="复制文案"
          >
            {{ copied ? '✓ 已复制' : '📋 复制文案' }}
          </button>
          <button
            class="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-success-600 via-success-500 to-success-400 hover:from-success-500 hover:via-success-400 hover:to-success-300 shadow-md shadow-success-600/30 hover:shadow-lg hover:shadow-success-600/40 transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:ring-2 focus:ring-success-400 focus:outline-none"
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
  }
}
</script>