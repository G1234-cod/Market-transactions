<template>
  <div
    role="button"
    tabindex="0"
    class="border-2 border-dashed rounded-2xl px-8 py-14 text-center cursor-pointer transition-all duration-300 select-none relative overflow-hidden"
    :class="dragOver
      ? 'border-primary-400 bg-primary-50/50 scale-[1.01] shadow-xl shadow-primary-100'
      : 'border-gray-200 hover:border-primary-300 hover:bg-primary-50/20'"
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
        <p class="text-gray-600 font-medium">拖拽图片到此处，或点击上传</p>
        <p class="text-xs text-gray-400">支持 JPG / PNG，单张最大 10MB，自动压缩</p>
      </div>
    </div>

    <div v-else class="relative inline-block group">
      <div class="relative">
        <img 
          :src="previewUrl" 
          class="max-h-80 max-w-full rounded-xl shadow-xl object-contain bg-white" 
          alt="上传预览"
        />
        <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 rounded-xl transition-colors duration-300" />
      </div>
      <button
        class="absolute -top-3 -right-3 w-8 h-8 bg-white border border-gray-200 text-gray-500 rounded-full text-sm flex items-center justify-center hover:bg-red-50 hover:text-red-500 hover:border-red-200 shadow-md transition-all hover:scale-110 focus:ring-2 focus:ring-red-400 focus:outline-none"
        @click.stop="clearImage"
        aria-label="删除图片"
      >×</button>
      <div v-if="compressing" class="mt-4 text-xs text-primary-500 flex items-center justify-center gap-2">
        <span class="w-4 h-4 border-2 border-primary-300 border-t-primary-500 rounded-full animate-spin" />
        压缩中…
      </div>
      <p v-else class="mt-4 text-xs text-gray-400">点击重新选择</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, watch } from 'vue'

const props = defineProps({ modelValue: { type: File, default: null } })
const emit = defineEmits(['update:modelValue'])

const dragOver = ref(false)
const compressing = ref(false)
const inputFile = ref(null)

// ✅ 存储 blob URL 以便释放
let currentBlobUrl = null

// ✅ 释放当前 blob URL
function revokeCurrentBlobUrl() {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl)
    currentBlobUrl = null
  }
}

// ✅ 创建 blob URL（自动释放旧的）
function createBlobUrl(file) {
  revokeCurrentBlobUrl()
  if (file) {
    currentBlobUrl = URL.createObjectURL(file)
    return currentBlobUrl
  }
  return ''
}

const previewUrl = computed(() => {
  if (inputFile.value) {
    return createBlobUrl(inputFile.value)
  }
  revokeCurrentBlobUrl()
  return ''
})

async function compressImage(file) {
  return new Promise((resolve) => {
    const img = new Image()
    // ✅ 临时 blob URL 用于加载图片
    const tempUrl = URL.createObjectURL(file)
    img.onload = () => {
      let { width, height } = img
      const max = 1920
      if (width > max || height > max) {
        if (width > height) { height = (height * max) / width; width = max }
        else { width = (width * max) / height; height = max }
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, width, height)
      canvas.toBlob((blob) => {
        // ✅ 释放临时 blob URL
        URL.revokeObjectURL(tempUrl)
        resolve(new File([blob], file.name, { type: 'image/jpeg' }))
      }, 'image/jpeg', 0.8)
    }
    img.onerror = () => {
      // ✅ 出错时也释放临时 blob URL
      URL.revokeObjectURL(tempUrl)
      resolve(file)
    }
    img.src = tempUrl
  })
}

async function processFile(file) {
  compressing.value = true
  const compressed = await compressImage(file)
  compressing.value = false
  inputFile.value = compressed
  emit('update:modelValue', compressed)
}

function handleDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) processFile(file)
}

function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) processFile(file)
  // ✅ 重置 input 以便重复选择同一文件
  e.target.value = ''
}

function clearImage() {
  // ✅ 释放当前 blob URL
  revokeCurrentBlobUrl()
  inputFile.value = null
  emit('update:modelValue', null)
}

// ✅ 组件卸载时释放 blob URL
onBeforeUnmount(() => {
  revokeCurrentBlobUrl()
})

// ✅ 监听 props 变化，如果外部清空了，同步清理
watch(() => props.modelValue, (newVal) => {
  if (newVal === null && inputFile.value !== null) {
    revokeCurrentBlobUrl()
    inputFile.value = null
  }
})
</script>