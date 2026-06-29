<template>
  <div
    role="button"
    tabindex="0"
    class="border-2 border-dashed rounded-xl px-8 py-14 text-center cursor-pointer transition-all duration-300 select-none relative overflow-hidden"
    :class="dragOver
      ? 'border-primary-400 bg-primary-50/50 scale-[1.01] shadow-lg shadow-primary-100'
      : 'border-border hover:border-primary-300 hover:bg-primary-50/20'"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="handleDrop"
    @click="$refs.input.click()"
    @keydown.enter="$refs.input.click()"
    aria-label="上传图片"
  >
    <input 
      ref="input" 
      type="file" 
      accept="image/*" 
      class="hidden" 
      @change="handleFileChange"
      aria-hidden="true"
    />

    <div v-if="dragOver" class="absolute inset-0 bg-gradient-to-r from-primary-100/30 to-accent-100/30 pointer-events-none"></div>

    <div v-if="!previewUrl" class="space-y-4">
      <div class="relative inline-block">
        <div class="absolute -inset-4 bg-gradient-to-br from-primary-200/40 to-accent-200/40 rounded-2xl blur-lg -z-10"></div>
        <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center shadow-sm">
          <span class="text-4xl">📷</span>
        </div>
      </div>
      <div class="space-y-1">
        <p class="text-text-secondary font-medium">拖拽图片到此处，或点击上传</p>
        <p class="text-xs text-text-muted">支持 JPG / PNG，单张最大 10MB，自动压缩</p>
      </div>
    </div>

    <div v-if="!previewUrl" class="space-y-4 transition-all duration-300" :class="dragOver ? 'opacity-0' : 'opacity-100'">
      <div class="relative inline-block">
        <div class="absolute -inset-6 bg-gradient-to-br from-primary-500/30 to-purple-500/30 rounded-2xl blur-lg -z-10 group-hover:animate-pulse-glow"></div>
        <div class="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-800/90 to-primary-700/90 flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform duration-300">
          <span class="text-5xl animate-float">📷</span>
        </div>
      </div>
      <div class="space-y-2">
        <p class="text-primary-200 font-semibold text-base">拖拽图片到此处，或点击上传</p>
        <p class="text-xs text-primary-400">支持 JPG / PNG，单张最大 10MB，自动压缩</p>
      </div>
      <div class="flex justify-center gap-4 text-xs text-primary-500">
        <span class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span> 安全加密
        </span>
        <span class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span> AI 识别
        </span>
      </div>
    </div>

    <div v-else class="relative inline-block group/image">
      <div class="relative overflow-hidden rounded-2xl">
        <img 
          :src="previewUrl" 
          class="max-h-80 max-w-full rounded-xl shadow-lg object-contain bg-white" 
          alt="上传预览"
        />
        <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 rounded-xl transition-colors duration-300" />
      </div>
      <button
        class="absolute -top-3 -right-3 w-8 h-8 bg-white border border-border text-text-muted rounded-full text-sm flex items-center justify-center hover:bg-red-50 hover:text-red-500 hover:border-red-200 shadow-md transition-all hover:scale-110 focus:ring-2 focus:ring-red-400 focus:outline-none"
        @click.stop="clearImage"
        aria-label="删除图片"
      >×</button>
      <div v-if="compressing" class="mt-4 text-xs text-primary-600 flex items-center justify-center gap-2">
        <span class="w-4 h-4 border-2 border-primary-300 border-t-primary-500 rounded-full animate-spin" />
        压缩中…
      </div>
      <p v-else class="mt-4 text-xs text-text-muted">点击重新选择</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ modelValue: { type: File, default: null } })
const emit = defineEmits(['update:modelValue'])

const dragOver = ref(false)
const previewUrl = ref('')
const compressing = ref(false)

function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (file) processFile(file)
}

function handleDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) processFile(file)
  dragOver.value = false
}

async function processFile(file) {
  if (!file.type.startsWith('image/')) return

  compressing.value = true

  // ✅ 修复：释放旧的 Object URL 防止内存泄漏
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }

  try {
    const compressed = await compressImage(file)
    previewUrl.value = URL.createObjectURL(compressed)
    emit('update:modelValue', compressed)
  } catch (err) {
    console.warn('图片压缩失败，使用原始文件:', err)
    previewUrl.value = URL.createObjectURL(file)
    emit('update:modelValue', file)
  } finally {
    compressing.value = false
  }
}

function compressImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        let width = img.width
        let height = img.height
        const maxSize = 1920
        
        if (width > maxSize || height > maxSize) {
          if (width > height) { height = (height / width) * maxSize; width = maxSize }
          else { width = (width / height) * maxSize; height = maxSize }
        }
        
        canvas.width = width
        canvas.height = height
        ctx.drawImage(img, 0, 0, width, height)
        
        canvas.toBlob((blob) => {
          if (blob) resolve(new File([blob], file.name, { type: 'image/jpeg' }))
          else reject(new Error('Compression failed'))
        }, 'image/jpeg', 0.85)
      }
      img.onerror = reject
      img.src = e.target.result
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function clearImage() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  emit('update:modelValue', null)
}

watch(() => props.modelValue, (file) => {
  if (file && !previewUrl.value) {
    previewUrl.value = URL.createObjectURL(file)
  } else if (!file && previewUrl.value) {
    // ✅ 修复：prop 置空时清预览
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
})
</script>
