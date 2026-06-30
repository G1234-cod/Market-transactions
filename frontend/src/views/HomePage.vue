<template>
  <div class="space-y-8">
    <div class="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold gradient-text">发布二手商品</h1>
        </div>
        <p class="text-text-muted text-sm mt-2">上传物品照片，AI 自动识别商品信息并生成专业带货文案</p>
      </div>
      <!-- 步骤指示器 -->
      <div class="flex items-center gap-2">
        <template v-for="(s, i) in steps" :key="s.label">
          <div class="flex flex-col items-center gap-1.5 cursor-pointer group" @click="step >= i && (step = i)">
            <div class="relative">
              <div class="step-indicator"
                :class="step >= i ? 'step-indicator-active' : 'step-indicator-pending'">
                <span v-if="step > i">✓</span><span v-else>{{ i + 1 }}</span>
              </div>
              <div v-if="step >= i" class="absolute -inset-1 bg-gradient-to-r from-primary-400/50 to-accent-400/50 rounded-full blur-lg opacity-50 -z-10 animate-pulse-slow"></div>
            </div>
            <span class="text-xs font-medium transition-colors" :class="step >= i ? 'text-primary-600' : 'text-text-muted group-hover:text-primary-500'">{{ s.label }}</span>
          </div>
          <div v-if="i < steps.length - 1" class="w-10 sm:w-16 h-1 mx-1 rounded-full transition-all duration-500 relative overflow-hidden"
            :class="step > i ? 'bg-primary-200' : 'bg-border-light'">
            <div v-if="step > i" class="absolute inset-y-0 left-0 gradient-primary rounded-full transition-all duration-500" style="width: 100%"></div>
          </div>
        </template>
      </div>
    </div>

    <div class="glass-card overflow-hidden">
      <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border">
        <div class="flex items-center gap-2">
          <span class="text-lg">{{ stepIcons[step] }}</span>
          <h2 class="font-semibold text-text-primary">{{ stepTitles[step] }}</h2>
        </div>
      </div>

      <div class="p-6 sm:p-8 lg:p-10">
        <transition name="step" mode="out-in">
          <div v-if="step === 0" key="upload" class="space-y-6">
            <div class="max-w-2xl mx-auto">
              <ImageUploader v-model="imageFile" />
              <button
                class="btn-primary w-full mt-6"
                :disabled="!imageFile || extracting"
                @click="doExtract"
              >
                <span v-if="extracting" class="loading-spinner mr-2" />
                <span>{{ extracting ? 'AI 视觉识别中…' : '🚀 开始识别' }}</span>
              </button>
            </div>
          </div>

          <div v-else-if="step === 1" key="confirm">
            <ConfirmCard :extractResult="extractResult" :priceInfo="priceInfo" :loading="queryingPrice"
              @confirm="doGenerate" @saveDraft="doSaveDraft" />
            <button class="btn-outline w-full flex items-center justify-center gap-2 mt-4" @click="step = 0">
              <span>←</span> 返回重新上传
            </button>
          </div>

          <div v-else-if="step === 2" key="generate">
            <TypewriterText :text="generatedText" :active="generating" :done="generateDone" />
            <button class="btn-outline w-full flex items-center justify-center gap-2 mt-4" @click="resetAll">
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
  // ✅ 修复：清理旧的 timeout 防止竞态
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
          // 自动保存到发布历史
          await doSave()
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
            // 自动保存到发布历史
            await doSave()
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
  // ✅ 商城展示用户手动输入的价格，不使用 AI 定价
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