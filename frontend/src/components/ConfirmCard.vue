<template>
  <div class="bg-primary-800/60 backdrop-blur-xl rounded-2xl shadow-xl border border-primary-700/50 p-6 space-y-5">
    <div class="flex items-center gap-3">
      <div class="relative">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 via-amber-500 to-orange-500 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-amber-500/30">✎</div>
        <div class="absolute -inset-1 bg-gradient-to-br from-amber-400/40 to-orange-400/40 rounded-xl blur-lg opacity-40 -z-10"></div>
      </div>
      <div>
        <h3 class="font-semibold text-white">确认商品信息</h3>
        <p class="text-xs text-primary-400">AI 识别结果，可修改后确认</p>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="category" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">品类</label>
        <input 
          id="category"
          v-model="local.category" 
          placeholder="例如：手机、笔记本…"
          class="w-full px-4 py-2.5 border rounded-xl text-sm text-white placeholder:text-primary-500 outline-none transition-all"
          :class="borderClass('category')"
          autocomplete="off"
        />
        <p v-if="fieldMsg('category')" class="text-xs mt-1 ml-1" :class="msgColor('category')">{{ fieldMsg('category') }}</p>
      </div>

      <div class="space-y-1.5">
        <label for="brand" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">品牌 <span class="text-red-400">*</span></label>
        <input 
          id="brand"
          v-model="local.brand" 
          placeholder="例如：Apple、罗技…" 
          maxlength="50"
          class="w-full px-4 py-2.5 border rounded-xl text-sm text-white placeholder:text-primary-500 outline-none transition-all"
          :class="borderClass('brand')"
          autocomplete="off"
          aria-required="true"
        />
        <p v-if="fieldMsg('brand')" class="text-xs mt-1 ml-1" :class="msgColor('brand')">{{ fieldMsg('brand') }}</p>
      </div>

      <div class="space-y-1.5 col-span-2">
        <label for="model" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">型号 <span class="text-red-400">*</span></label>
        <input 
          id="model"
          v-model="local.model" 
          placeholder="例如：iPhone 13、G610 机械键盘…" 
          maxlength="100"
          class="w-full px-4 py-2.5 border rounded-xl text-sm text-white placeholder:text-primary-500 outline-none transition-all"
          :class="borderClass('model')"
          autocomplete="off"
          aria-required="true"
        />
        <p v-if="fieldMsg('model')" class="text-xs mt-1 ml-1" :class="msgColor('model')">{{ fieldMsg('model') }}</p>
      </div>

      <div class="space-y-1.5 col-span-2">
        <label for="condition" class="block text-xs text-primary-300 font-medium uppercase tracking-wider">成色描述</label>
        <textarea 
          id="condition"
          v-model="local.condition" 
          rows="3" 
          placeholder="例如：9成新，屏幕有细微划痕，电池健康度85%…" 
          maxlength="200"
          class="w-full px-4 py-2.5 border rounded-xl text-sm text-white placeholder:text-primary-500 outline-none transition-all resize-none"
          :class="borderClass('condition')"
        />
        <p v-if="fieldMsg('condition')" class="text-xs mt-1 ml-1 text-red-400">{{ fieldMsg('condition') }}</p>
      </div>
    </div>

    <div v-if="priceInfo && priceInfo.matched" class="rounded-xl overflow-hidden">
      <div class="bg-gradient-to-r from-success-900/30 via-success-800/30 to-success-700/30 border border-success-700/50 px-4 py-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs text-success-300 font-medium flex items-center gap-1.5">
            <span>📊</span> 市场行情参考
          </span>
          <span class="text-xs text-success-400">{{ priceInfo.brand }} {{ priceInfo.model }}</span>
        </div>
        <div class="flex items-end gap-6">
          <div>
            <p class="text-xs text-success-400">均价</p>
            <p class="text-2xl font-bold text-success-200">¥{{ priceInfo.avg_price.toLocaleString() }}</p>
          </div>
          <div class="flex-1 pb-1.5">
            <div class="flex justify-between text-[10px] text-success-400/70 mb-0.5">
              <span>¥{{ priceInfo.low_price.toLocaleString() }}</span>
              <span>¥{{ priceInfo.high_price.toLocaleString() }}</span>
            </div>
            <div class="relative h-2.5 bg-success-800/50 rounded-full overflow-hidden">
              <div class="absolute top-0 bottom-0 bg-gradient-to-r from-success-500 via-success-400 to-success-300 rounded-full transition-all duration-700"
                :style="{ left: lowPct + '%', width: rangePct + '%' }" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="priceInfo && !priceInfo.matched"
      class="rounded-xl bg-amber-900/30 border border-amber-700/50 px-4 py-3 text-sm text-amber-300 flex items-start gap-2">
      <span class="text-lg">💡</span>
      <span>暂无该型号的市场行情，AI 将根据经验生成建议价</span>
    </div>

    <div v-if="warnings.length" class="rounded-xl bg-amber-900/30 border border-amber-700/50 px-4 py-3 text-xs space-y-1">
      <p class="text-amber-300 font-medium flex items-center gap-1.5"><span>⚠️</span> 温馨提示：</p>
      <ul class="list-disc list-inside space-y-0.5 text-amber-400">
        <li v-for="m in warnings" :key="m">{{ m }}</li>
      </ul>
    </div>

    <div v-if="errors.length" class="rounded-xl bg-red-900/30 border border-red-700/50 px-4 py-3 text-xs text-red-300 space-y-1" role="alert" aria-live="polite">
      <p class="font-medium">请修正以下问题后重试：</p>
      <ul class="list-disc list-inside space-y-0.5">
        <li v-for="m in errors" :key="m">{{ m }}</li>
      </ul>
    </div>

    <div class="flex gap-3 pt-2">
      <button
        class="flex-1 py-3.5 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        :class="canPublish && !loading
          ? 'bg-gradient-to-r from-primary-500 via-primary-400 to-primary-300 hover:from-primary-400 hover:via-primary-300 hover:to-primary-200 shadow-lg shadow-primary-500/40 hover:shadow-xl hover:shadow-primary-500/50 transform hover:-translate-y-0.5 active:translate-y-0'
          : 'bg-primary-700/50'"
        :disabled="!canPublish || loading"
        @click="$emit('confirm', local)"
      >
        <span v-if="loading" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        {{ loading ? '查询行情中…' : '✨ 确认并生成文案' }}
      </button>

      <button
        class="px-6 py-3.5 rounded-xl font-medium border transition-all flex items-center gap-2"
        :class="canSaveDraft
          ? 'text-primary-200 border-primary-600 hover:bg-primary-700/50 hover:text-white'
          : 'text-primary-500 border-primary-700/50 cursor-not-allowed'"
        :disabled="!canSaveDraft || loading"
        @click="$emit('saveDraft', local)"
        aria-label="保存草稿"
      >
        <span>💾</span> 存草稿
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'

const props = defineProps({
  extractResult: { type: Object, default: () => ({}) },
  priceInfo: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
defineEmits(['confirm', 'saveDraft'])

const local = reactive({ category: '', brand: '', model: '', condition: '' })
watch(() => props.extractResult, (v) => { if (v) Object.assign(local, v) }, { immediate: true })

function validateField(value, fieldName, maxLen = 100) {
  const mandatory = fieldName.startsWith('品牌') || fieldName.startsWith('型号')
  if (!value) return mandatory ? { level: 'error', msg: `请填写${fieldName}` } : null
  if (value.length < 2) return { level: 'error', msg: `${fieldName}至少 2 个字符` }
  if (value.length > maxLen) return { level: 'error', msg: `${fieldName}不能超过 ${maxLen} 个字符` }
  if (/^(.)\1{3,}$/.test(value)) return { level: 'error', msg: `${fieldName}不能全是重复字符` }
  if (/^\d+$/.test(value)) return { level: 'error', msg: `${fieldName}不能全是数字` }
  if (/^[^a-zA-Z\u4e00-\u9fff\d]+$/.test(value)) return { level: 'error', msg: `${fieldName}不能全是符号` }
  if (value.length > 4) {
    const letters = (value.match(/[a-zA-Z\u4e00-\u9fff]/g) || []).length
    if (letters / value.length < 0.3) return { level: 'error', msg: `${fieldName}看起来像乱码` }
  }
  return { level: 'ok', msg: '' }
}

function validateBrand(value) {
  const hasCh = /[\u4e00-\u9fff]/.test(value)
  const chCount = (value.match(/[\u4e00-\u9fff]/g) || []).length
  const hasEng = /[a-zA-Z]/.test(value)
  const hasNum = /\d/.test(value)
  const total = value.length
  if (hasCh && !hasEng && !hasNum && total > 10)
    return { level: 'warn', msg: `"${value}" 作为品牌名较长，确认无误可继续` }
  if (value.includes(' ') && total > 15)
    return { level: 'warn', msg: `品牌名看起来较长，确认无误可继续` }
  return { level: 'ok', msg: '' }
}

function validateModel(value) {
  const hasNum = /\d/.test(value)
  const hasEng = /[a-zA-Z]/.test(value)
  const hasCh = /[\u4e00-\u9fff]/.test(value)
  const chCount = (value.match(/[\u4e00-\u9fff]/g) || []).length
  const hasSpace = /\s/.test(value)
  const total = value.length
  if (hasSpace && !hasNum && !hasEng && chCount / total > 0.7 && total > 10)
    return { level: 'error', msg: '型号看起来像是普通句子，请填写具体型号（如 iPhone 13）' }
  if (!hasNum && !hasEng && chCount > 15)
    return { level: 'error', msg: '型号过长，应包含数字或英文（如 G610 机械键盘）' }
  if (total > 20 && chCount / total > 0.8 && !hasNum)
    return { level: 'error', msg: '型号信息密度不足，请缩短为具体型号名称' }
  if (!hasNum && !hasEng && chCount > 6)
    return { level: 'warn', msg: `"${value}" 看起来是纯中文型号，确认无误可继续` }
  return { level: 'ok', msg: '' }
}

const fields = computed(() => {
  const b = validateField(local.brand || '', '品牌', 50) || { level: 'ok', msg: '' }
  const m = validateField(local.model || '', '型号', 100) || { level: 'ok', msg: '' }
  const c = local.category ? validateField(local.category, '品类') : null
  const cond = local.condition ? validateField(local.condition, '成色描述', 200) : null

  return {
    brand: b.level === 'ok' ? validateBrand(local.brand || '') : b,
    model: m.level === 'ok' ? validateModel(local.model || '') : m,
    category: c || { level: 'ok', msg: '' },
    condition: cond || { level: 'ok', msg: '' },
  }
})

const errors   = computed(() => Object.entries(fields.value).filter(([,v]) => v && v.level === 'error').map(([k,v]) => ({ [k]: v.msg })))
const warnings = computed(() => Object.entries(fields.value).filter(([,v]) => v && v.level === 'warn').map(([,v]) => v.msg))
const canPublish = computed(() => errors.value.length === 0 && local.brand && local.model)
const canSaveDraft = computed(() => local.brand || local.model || local.category)

function fieldMsg(key) {
  const f = fields.value[key]
  if (!f || !f.msg) return ''
  return f.level === 'ok' ? '✓' : f.msg
}
function msgColor(key) {
  const f = fields.value[key]
  if (!f || f.level === 'ok') return 'text-success-400'
  return f.level === 'warn' ? 'text-amber-400' : 'text-red-400'
}
const colorMap = { ok: 'bg-success-900/30 border-success-600 focus:ring-success-500/30', warn: 'bg-amber-900/30 border-amber-600 focus:ring-amber-500/30', error: 'bg-red-900/30 border-red-600 focus:ring-red-500/30' }
const gray = 'bg-primary-900/50 border-primary-600 focus:bg-primary-900 focus:ring-primary-500/30 focus:border-primary-500'
function borderClass(key) {
  const f = fields.value[key]
  const raw = key === 'brand' ? local.brand : key === 'model' ? local.model : key === 'category' ? local.category : local.condition
  if (!raw) return gray
  return colorMap[f ? f.level : 'ok'] || gray
}

const lowPct = computed(() => {
  if (!props.priceInfo?.matched) return 0
  const range = Math.max(1, props.priceInfo.high_price - props.priceInfo.low_price)
  return Math.max(0, ((props.priceInfo.avg_price - props.priceInfo.low_price) / range) * 80)
})
const rangePct = computed(() => 20)
</script>