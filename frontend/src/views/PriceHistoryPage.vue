<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="relative inline-block">
          <div class="absolute -inset-4 bg-gradient-to-r from-primary-400/30 to-accent-400/30 rounded-3xl blur-xl -z-10"></div>
          <h1 class="text-3xl sm:text-4xl font-bold gradient-text">历史价格</h1>
        </div>
        <p class="text-text-muted text-sm mt-2">
          {{ priceData.brand }} {{ priceData.model }} · 过去6个月价格走势
        </p>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="glass-card p-8 text-center">
      <div class="loading-spinner mx-auto mb-4" style="width: 40px; height: 40px; border-width: 3px;" />
      <p class="text-text-muted">正在获取历史价格...</p>
    </div>

    <!-- 无数据 -->
    <div v-else-if="!hasData" class="glass-card p-12 text-center">
      <div class="relative inline-block mb-6">
        <div class="absolute -inset-4 bg-gradient-to-br from-warning-400/30 to-accent-400/30 rounded-2xl blur-lg -z-10"></div>
        <div class="w-24 h-24 rounded-full bg-surface-secondary flex items-center justify-center">
          <span class="text-5xl">📊</span>
        </div>
      </div>
      <p class="text-text-secondary font-medium text-lg">暂无价格数据</p>
      <p class="text-text-muted text-sm mt-2">请先在发布页面确认商品信息后再查看</p>
    </div>

    <!-- 价格分析结果 -->
    <div v-else>
      <!-- 统计卡片 -->
      <div class="grid grid-cols-3 gap-4">
        <div class="stat-card">
          <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-accent-100 flex items-center justify-center">
            <span class="text-accent-600 text-sm">💰</span>
          </div>
          <p class="stat-value text-accent-600">¥{{ formatPrice(priceData.avg_price) }}</p>
          <p class="stat-label">平均价格</p>
        </div>
        <div class="stat-card">
          <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-green-100 flex items-center justify-center">
            <span class="text-green-600 text-sm">📉</span>
          </div>
          <p class="stat-value text-green-600">¥{{ formatPrice(priceData.min_price) }}</p>
          <p class="stat-label">最低价格</p>
        </div>
        <div class="stat-card">
          <div class="w-8 h-8 mx-auto mb-2 rounded-lg bg-red-100 flex items-center justify-center">
            <span class="text-red-600 text-sm">📈</span>
          </div>
          <p class="stat-value text-red-600">¥{{ formatPrice(priceData.max_price) }}</p>
          <p class="stat-label">最高价格</p>
        </div>
      </div>

      <!-- 价格趋势图表 -->
      <div class="glass-card p-6">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-xl font-bold text-text-primary">{{ priceData.brand }} {{ priceData.model }}</h2>
            <p class="text-sm text-text-muted mt-1">价格趋势曲线（过去6个月 · {{ chartPoints.length }}个数据点）</p>
          </div>
          <div class="flex gap-2">
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              :class="chartView === 'line' ? 'bg-primary-100 text-primary-700' : 'bg-surface-secondary text-text-secondary hover:bg-primary-50'"
              @click="chartView = 'line'"
            >
              趋势图
            </button>
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              :class="chartView === 'bar' ? 'bg-primary-100 text-primary-700' : 'bg-surface-secondary text-text-secondary hover:bg-primary-50'"
              @click="chartView = 'bar'"
            >
              柱状图
            </button>
          </div>
        </div>

        <!-- SVG 图表 -->
        <div class="relative" style="height: 420px;">
          <svg
            :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
            class="w-full h-full"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.25" />
                <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.02" />
              </linearGradient>
              <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.9" />
                <stop offset="100%" stop-color="#7c3aed" stop-opacity="0.5" />
              </linearGradient>
              <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#7c3aed" />
                <stop offset="50%" stop-color="#8b5cf6" />
                <stop offset="100%" stop-color="#a78bfa" />
              </linearGradient>
            </defs>

            <!-- 网格线 -->
            <g>
              <line v-for="(tick, i) in yTicks" :key="'h-' + i"
                :x1="pad.l" :y1="yPos(tick.value)" :x2="chartWidth - pad.r" :y2="yPos(tick.value)"
                stroke="#e4e4e7" stroke-width="1" stroke-dasharray="4,4" />
            </g>

            <!-- Y轴 -->
            <g>
              <text v-for="(tick, i) in yTicks" :key="'yl-' + i"
                :x="pad.l - 8" :y="yPos(tick.value) + 4"
                text-anchor="end" class="axis-label">¥{{ formatPrice(tick.value) }}</text>
            </g>

            <!-- X轴 -->
            <g>
              <text v-for="(tick, i) in xTicks" :key="'xl-' + i"
                :x="xPos(tick.index)" :y="chartHeight - pad.b + 18"
                text-anchor="middle" class="axis-label">{{ tick.label }}</text>
            </g>

            <!-- 柱状图 -->
            <g v-if="chartView === 'bar'">
              <rect v-for="(pt, i) in chartPoints" :key="'bar-' + i"
                :x="barX(i)" :y="yPos(pt.price)"
                :width="barW" :height="yPos(baseline) - yPos(pt.price)"
                :fill="barColor(pt.price)"
                rx="1"
                class="bar-rect"
                @mouseenter="hovered = pt; hoverIdx = i"
                @mouseleave="hovered = null" />
            </g>

            <!-- 折线图-填充 -->
            <path v-if="chartView === 'line'" :d="areaPath" fill="url(#areaGrad)" />

            <!-- 折线图-曲线 -->
            <path v-if="chartView === 'line'" :d="smoothPath"
              fill="none" stroke="url(#lineGrad)"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

            <!-- 数据点 -->
            <g v-if="chartView === 'line'">
              <circle v-for="(pt, i) in chartPoints" :key="'pt-' + i"
                :cx="xPos(i)" :cy="yPos(pt.price)"
                :r="hoverIdx === i ? 5 : (i % 15 === 0 ? 3 : 0)"
                :fill="hoverIdx === i ? '#8b5cf6' : '#fff'"
                :stroke="hoverIdx === i ? '#7c3aed' : '#a78bfa'"
                :stroke-width="hoverIdx === i ? 2.5 : 1.5"
                class="data-point"
                @mouseenter="hovered = pt; hoverIdx = i"
                @mouseleave="hovered = null" />
            </g>

            <!-- Tooltip -->
            <g v-if="hovered" :transform="`translate(${tooltipX}, ${tooltipY})`">
              <rect x="-70" y="-48" width="140" height="42" rx="8"
                fill="rgba(24,24,27,0.92)" stroke="#8b5cf6" stroke-width="1" />
              <text x="0" y="-26" text-anchor="middle" fill="#fff" font-size="11">{{ hovered.date }}</text>
              <text x="0" y="-6" text-anchor="middle" fill="#c4b5fd" font-size="13" font-weight="bold">¥{{ formatPrice(hovered.price) }}</text>
            </g>
          </svg>
        </div>

        <!-- 图例 -->
        <div class="flex items-center justify-center gap-6 mt-4 text-xs text-text-muted">
          <div class="flex items-center gap-1.5">
            <div class="w-4 h-0.5 rounded" style="background: #8b5cf6"></div>
            <span>价格走势</span>
          </div>
          <div class="flex items-center gap-1.5">
            <div class="w-2.5 h-2.5 rounded-full border" style="border-color: #a78bfa; background: #fff"></div>
            <span>数据采样点</span>
          </div>
        </div>

        <!-- 价格区间 -->
        <div class="mt-6 pt-6 border-t border-border">
          <div class="flex items-center gap-4">
            <span class="text-sm text-text-muted flex-shrink-0">价格区间</span>
            <div class="flex-1 relative h-3 bg-gray-100 rounded-full overflow-hidden">
              <div class="absolute top-0 bottom-0 bg-gradient-to-r from-green-400 via-yellow-400 to-red-400 rounded-full" style="width: 100%" />
              <div class="absolute top-1/2 -translate-y-1/2 bg-white border-2 border-primary-500 rounded-full w-4 h-4 shadow-md"
                :style="{ left: avgPosition + '%' }" />
            </div>
          </div>
          <div class="flex justify-between mt-2 text-xs text-text-muted">
            <span>¥{{ formatPrice(priceData.min_price) }}</span>
            <span class="text-primary-600 font-medium">均价 ¥{{ formatPrice(priceData.avg_price) }}</span>
            <span>¥{{ formatPrice(priceData.max_price) }}</span>
          </div>
        </div>

        <!-- 定价建议 -->
        <div class="mt-6 p-4 rounded-xl bg-gradient-to-r from-primary-50 to-accent-50 border border-primary-100">
          <div class="flex items-start gap-3">
            <span class="text-2xl">💡</span>
            <div>
              <p class="text-sm font-medium text-primary-700">定价建议</p>
              <p class="text-sm text-text-secondary mt-1">
                建议售价 <span class="font-bold text-accent-600">¥{{ formatPrice(priceData.avg_price * 0.9) }} - ¥{{ formatPrice(priceData.avg_price * 1.1) }}</span>，
                参考均价 <span class="font-bold">¥{{ formatPrice(priceData.avg_price) }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPriceHistory } from '../api/index.js'

const route = useRoute()

const loading = ref(false)
const hasData = ref(false)
const chartView = ref('line')
const hovered = ref(null)
const hoverIdx = ref(-1)

const priceData = ref({
  brand: '',
  model: '',
  avg_price: 0,
  min_price: 0,
  max_price: 0,
  price_points: [],
})

const chartWidth = 960
const chartHeight = 420
const pad = { t: 20, r: 20, b: 45, l: 70 }
const chartPoints = computed(() => priceData.value.price_points || [])
const count = computed(() => chartPoints.value.length)
const baseline = computed(() => {
  const ticks = yTicks.value
  return ticks.length ? ticks[0].value : 0
})

const yTicks = computed(() => {
  if (!hasData.value) return []
  const min = priceData.value.min_price * 0.88
  const max = priceData.value.max_price * 1.12
  const range = max - min
  if (range < 1) {
    const v = Math.round(min)
    return [{ value: v - 200 }, { value: v }, { value: v + 200 }]
  }
  const step = Math.max(1, Math.ceil(range / 6 / 50) * 50)
  const ticks = []
  for (let v = Math.floor(min / step) * step; v <= Math.ceil(max / step) * step; v += step) {
    ticks.push({ value: v })
  }
  if (ticks.length < 3) {
    const mid = Math.round((min + max) / 2)
    return [{ value: Math.round(min) }, { value: mid }, { value: Math.round(max) }]
  }
  return ticks
})

const xTicks = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return []
  const n = pts.length
  const step = Math.max(1, Math.floor(n / 8))
  const ticks = []
  for (let i = 0; i < n; i += step) {
    ticks.push({ index: i, label: pts[i].date.slice(5) })
  }
  const last = ticks[ticks.length - 1]
  if (last && last.index < n - 2) {
    ticks.push({ index: n - 1, label: pts[n - 1].date.slice(5) })
  }
  return ticks
})

function xPos(i) {
  const pts = chartPoints.value
  if (pts.length <= 1) return pad.l + (chartWidth - pad.l - pad.r) / 2
  return pad.l + (i / (pts.length - 1)) * (chartWidth - pad.l - pad.r)
}

function yPos(v) {
  const ticks = yTicks.value
  if (!ticks.length) return chartHeight / 2
  const tMin = ticks[0].value
  const tMax = ticks[ticks.length - 1].value
  const range = tMax - tMin || 1
  return pad.t + ((tMax - v) / range) * (chartHeight - pad.t - pad.b)
}

const barW = computed(() => {
  const n = count.value
  if (!n) return 0
  const tw = chartWidth - pad.l - pad.r
  return Math.max(2, tw / n - 1)
})

function barX(i) {
  const n = count.value
  if (!n) return 0
  const tw = chartWidth - pad.l - pad.r
  return pad.l + i * (tw / n)
}

function barColor(price) {
  const max = priceData.value.max_price || 1
  const min = priceData.value.min_price || 0
  const ratio = (price - min) / (max - min || 1)
  if (ratio < 0.4) return '#22c55e'
  if (ratio < 0.7) return '#eab308'
  return '#ef4444'
}

// 平滑曲线（Catmull-Rom → Cubic Bezier）
const smoothPath = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return ''
  if (pts.length === 1) {
    const x = xPos(0), y = yPos(pts[0].price)
    return `M ${x},${y}`
  }
  if (pts.length === 2) {
    return `M ${xPos(0)},${yPos(pts[0].price)} L ${xPos(1)},${yPos(pts[1].price)}`
  }

  const points = pts.map((p, i) => ({ x: xPos(i), y: yPos(p.price) }))
  let d = `M ${points[0].x},${points[0].y}`

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[Math.min(points.length - 1, i + 2)]

    const t = 0.35
    const cp1x = p1.x + (p2.x - p0.x) * t / 3
    const cp1y = p1.y + (p2.y - p0.y) * t / 3
    const cp2x = p2.x - (p3.x - p1.x) * t / 3
    const cp2y = p2.y - (p3.y - p1.y) * t / 3

    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`
  }
  return d
})

const areaPath = computed(() => {
  if (!smoothPath.value) return ''
  const lastX = xPos(count.value - 1)
  const baseY = yPos(baseline.value)
  const firstX = xPos(0)
  return `${smoothPath.value} L ${lastX},${baseY} L ${firstX},${baseY} Z`
})

const avgPosition = computed(() => {
  const range = priceData.value.max_price - priceData.value.min_price || 1
  return ((priceData.value.avg_price - priceData.value.min_price) / range) * 100
})

const tooltipX = computed(() => {
  if (!hovered.value) return 0
  const idx = chartPoints.value.indexOf(hovered.value)
  return Math.min(chartWidth - pad.r - 70, Math.max(pad.l + 70, xPos(idx)))
})

const tooltipY = computed(() => {
  if (!hovered.value) return 0
  return Math.max(pad.t + 48, yPos(hovered.value.price) - 48)
})

const brand = ref('')
const model = ref('')
const basePrice = ref(0)

function formatPrice(v) {
  if (!v || isNaN(v)) return '0'
  return Math.round(v).toLocaleString()
}

async function loadData() {
  if (!brand.value || !model.value) return
  loading.value = true
  try {
    const data = await getPriceHistory(brand.value, model.value, 180, basePrice.value)
    priceData.value = data
    hasData.value = data.price_points && data.price_points.length > 0
  } catch (e) {
    console.error('Failed to load price history:', e)
    hasData.value = false
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (route.query.brand) brand.value = decodeURIComponent(route.query.brand)
  if (route.query.model) model.value = decodeURIComponent(route.query.model)
  if (route.query.price) basePrice.value = parseFloat(route.query.price) || 0
  if (brand.value && model.value) loadData()
})
</script>

<style scoped>
.axis-label {
  fill: #a1a1aa;
  font-size: 10px;
  font-family: 'Inter', sans-serif;
}

.data-point {
  cursor: pointer;
  transition: all 0.15s ease;
}

.bar-rect {
  transition: opacity 0.15s ease;
  cursor: pointer;
}

.bar-rect:hover {
  opacity: 0.8;
}
</style>
