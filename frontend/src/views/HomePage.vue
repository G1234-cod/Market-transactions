<template>
  <div class="space-y-12 relative">
    <div class="hero-section text-center py-16 sm:py-24 relative">
      <div class="orb orb-primary w-96 h-96 -top-20 -left-20 animate-float-slow"></div>
      <div class="orb orb-accent w-80 h-80 -bottom-10 -right-10 animate-float-medium"></div>
      <div class="orb orb-amber w-64 h-64 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-float-fast opacity-20"></div>
      
      <div class="relative z-10 space-y-6">
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-medium animate-fade-in-up-1">
          <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse"></span>
          AI 智能识别技术支持
        </div>
        
        <h1 class="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-tight animate-fade-in-up-2">
          <span class="gradient-text">发布二手商品</span>
        </h1>
        
        <p class="text-text-secondary text-base sm:text-lg max-w-xl mx-auto leading-relaxed animate-fade-in-up-3">
          上传物品照片，AI 自动识别商品信息并生成专业带货文案
        </p>
      </div>
    </div>

    <div class="flex flex-wrap justify-center items-center gap-2 sm:gap-4 animate-fade-in-up-4">
      <template v-for="(s, i) in steps" :key="s.label">
        <div class="flex flex-col items-center gap-3 cursor-pointer group" @click="step >= i && (step = i)">
          <div class="relative">
            <div class="step-indicator w-14 h-14 text-base"
              :class="step >= i ? 'step-indicator-active' : 'step-indicator-pending'">
              <span v-if="step > i">✓</span><span v-else>{{ i + 1 }}</span>
            </div>
            <div v-if="step >= i" class="absolute -inset-2 bg-gradient-to-r from-primary-500/40 to-accent-500/40 rounded-full blur-xl opacity-60 -z-10 animate-pulse-slow"></div>
          </div>
          <span class="text-sm font-medium transition-all" :class="step >= i ? 'text-primary-400' : 'text-text-muted group-hover:text-primary-400'">{{ s.label }}</span>
        </div>
        <div v-if="i < steps.length - 1" class="w-12 sm:w-24 h-1.5 mx-2 rounded-full transition-all duration-500 relative overflow-hidden hidden sm:block"
          :class="step > i ? 'bg-primary-500/30' : 'bg-border/50'">
          <div v-if="step > i" class="absolute inset-y-0 left-0 gradient-primary rounded-full transition-all duration-500" style="width: 100%"></div>
        </div>
      </template>
    </div>

    <div class="glass-card overflow-hidden animate-fade-in-up-5 card-glow-hover">
      <div class="bg-gradient-to-r from-primary-500/15 via-accent-500/10 to-primary-500/15 px-8 py-5 border-b border-border/50">
        <div class="flex items-center gap-4">
          <span class="text-2xl">{{ stepIcons[step] }}</span>
          <div>
            <h2 class="text-lg font-bold text-text-primary">{{ stepTitles[step] }}</h2>
            <p class="text-xs text-text-muted">第 {{ step + 1 }} / {{ steps.length }} 步</p>
          </div>
        </div>
      </div>
      
      <div class="p-8">
        <transition name="step" mode="out-in">
          <div v-if="step === 0" key="upload" class="space-y-6">
            <ImageUploader v-model="imageFile" />
            <button 
              class="btn-primary w-full ripple-container text-lg py-4"
              :disabled="!imageFile || extracting" 
              @click="doExtract"
            >
              <span v-if="extracting" class="loading-spinner mr-3" />
              <span>{{ extracting ? 'AI 视觉识别中…' : '🚀 开始识别' }}</span>
            </button>
          </div>

          <div v-else-if="step === 1" key="confirm" class="space-y-6">
            <ConfirmCard :extractResult="extractResult" :priceInfo="priceInfo" :loading="queryingPrice"
              @confirm="doGenerate" @saveDraft="doSaveDraft" />
            <button class="btn-outline w-full flex items-center justify-center gap-2 ripple-container py-3" @click="step = 0">
              <span>←</span> 返回重新上传
            </button>
          </div>

          <div v-else-if="step === 2" key="generate" class="space-y-6">
            <TypewriterText :text="generatedText" :active="generating" :done="generateDone" @save="doSave" />
            <button class="btn-outline w-full flex items-center justify-center gap-2 ripple-container py-3" @click="resetAll">
              发布另一件商品 <span>→</span>
            </button>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '../store/user.js'
import ImageUploader from '../components/ImageUploader.vue'
import ConfirmCard from '../components/ConfirmCard.vue'
import TypewriterText from '../components/TypewriterText.vue'
import { extractImage, queryPrice, generateStream, saveHistory, recognizeImage } from '../api/index.js'

const toast = inject('toast', () => {})
const router = useRouter()
const { userId } = useUser()

const steps = [{ label: '上传' }, { label: '确认' }, { label: '生成' }]
const stepIcons = ['📸', '✍️', '🤖']
const stepTitles = ['上传商品图片', '确认商品信息', 'AI 生成文案']
const step = ref(0)
const imageFile = ref(null)
const extracting = ref(false)
const extractResult = ref({ 
  category: '', 
  brand: '', 
  model: '', 
  condition: '',
  title: '',
  description: '',
  suggested_price: 0,
  price_reasoning: '',
  selling_points: []
})
const queryingPrice = ref(false)
const priceInfo = ref(null)
const generating = ref(false)
const generateDone = ref(false)
const generatedText = ref('')
const _savedForm = ref(null)
let _sseTimeout = null
let _streamControl = null

function cancelGenerate() {
  if (_streamControl) {
    _streamControl.abort()
    _streamControl = null
    generating.value = false
    toast('生成已取消', 'warning')
  }
}

async function doExtract() {
  extracting.value = true
  try {
    const resp = await recognizeImage(imageFile.value)
    if (resp.success && resp.final_result) {
      extractResult.value = {
        category: resp.final_result.category || '',
        brand: resp.final_result.brand || '',
        model: resp.final_result.model || '',
        condition: resp.final_result.condition || '',
        title: resp.deepseek?.title || '',
        description: resp.deepseek?.description || '',
        suggested_price: resp.deepseek?.suggested_price || resp.market_price?.avg_price || 0,
        price_reasoning: resp.deepseek?.price_reasoning || '',
        selling_points: resp.deepseek?.selling_points || [],
        image_urls: resp.image_urls || [],
        annotated_url: resp.defect_result?.annotated_url || '',
        defect_count: resp.defect_result?.defect_count || 0,
        condition_grade: resp.defect_result?.condition_grade || null,
      }
      
      if (resp.market_price?.avg_price) {
        priceInfo.value = {
          avg_price: resp.market_price.avg_price,
          matched: resp.market_price.matched,
        }
      }
      
      toast('AI 识别完成，请确认信息', 'success')
      extracting.value = false
      step.value = 1
    } else {
      toast(resp.error || '识别失败，请重试', 'error')
      extracting.value = false
    }
  } catch (e) {
    if (e.response?.status === 401) {
      toast('请先登录', 'error')
      router.push('/login')
      extracting.value = false
      return
    }
    extractResult.value = { 
      category: '', 
      brand: '', 
      model: '', 
      condition: '',
      title: '',
      description: '',
      suggested_price: 0,
      price_reasoning: '',
      selling_points: [],
      image_urls: [] 
    }
    toast('视觉服务暂未就绪，请手动填写商品信息', 'warning')
    extracting.value = false
    return
  }
}

async function doSaveDraft(form) {
  _savedForm.value = form
  try {
    await saveHistory({
      user_id: userId.value,
      image_url: extractResult.value.image_urls?.[0] || '',
      title: `${form.brand || ''} ${form.model || ''}`.trim() || '未命名草稿',
      desc: `品牌：${form.brand || '未填'}\n型号：${form.model || '未填'}\n成色：${form.condition || '未填'}\n品类：${form.category || '未填'}`,
      price: 0,
      status: 'draft',
      category: form.category,
      brand: form.brand,
      model: form.model,
      condition: form.condition,
    })
    toast('草稿已保存，可在"历史"页查看并继续发布', 'success')
  } catch {
    toast('草稿保存失败，请重试', 'error')
  }
}

async function doGenerate(form) {
  if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
  if (_streamControl) {
    _streamControl.abort()
    _streamControl = null
  }

  _savedForm.value = form
  queryingPrice.value = true
  try { priceInfo.value = await queryPrice(form.brand, form.model) } catch { priceInfo.value = null }
  queryingPrice.value = false

  step.value = 2
  generating.value = true
  generateDone.value = false
  generatedText.value = ''
  toast('AI 正在为您生成文案...', 'info')

  const { stream, abort } = generateStream({
    user_id: userId.value, 
    category: form.category, 
    brand: form.brand, 
    model: form.model,
    condition: form.condition, 
    image_urls: extractResult.value.image_urls || [],
    avg_price: priceInfo.value?.avg_price || null, 
    low_price: priceInfo.value?.low_price || null, 
    high_price: priceInfo.value?.high_price || null,
  })

  _streamControl = { abort }

  const reader = stream.getReader()
  let isComplete = false

  _sseTimeout = setTimeout(() => {
    if (generating.value && !isComplete) {
      generating.value = false
      toast('生成超时，请重试', 'error')
      if (_streamControl) {
        _streamControl.abort()
        _streamControl = null
      }
    }
  }, 60000)

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        if (generating.value && !isComplete) {
          generating.value = false
          toast('生成中断，请重试', 'warning')
        }
        break
      }

      const data = value

      switch (data.type) {
        case 'start':
          generating.value = true
          generatedText.value = ''
          toast('生成中...', 'info')
          break

        case 'content':
          generatedText.value += data.content
          break

        case 'done':
          generating.value = false
          generateDone.value = true
          isComplete = true
          toast('文案生成完毕！', 'success')
          if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
          _streamControl = null
          break

        case 'error':
          generating.value = false
          isComplete = true
          toast(data.message || '生成失败，请重试', 'error')
          if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
          _streamControl = null
          break

        default:
          if (data.content) { generatedText.value += data.content }
          if (data.done) {
            generating.value = false
            generateDone.value = true
            isComplete = true
            toast('文案生成完毕！', 'success')
            if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
            _streamControl = null
          }
          if (data.error) {
            generating.value = false
            isComplete = true
            toast(data.error, 'error')
            if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
            _streamControl = null
          }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      generating.value = false
      _streamControl = null
      return
    }
    generating.value = false
    isComplete = true
    toast('连接中断，请重试', 'error')
    if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
    _streamControl = null
  }
}

async function doSave() {
  const lines = generatedText.value.split('\n')
  let title = lines[0] || 'AI 生成商品'
  let price = _savedForm.value?.user_price || _savedForm.value?.suggested_price || 0
  try {
    await saveHistory({
      user_id: userId.value,
      image_url: extractResult.value.image_urls?.[0] || '',
      title,
      desc: generatedText.value,
      price,
      status: 'published',
      category: _savedForm.value?.category,
      brand: _savedForm.value?.brand,
      model: _savedForm.value?.model,
      condition: _savedForm.value?.condition,
    })
    toast('已保存到发布记录（已自动加入搜索索引）', 'success')
  } catch {
    toast('保存失败，请重试', 'error')
  }
}

function resetAll() {
  if (_streamControl) { _streamControl.abort(); _streamControl = null }
  step.value = 0
  extractResult.value = { 
    category: '', 
    brand: '', 
    model: '', 
    condition: '',
    title: '',
    description: '',
    suggested_price: 0,
    price_reasoning: '',
    selling_points: []
  }
  priceInfo.value = null
  generatedText.value = ''
  generateDone.value = false
  imageFile.value = null
  if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
}

onBeforeUnmount(() => {
  if (_streamControl) { _streamControl.abort(); _streamControl = null }
  if (_sseTimeout) { clearTimeout(_sseTimeout); _sseTimeout = null }
})
</script>
