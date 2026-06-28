<template>
  <div class="glass-card overflow-hidden">
    <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border">
      <div class="flex items-center gap-3">
        <div class="relative">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-400 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-primary-500/30">🤖</div>
          <div class="absolute -inset-1 bg-gradient-to-br from-primary-400/40 to-primary-300/40 rounded-xl blur-lg opacity-40 -z-10"></div>
        </div>
        <div>
          <h3 class="font-semibold text-text-primary">AI 文案生成</h3>
          <p class="text-xs text-text-muted">智能生成专业带货文案</p>
        </div>
      </div>
    </div>

    <div class="p-6">
      <div v-if="!text && !active" class="text-center py-12">
        <div class="relative inline-block mb-4">
          <div class="absolute -inset-4 bg-gradient-to-br from-primary-400/30 to-accent-400/30 rounded-2xl blur-lg -z-10"></div>
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
            <span class="text-4xl">✨</span>
          </div>
        </div>
        <p class="text-sm text-text-muted">点击上方 "确认并生成文案" 按钮开始</p>
      </div>

      <div v-else-if="active && !text" class="flex items-center justify-center gap-3 py-8">
        <span class="flex gap-1.5">
          <span class="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay:0s" />
          <span class="w-2.5 h-2.5 bg-primary-300 rounded-full animate-bounce" style="animation-delay:0.15s" />
          <span class="w-2.5 h-2.5 bg-primary-200 rounded-full animate-bounce" style="animation-delay:0.3s" />
        </span>
        <span class="text-sm text-text-muted">AI 正在为您撰写文案…</span>
      </div>

      <div v-if="text" class="relative">
        <div class="prose prose-sm max-w-none text-text-primary leading-relaxed whitespace-pre-wrap min-h-[120px] p-4 bg-surface-secondary rounded-xl"
          :class="{ 'cursor-blink': active }">
          {{ text }}
        </div>

        <div v-if="done" class="mt-6 pt-5 border-t border-border flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <div class="relative">
              <div class="w-5 h-5 rounded-full bg-accent-100 flex items-center justify-center text-accent-600 text-xs font-bold">✓</div>
              <div class="absolute -inset-1 bg-accent-400/30 rounded-full blur opacity-40 -z-10"></div>
            </div>
            <span class="text-sm text-accent-700 font-medium">生成完成</span>
          </div>
          <div class="flex gap-2">
            <button
              class="px-5 py-2.5 rounded-xl text-sm font-medium border border-primary-200 text-primary-600 hover:bg-primary-50 hover:border-primary-300 transition-all focus:ring-2 focus:ring-primary-500 focus:outline-none"
              @click="copyText"
              aria-label="复制文案"
            >
              {{ copied ? '✓ 已复制' : '📋 复制文案' }}
            </button>
            <button
              class="px-5 py-2.5 rounded-xl text-sm font-medium text-white gradient-accent shadow-md shadow-accent-500/30 hover:shadow-lg hover:shadow-accent-500/40 transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:ring-2 focus:ring-accent-400 focus:outline-none"
              @click="$emit('save')"
              aria-label="保存到记录"
            >
              💾 保存到记录
            </button>
          </div>
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