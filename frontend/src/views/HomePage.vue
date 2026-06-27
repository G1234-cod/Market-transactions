<template>
  <div class="space-y-8">
    <div class="text-center space-y-4">
      <div class="relative inline-block">
        <div class="absolute -inset-4 bg-gradient-to-r from-primary-500/30 to-primary-400/30 rounded-3xl blur-2xl -z-10"></div>
        <h1 class="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary-200 via-white to-primary-100 bg-clip-text text-transparent relative">发布二手商品</h1>
      </div>
      <p class="text-primary-300 text-sm sm:text-base max-w-md mx-auto">上传物品照片，AI 自动识别商品信息并生成专业带货文案</p>
    </div>

    <div class="flex justify-center items-center gap-0">
      <template v-for="(s, i) in steps" :key="s.label">
        <div class="flex flex-col items-center gap-2 cursor-pointer group" @click="step >= i && (step = i)">
          <div class="relative">
            <div class="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-500"
              :class="step >= i ? 'bg-gradient-to-br from-primary-500 via-primary-400 to-primary-300 text-white shadow-xl shadow-primary-500/40 scale-110' : 'bg-primary-800/50 text-primary-400 group-hover:bg-primary-700/50'">
              <span v-if="step > i">✓</span><span v-else>{{ i + 1 }}</span>
            </div>
            <div v-if="step >= i" class="absolute -inset-1 bg-gradient-to-br from-primary-400/50 to-primary-500/50 rounded-full blur-lg opacity-50 -z-10 animate-pulse"></div>
          </div>
          <span class="text-xs font-medium transition-colors" :class="step >= i ? 'text-primary-200' : 'text-primary-500 group-hover:text-primary-400'">{{ s.label }}</span>
        </div>
        <div v-if="i < steps.length - 1" class="w-12 sm:w-24 h-1 mx-2 rounded-full transition-all duration-500 relative overflow-hidden"
          :class="step > i ? 'bg-primary-700/50' : 'bg-primary-800/50'">
          <div v-if="step > i" class="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-500 to-primary-400 rounded-full transition-all duration-500" style="width: 100%"></div>
        </div>
      </template>
    </div>

    <transition name="step" mode="out-in">
      <div v-if="step === 0" key="upload" class="space-y-5">
        <ImageUploader v-model="imageFile" />
        <button 
          class="w-full py-4 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          :class="imageFile ? 'bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transform hover:-translate-y-0.5 active:translate-y-0' : 'bg-primary-700/50'"
          :disabled="!imageFile || extracting" 
          @click="doExtract"
        >
          <span v-if="extracting" class="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          <span>{{ extracting ? 'AI 视觉识别中…' : '🚀 开始识别' }}</span>
        </button>
      </div>

      <div v-else-if="step === 1" key="confirm" class="space-y-4">
        <ConfirmCard :extractResult="extractResult" :priceInfo="priceInfo" :loading="queryingPrice"
          @confirm="doGenerate" @saveDraft="doSaveDraft" />
        <button class="w-full py-3 text-primary-400 text-sm hover:text-primary-200 transition-colors flex items-center justify-center gap-1.5" @click="step = 0">
          <span>←</span> 返回重新上传
        </button>
      </div>

      <div v-else-if="step === 2" key="generate" class="space-y-4">
        <TypewriterText :text="generatedText" :active="generating" :done="generateDone" @save="doSave" />
        <button class="w-full py-3 text-primary-400 text-sm hover:text-primary-200 transition-colors flex items-center justify-center gap-1.5" @click="resetAll">
          发布另一件商品 <span>→</span>
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, inject, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'  // ✅ 导入 router
import { useUser } from '../store/user.js'
import ImageUploader from '../components/ImageUploader.vue'
import ConfirmCard from '../components/ConfirmCard.vue'
import TypewriterText from '../components/TypewriterText.vue'
import { extractImage, queryPrice, generateStream, saveHistory } from '../api/index.js'

const toast = inject('toast', () => {})
const router = useRouter()  // ✅ 获取 router 实例
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
    const resp = await extractImage(imageFile.value, userId.value)
    if (resp.success && resp.data) {
      extractResult.value = resp.data
      extractResult.value.image_urls = resp.image_urls || []
      toast('AI 识别完成，请确认信息', 'success')
      // ✅ 只在成功时跳转
      extracting.value = false
      step.value = 1
    } else {
      toast(resp.error || '识别失败，请重试', 'error')
      extracting.value = false
      // ✅ 不跳转，留在上传页让用户重试
    }
  } catch (e) {
    // ✅ 检查是否为认证错误
    if (e.response?.status === 401) {
      toast('请先登录', 'error')
      router.push('/login')
      extracting.value = false
      return
    }
    // ✅ 其他错误，留在上传页
    extractResult.value = { category: '', brand: '', model: '', condition: '', image_urls: [] }
    toast('视觉服务暂未就绪，请手动填写商品信息', 'warning')
    extracting.value = false
    // ✅ 不跳转，留在上传页让用户重试
    return
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
    category: form.category,      // ✅ 新增
    brand: form.brand,            // ✅ 新增
    model: form.model,            // ✅ 新增
    condition: form.condition,    // ✅ 新增
  })
  toast('草稿已保存，可在"历史"页查看并继续发布', 'success')
}

async function doGenerate(form) {
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
          console.log('🚀 开始生成:', data.message)
          generating.value = true
          generatedText.value = ''
          toast('生成中...', 'info')
          break

        case 'content':
          generatedText.value += data.content
          break

        case 'done':
          console.log('✅ 生成完成:', data.message)
          generating.value = false
          generateDone.value = true
          isComplete = true
          toast('文案生成完毕！', 'success')
          if (_sseTimeout) {
            clearTimeout(_sseTimeout)
            _sseTimeout = null
          }
          _streamControl = null
          break

        case 'error':
          console.error('❌ 生成错误:', data.message)
          generating.value = false
          isComplete = true
          toast(data.message || '生成失败，请重试', 'error')
          if (_sseTimeout) {
            clearTimeout(_sseTimeout)
            _sseTimeout = null
          }
          _streamControl = null
          break

        default:
          if (data.content) {
            generatedText.value += data.content
          }
          if (data.done) {
            generating.value = false
            generateDone.value = true
            isComplete = true
            toast('文案生成完毕！', 'success')
            if (_sseTimeout) {
              clearTimeout(_sseTimeout)
              _sseTimeout = null
            }
            _streamControl = null
          }
          if (data.error) {
            generating.value = false
            isComplete = true
            toast(data.error, 'error')
            if (_sseTimeout) {
              clearTimeout(_sseTimeout)
              _sseTimeout = null
            }
            _streamControl = null
          }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('SSE 请求已被取消')
      generating.value = false
      _streamControl = null
      return
    }
    console.error('❌ SSE 流读取错误:', error)
    generating.value = false
    isComplete = true
    toast('连接中断，请重试', 'error')
    if (_sseTimeout) {
      clearTimeout(_sseTimeout)
      _sseTimeout = null
    }
    _streamControl = null
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
  await saveHistory({ 
    user_id: userId.value, 
    image_url: extractResult.value.image_urls?.[0] || '', 
    title, 
    desc: generatedText.value, 
    price,
    status: 'published',
    category: _savedForm.value?.category,      // ✅ 新增
    brand: _savedForm.value?.brand,            // ✅ 新增
    model: _savedForm.value?.model,            // ✅ 新增
    condition: _savedForm.value?.condition,    // ✅ 新增
  })
  toast('已保存到发布记录', 'success')
}

function resetAll() {
  if (_streamControl) {
    _streamControl.abort()
    _streamControl = null
  }
  step.value = 0
  extractResult.value = { category: '', brand: '', model: '', condition: '' }
  priceInfo.value = null
  generatedText.value = ''
  generateDone.value = false
  imageFile.value = null
  if (_sseTimeout) {
    clearTimeout(_sseTimeout)
    _sseTimeout = null
  }
}

onBeforeUnmount(() => {
  if (_streamControl) {
    _streamControl.abort()
    _streamControl = null
  }
  if (_sseTimeout) {
    clearTimeout(_sseTimeout)
    _sseTimeout = null
  }
})
</script>