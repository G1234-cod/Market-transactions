<template>
  <div class="space-y-8">
    <div class="text-center space-y-2">
      <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent">发布二手商品</h1>
      <p class="text-gray-400 text-sm">上传物品照片，AI 自动识别并生成吸睛带货文案</p>
    </div>

    <!-- 步骤指示器 -->
    <div class="flex justify-center items-center gap-0">
      <template v-for="(s, i) in steps" :key="s.label">
        <div class="flex flex-col items-center gap-1.5 cursor-pointer" @click="step >= i && (step = i)">
          <div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300"
            :class="step >= i ? 'bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-lg shadow-blue-500/30 scale-110' : 'bg-gray-100 text-gray-400'">
            <span v-if="step > i">✓</span><span v-else>{{ i + 1 }}</span>
          </div>
          <span class="text-xs font-medium transition-colors" :class="step >= i ? 'text-blue-600' : 'text-gray-400'">{{ s.label }}</span>
        </div>
        <div v-if="i < steps.length - 1" class="w-12 sm:w-20 h-0.5 mx-1 rounded-full transition-colors duration-500"
          :class="step > i ? 'bg-blue-500' : 'bg-gray-200'" />
      </template>
    </div>

    <transition name="step" mode="out-in">
      <!-- Step 0: 上传 -->
      <div v-if="step === 0" key="upload" class="space-y-4">
        <ImageUploader v-model="imageFile" />
        <button class="w-full py-3.5 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :class="imageFile ? 'bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40' : 'bg-gray-300'"
          :disabled="!imageFile || extracting" @click="doExtract">
          <span v-if="extracting" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          {{ extracting ? 'AI 视觉识别中...' : '🚀 开始识别' }}
        </button>
      </div>

      <!-- Step 1: 确认 -->
      <div v-else-if="step === 1" key="confirm" class="space-y-4">
        <ConfirmCard :extractResult="extractResult" :priceInfo="priceInfo" :loading="queryingPrice"
          @confirm="doGenerate" @saveDraft="doSaveDraft" />
        <button class="w-full py-2.5 text-gray-400 text-sm hover:text-gray-600 transition-colors" @click="step = 0">← 返回重新上传</button>
      </div>

      <!-- Step 2: 生成 -->
      <div v-else-if="step === 2" key="generate" class="space-y-4">
        <TypewriterText :text="generatedText" :active="generating" :done="generateDone" @save="doSave" />
        <button class="w-full py-2.5 text-gray-400 text-sm hover:text-gray-600 transition-colors" @click="resetAll">发布另一件商品 →</button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useUser } from '../store/user.js'
import ImageUploader from '../components/ImageUploader.vue'
import ConfirmCard from '../components/ConfirmCard.vue'
import TypewriterText from '../components/TypewriterText.vue'
import { extractImage, queryPrice, generateStream, saveHistory } from '../api/index.js'

const toast = inject('toast', () => {})
const { userId } = useUser()

const steps = [{ label: '上传' }, { label: '确认' }, { label: '生成' }]
const step = ref(0)
const imageFile = ref(null)
const extracting = ref(false)
const extractResult = ref({ category: '', brand: '', model: '', condition: '' })
const queryingPrice = ref(false)
const priceInfo = ref(null)
const generating = ref(false)
const generateDone = ref(false)
const generatedText = ref('')
const _savedForm = ref(null)

async function doExtract() {
  extracting.value = true
  try {
    const resp = await extractImage(imageFile.value, userId.value)
    if (resp.success && resp.data) {
      extractResult.value = resp.data
      extractResult.value.image_urls = resp.image_urls || []
      toast('AI 识别完成，请确认信息', 'success')
    } else {
      toast(resp.error || '识别失败，请重试', 'error')
    }
  } catch {
    extractResult.value = { category: '', brand: '', model: '', condition: '', image_urls: [] }
    toast('视觉服务暂未就绪，请手动填写商品信息', 'warning')
  } finally {
    extracting.value = false
    step.value = 1
  }
}

async function doSaveDraft(form) {
  _savedForm.value = form
  await saveHistory({
    user_id: userId.value,
    image_url: extractResult.value.image_urls?.[0] || '',
    title: `${form.brand || ''} ${form.model || ''}`.trim() || '未命名草稿',
    desc: `品牌：${form.brand || '未填'}\n型号：${form.model || '未填'}\n成色：${form.condition || '未填'}\n品类：${form.category || '未填'}`,
    price: 0,
    status: 'draft',
  })
  toast('草稿已保存，可在"历史"页查看并继续发布', 'success')
}

async function doGenerate(form) {
  _savedForm.value = form
  queryingPrice.value = true
  try { priceInfo.value = await queryPrice(form.brand, form.model) } catch { priceInfo.value = null }
  queryingPrice.value = false

  step.value = 2
  generating.value = true
  generatedText.value = ''
  toast('AI 正在为您生成文案...', 'info')

  const { stream } = generateStream({
    user_id: userId.value, category: form.category, brand: form.brand, model: form.model,
    condition: form.condition, image_urls: extractResult.value.image_urls || [],
    avg_price: priceInfo.value?.avg_price || null, low_price: priceInfo.value?.low_price || null, high_price: priceInfo.value?.high_price || null,
  })

  const reader = stream.getReader()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    if (value.content) generatedText.value += value.content
    if (value.done) { generating.value = false; generateDone.value = true; toast('文案生成完毕！', 'success') }
    if (value.error) { toast(value.error, 'error'); generating.value = false }
  }
}

async function doSave() {
  const lines = generatedText.value.split('\n')
  let title = lines[0] || 'AI 生成商品'
  let price = 0
  for (const line of lines) {
    const m = line.match(/[\d,]+/)
    if (m && (line.includes('售价') || line.includes('¥') || line.includes('￥'))) { price = parseFloat(m[0].replace(/,/g, '')); break }
  }
  await saveHistory({ user_id: userId.value, image_url: extractResult.value.image_urls?.[0] || '', title, desc: generatedText.value, price })
  toast('已保存到发布记录', 'success')
}

function resetAll() {
  step.value = 0; extractResult.value = { category: '', brand: '', model: '', condition: '' }
  priceInfo.value = null; generatedText.value = ''; generateDone.value = false; imageFile.value = null
}
</script>
