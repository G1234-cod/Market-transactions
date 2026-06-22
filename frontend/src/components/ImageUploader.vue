<template>
  <div
    class="border-2 border-dashed rounded-2xl px-8 py-12 text-center cursor-pointer transition-all duration-200 select-none"
    :class="dragOver
      ? 'border-blue-400 bg-blue-50/50 scale-[1.01] shadow-lg shadow-blue-100'
      : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/20'"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="handleDrop"
    @click="$refs.input.click()"
  >
    <input ref="input" type="file" accept="image/*" class="hidden" @change="handleFileChange" />

    <!-- 空状态 -->
    <div v-if="!previewUrl" class="space-y-3">
      <div class="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center">
        <span class="text-3xl">📷</span>
      </div>
      <p class="text-gray-600 font-medium">拖拽图片到此处，或点击上传</p>
      <p class="text-xs text-gray-400">支持 JPG / PNG，单张最大 10MB，自动压缩</p>
    </div>

    <!-- 已上传预览 -->
    <div v-else class="relative inline-block group">
      <img :src="previewUrl" class="max-h-72 max-w-full rounded-xl shadow-lg object-contain" />
      <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 rounded-xl transition-colors" />
      <button
        class="absolute -top-2 -right-2 w-7 h-7 bg-white border border-gray-200 text-gray-500 rounded-full text-sm leading-7 hover:bg-red-50 hover:text-red-500 hover:border-red-200 shadow-sm transition-all"
        @click.stop="clearImage"
      >×</button>
      <p v-if="compressing" class="mt-3 text-xs text-blue-500 flex items-center justify-center gap-1.5">
        <span class="w-3 h-3 border-2 border-blue-300 border-t-blue-500 rounded-full animate-spin" />
        压缩中...
      </p>
      <p v-else class="mt-3 text-xs text-gray-400">点击重新选择</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({ modelValue: { type: File, default: null } })
const emit = defineEmits(['update:modelValue'])

const dragOver = ref(false)
const compressing = ref(false)
const inputFile = ref(null)

const previewUrl = computed(() => {
  if (inputFile.value) return URL.createObjectURL(inputFile.value)
  return ''
})

async function compressImage(file) {
  return new Promise((resolve) => {
    const img = new Image()
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
        resolve(new File([blob], file.name, { type: 'image/jpeg' }))
      }, 'image/jpeg', 0.8)
    }
    img.src = URL.createObjectURL(file)
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
}

function clearImage() {
  inputFile.value = null
  emit('update:modelValue', null)
}
</script>
