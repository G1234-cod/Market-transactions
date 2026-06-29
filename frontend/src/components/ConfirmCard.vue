<template>
  <div class="glass-card overflow-hidden">
    <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border">
      <div class="flex items-center gap-3">
        <div class="relative">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 via-amber-500 to-orange-500 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-amber-500/30">✎</div>
          <div class="absolute -inset-1 bg-gradient-to-br from-amber-400/40 to-orange-400/40 rounded-xl blur-lg opacity-40 -z-10"></div>
        </div>
        <div>
          <h3 class="font-semibold text-text-primary">确认商品信息</h3>
          <p class="text-xs text-text-muted">AI 识别结果，可修改后确认</p>
        </div>
      </div>
    </div>

    <div class="p-6 space-y-5">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="space-y-1.5">
          <label for="category" class="block text-xs text-text-muted font-medium uppercase tracking-wider">品类</label>
          <input 
            id="category"
            v-model="local.category" 
            placeholder="例如：手机、笔记本…"
            class="input-field"
            :class="borderClass('category')"
            autocomplete="off"
          />
          <p v-if="fieldMsg('category')" class="text-xs mt-1 ml-1" :class="msgColor('category')">{{ fieldMsg('category') }}</p>
        </div>

        <div class="space-y-1.5">
          <label for="brand" class="block text-xs text-text-muted font-medium uppercase tracking-wider">品牌 <span class="text-danger-500">*</span></label>
          <input 
            id="brand"
            v-model="local.brand" 
            placeholder="例如：Apple、罗技…" 
            maxlength="50"
            class="input-field"
            :class="borderClass('brand')"
            autocomplete="off"
            aria-required="true"
          />
          <p v-if="fieldMsg('brand')" class="text-xs mt-1 ml-1" :class="msgColor('brand')">{{ fieldMsg('brand') }}</p>
        </div>

        <div class="space-y-1.5 col-span-2">
          <label for="model" class="block text-xs text-text-muted font-medium uppercase tracking-wider">型号 <span class="text-danger-500">*</span></label>
          <input 
            id="model"
            v-model="local.model" 
            placeholder="例如：iPhone 13、G610 机械键盘…" 
            maxlength="100"
            class="input-field"
            :class="borderClass('model')"
            autocomplete="off"
            aria-required="true"
          />
          <p v-if="fieldMsg('model')" class="text-xs mt-1 ml-1" :class="msgColor('model')">{{ fieldMsg('model') }}</p>
        </div>

        <div class="space-y-1.5 col-span-2">
          <label for="condition" class="block text-xs text-text-muted font-medium uppercase tracking-wider">成色描述</label>
          <textarea 
            id="condition"
            v-model="local.condition" 
            rows="3" 
            placeholder="例如：9成新，屏幕有细微划痕，电池健康度85%…" 
            maxlength="200"
            class="textarea-field"
            :class="borderClass('condition')"
          />
          <p v-if="fieldMsg('condition')" class="text-xs mt-1 ml-1 text-danger-500">{{ fieldMsg('condition') }}</p>
        </div>

      </div>

      <!-- ✅ AI 定价（独立区块，系统自动生成，仅供展示） -->
      <div class="rounded-xl overflow-hidden border-2 border-dashed border-primary-300 bg-gradient-to-br from-primary-50/50 to-blue-50/50">
        <div class="px-5 py-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-primary-600 font-bold uppercase tracking-wider flex items-center gap-1.5">
              <span>🤖</span> AI 智能定价
            </span>
            <span class="text-[10px] text-primary-400 bg-primary-100 px-2 py-0.5 rounded-full">系统自动生成</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-extrabold text-primary-700">¥{{ (extractResult.suggested_price || 0).toLocaleString() }}</span>
            <span class="text-xs text-primary-400">/ 建议售价</span>
          </div>
          <p v-if="extractResult.price_reasoning" class="text-xs text-primary-500 mt-2 italic">"{{ extractResult.price_reasoning }}"</p>
        </div>
      </div>

      <!-- ✅ 用户手动定价（完全独立的区块） -->
      <div class="rounded-xl border border-border bg-white p-5 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs text-text-primary font-bold uppercase tracking-wider flex items-center gap-1.5">
            <span>✏️</span> 你的售价
          </span>
          <span class="text-[10px] text-text-muted bg-surface-secondary px-2 py-0.5 rounded-full">手动输入</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="relative flex-1">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-semibold text-lg">¥</span>
            <input
              id="user-price"
              v-model.number="local.user_price"
              type="number"
              min="0"
              max="9999999"
              step="1"
              placeholder="输入你的卖价"
              class="w-full pl-9 pr-4 py-3 bg-surface-secondary border border-border rounded-xl text-lg font-bold text-text-primary placeholder:text-text-muted focus:bg-white focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none transition-all"
              autocomplete="off"
            />
          </div>
          <!-- 历史价格按钮 -->
          <button
            v-if="local.brand && local.model"
            @click="goToPriceHistory"
            class="flex-shrink-0 px-4 py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-accent-500 to-green-500 text-white shadow-lg shadow-accent-500/30 hover:shadow-xl hover:shadow-accent-500/40 hover:from-accent-600 hover:to-green-600 transition-all flex items-center gap-1.5"
            title="查看该商品历史价格走势"
          >
            <span>📊</span> 历史价格
          </button>
        </div>
        <p class="text-[11px] text-text-muted">此价格将展示在商城中，AI 价格仅供你参考</p>
      </div>

      <div v-if="extractResult.annotated_url" class="rounded-xl overflow-hidden border border-border">
        <div class="bg-gradient-to-r from-danger-50 to-warning-50/50 px-4 py-3 border-b border-border">
          <div class="flex items-center justify-between">
            <span class="text-xs text-danger-700 font-medium flex items-center gap-1.5">
              <span>🔍</span> 瑕疵检测结果
            </span>
            <div class="flex items-center gap-3">
              <span v-if="extractResult.defect_count" class="text-xs text-danger-600">
                发现 {{ extractResult.defect_count }} 处瑕疵
              </span>
              <!-- ✅ R4: 成色分级标签 -->
              <span v-if="extractResult.condition_grade" class="text-xs font-bold px-2 py-0.5 rounded-full"
                :class="conditionGradeClass">
                {{ extractResult.condition_grade.grade_label }}
              </span>
            </div>
          </div>
        </div>
        <div class="p-4 flex justify-center bg-gray-50">
          <img :src="extractResult.annotated_url" alt="瑕疵标注图" class="max-h-64 rounded-lg object-contain shadow-sm" />
        </div>
        <!-- ✅ 5级成色程度 —— 瑕疵底部独立一行 -->
        <div v-if="extractResult.condition_grade" class="px-4 py-3 border-t border-border flex items-center justify-between"
          :class="conditionGradeBgClass">
          <span class="text-sm font-bold">成色程度</span>
          <span class="text-lg font-extrabold" :class="conditionGradeTextClass">
            {{ extractResult.condition_grade.grade_label }}
          </span>
        </div>
      </div>

      <!-- ✅ R5: 市场行情参考 -->
      <div v-if="priceInfo && priceInfo.matched" class="rounded-xl overflow-hidden">
        <div class="bg-gradient-to-r from-accent-50 via-accent-50/50 to-accent-100/50 border border-accent-200 px-4 py-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-accent-700 font-medium flex items-center gap-1.5">
              <span>📊</span> 市场行情参考
            </span>
            <span class="text-xs text-accent-600">{{ priceInfo.brand }} {{ priceInfo.model }}</span>
          </div>
          <div class="flex items-end gap-6">
            <div>
              <p class="text-xs text-accent-600">均价</p>
              <p class="text-2xl font-bold text-accent-700">¥{{ priceInfo.avg_price.toLocaleString() }}</p>
            </div>
            <div class="flex-1 pb-1.5">
              <div class="flex justify-between text-[10px] text-accent-500/70 mb-0.5">
                <span>¥{{ priceInfo.low_price.toLocaleString() }}</span>
                <span>¥{{ priceInfo.high_price.toLocaleString() }}</span>
              </div>
              <div class="relative h-2.5 bg-accent-200/50 rounded-full overflow-hidden">
                <div class="absolute top-0 bottom-0 bg-gradient-to-r from-accent-500 via-accent-400 to-accent-300 rounded-full transition-all duration-700"
                  :style="{ left: lowPct + '%', width: rangePct + '%' }" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="priceInfo && priceInfo.matched && !local.suggested_price" class="rounded-xl overflow-hidden">
        <div class="bg-gradient-to-r from-accent-50 via-accent-50/50 to-accent-100/50 border border-accent-200 px-4 py-4">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs text-accent-700 font-medium flex items-center gap-1.5">
              <span>📊</span> 市场行情参考
            </span>
            <span class="text-xs text-accent-600">{{ priceInfo.brand }} {{ priceInfo.model }}</span>
          </div>
          <div class="flex items-end gap-6">
            <div>
              <p class="text-xs text-accent-600">均价</p>
              <p class="text-2xl font-bold text-accent-700">¥{{ priceInfo.avg_price.toLocaleString() }}</p>
            </div>
            <div class="flex-1 pb-1.5">
              <div class="flex justify-between text-[10px] text-accent-500/70 mb-0.5">
                <span>¥{{ priceInfo.low_price.toLocaleString() }}</span>
                <span>¥{{ priceInfo.high_price.toLocaleString() }}</span>
              </div>
              <div class="relative h-2.5 bg-accent-200/50 rounded-full overflow-hidden">
                <div class="absolute top-0 bottom-0 bg-gradient-to-r from-accent-500 via-accent-400 to-accent-300 rounded-full transition-all duration-700"
                  :style="{ left: lowPct + '%', width: rangePct + '%' }" />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="priceInfo && !priceInfo.matched"
        class="rounded-xl bg-warning-50 border border-warning-200 px-4 py-3 text-sm text-warning-700 flex items-start gap-2">
        <span class="text-lg">💡</span>
        <span>暂无该型号的市场行情，AI 将根据经验生成建议价</span>
      </div>

      <div v-if="warnings.length" class="rounded-xl bg-warning-50 border border-warning-200 px-4 py-3 text-xs space-y-1">
        <p class="text-warning-700 font-medium flex items-center gap-1.5"><span>⚠️</span> 温馨提示：</p>
        <ul class="list-disc list-inside space-y-0.5 text-warning-600">
          <li v-for="m in warnings" :key="m">{{ m }}</li>
        </ul>
      </div>

      <div v-if="errors.length" class="rounded-xl bg-danger-50 border border-danger-200 px-4 py-3 text-xs text-danger-600 space-y-1" role="alert" aria-live="polite">
        <p class="font-medium">请修正以下问题后重试：</p>
        <ul class="list-disc list-inside space-y-0.5">
          <li v-for="m in errors" :key="m">{{ m }}</li>
        </ul>
      </div>

      <div class="flex gap-3 pt-2">
        <button
          class="flex-1 py-3.5 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          :class="canPublish && !loading
            ? 'gradient-primary shadow-lg shadow-primary-500/30 hover:shadow-xl hover:shadow-primary-500/40 hover:from-primary-600 hover:via-primary-500 hover:to-accent-600 transform hover:-translate-y-0.5 active:translate-y-0'
            : 'bg-gray-400'"
          :disabled="!canPublish || loading"
          @click="$emit('confirm', local)"
        >
          <span v-if="loading" class="loading-spinner" />
          {{ loading ? '查询行情中…' : '✨ 确认并生成文案' }}
        </button>

        <button
          class="px-6 py-3.5 rounded-xl font-medium border transition-all flex items-center gap-2"
          :class="canSaveDraft
            ? 'text-primary-600 border-primary-200 hover:bg-primary-50 hover:border-primary-300'
            : 'text-text-muted border-border cursor-not-allowed'"
          :disabled="!canSaveDraft || loading"
          @click="$emit('saveDraft', local)"
          aria-label="保存草稿"
        >
          <span>💾</span> 存草稿
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  extractResult: { type: Object, default: () => ({}) },
  priceInfo: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
defineEmits(['confirm', 'saveDraft'])

const local = reactive({
  category: '',
  brand: '',
  model: '',
  condition: '',
  title: '',
  description: '',
  suggested_price: 0,   // AI 生成的建议价（来自 extractResult，只读展示）
  user_price: 0,         // 用户手动输入的售价（绑定到 input）
  price_reasoning: '',
  selling_points: [],
  image_urls: [],
  annotated_url: '',
  defect_count: 0,
  condition_grade: null,
})
watch(() => props.extractResult, (v) => {
  if (v) {
    // ✅ 修复：显式赋值替代 Object.assign，防止意外属性注入
    local.category = v.category || ''
    local.brand = v.brand || ''
    local.model = v.model || ''
    local.condition = v.condition || ''
    local.title = v.title || ''
    local.description = v.description || ''
    local.price_reasoning = v.price_reasoning || ''
    local.selling_points = v.selling_points || []
    local.image_urls = v.image_urls || []
    local.annotated_url = v.annotated_url || ''
    local.defect_count = v.defect_count || 0
    local.condition_grade = v.condition_grade || null
    // ✅ AI 定价始终来自后端（只读展示，不绑定到用户价格）
    local.suggested_price = parseFloat(v.suggested_price) || 0
    // ✅ 用户价格完全独立，不自动填入 AI 定价
  }
}, { immediate: true })

function goToPriceHistory() {
  const price = local.suggested_price || props.priceInfo?.avg_price || 0
  router.push(
    `/price-history?brand=${encodeURIComponent(local.brand)}&model=${encodeURIComponent(local.model)}&price=${price}`
  )
}

function validateField(value, fieldName, maxLen = 100, required = false) {
  if (!value) return required ? { level: 'error', msg: `请填写${fieldName}` } : null
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
  const b = validateField(local.brand || '', '品牌', 50, true) || { level: 'ok', msg: '' }
  const m = validateField(local.model || '', '型号', 100, true) || { level: 'ok', msg: '' }
  const c = local.category ? validateField(local.category, '品类') : null
  const cond = local.condition ? validateField(local.condition, '成色描述', 200) : null

  return {
    brand: b.level === 'ok' ? validateBrand(local.brand || '') : b,
    model: m.level === 'ok' ? validateModel(local.model || '') : m,
    category: c || { level: 'ok', msg: '' },
    condition: cond || { level: 'ok', msg: '' },
  }
})

const errors   = computed(() => Object.entries(fields.value).filter(([,v]) => v && v.level === 'error').map(([,v]) => v.msg))
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
  if (!f || f.level === 'ok') return 'text-accent-600'
  return f.level === 'warn' ? 'text-warning-600' : 'text-danger-600'
}
const colorMap = { ok: 'focus:border-accent-400 focus:ring-accent-100', warn: 'focus:border-warning-400 focus:ring-warning-100', error: 'bg-danger-50 border-danger-200 focus:border-danger-400 focus:ring-danger-100' }
const gray = ''
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

const priceBorderClass = computed(() => {
  if (!local.suggested_price || local.suggested_price <= 0) return ''
  return 'focus:border-accent-400 focus:ring-accent-100'
})

// ✅ R4: 成色分级颜色映射（小标签用）
const conditionGradeClass = computed(() => {
  const grade = props.extractResult?.condition_grade?.grade
  if (grade === 0) return 'bg-green-100 text-green-700'
  if (grade === 1) return 'bg-yellow-100 text-yellow-700'
  if (grade === 2) return 'bg-orange-100 text-orange-700'
  if (grade === 3) return 'bg-red-100 text-red-700'
  if (grade === 4) return 'bg-red-200 text-red-800'
  return 'bg-gray-100 text-gray-600'
})

// ✅ R4: 成色程度底部背景色
const conditionGradeBgClass = computed(() => {
  const grade = props.extractResult?.condition_grade?.grade
  if (grade === 0) return 'bg-green-50'
  if (grade === 1) return 'bg-yellow-50'
  if (grade === 2) return 'bg-orange-50'
  if (grade === 3) return 'bg-red-50'
  if (grade === 4) return 'bg-red-100'
  return 'bg-gray-50'
})

// ✅ R4: 成色程度底部文字颜色
const conditionGradeTextClass = computed(() => {
  const grade = props.extractResult?.condition_grade?.grade
  if (grade === 0) return 'text-green-700'
  if (grade === 1) return 'text-yellow-700'
  if (grade === 2) return 'text-orange-700'
  if (grade === 3) return 'text-red-700'
  if (grade === 4) return 'text-red-800'
  return 'text-gray-600'
})
</script>