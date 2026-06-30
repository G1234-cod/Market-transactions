/**
 * 前端 API 封装层
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// ✅ 获取 Token（返回空字符串而非 null）
function getToken() {
  const token = localStorage.getItem('token')
  return token || ''
}

// ✅ 获取认证请求头（只有 token 存在时才添加）
function getAuthHeaders() {
  const token = getToken()
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// ============================================================
// 用户
// ============================================================
export async function login(username, password) {
  const { data } = await api.post('/login', { username, password })
  if (data.access_token) {
    localStorage.setItem('token', data.access_token)
  }
  return data
}

export async function register(username, password, role = 'user') {
  const { data } = await api.post('/register', { username, password, role })
  return data
}

// ============================================================
// 图片提取
// ============================================================
export async function extractImage(file) {
  const form = new FormData()
  form.append('image', file)
  const { data } = await api.post('/extract', form, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

// ============================================================
// ✅ 查价（携带认证）
// ============================================================
export async function queryPrice(brand, model) {
  const { data } = await api.get('/price', {
    params: { brand, model },
    headers: {
      ...getAuthHeaders(),  // ✅ 新增认证
    }
  })
  return data
}

// ============================================================
// ✅ 流式生成文案 (SSE) - 使用 axios baseURL
// ============================================================
export function generateStream(payload) {
  const controller = new AbortController()
  const signal = controller.signal
  let isAborted = false

  const authHeaders = getAuthHeaders()

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // ✅ 使用 axios 的 baseURL
        const url = `${api.defaults.baseURL}/generate`
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
          },
          body: JSON.stringify(payload),
          signal,
        })

        if (!resp.ok) {
          const errorText = await resp.text()
          controller.error(new Error(`HTTP ${resp.status}: ${errorText}`))
          return
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          if (isAborted) break
          const { done, value } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                controller.enqueue(data)
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }
      } catch (e) {
        if (e.name === 'AbortError') {
          console.debug('SSE 请求已被取消')
          controller.close()
          return
        }
        controller.error(e)
      } finally {
        controller.close()
      }
    },
  })

  return {
    stream,
    abort() {
      isAborted = true
      controller.abort()
    }
  }
}

// ============================================================
// 发布历史
// ============================================================
export async function getHistory(userId) {
  const { data } = await api.get('/history', { 
    params: { user_id: userId },
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data.items || []
}

export async function saveHistory(payload) {
  const { data } = await api.post('/history/save', payload, {
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data
}

export async function delistItem(id) {
  const { data } = await api.post(`/history/${id}/delist`, {}, {
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data
}

export async function publishItem(id) {
  const { data } = await api.post(`/history/${id}/publish`, {}, {
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data
}


// ============================================================
// 商城（分页 + 排序 + 多维筛选）
// ============================================================
export async function getMarket({
  keyword = '',
  category = '',
  condition = '',
  priceMin = null,
  priceMax = null,
  sortBy = 'created_at',
  sortOrder = 'desc',
  page = 1,
  pageSize = 20,
} = {}) {
  const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
  if (keyword) params.keyword = keyword
  if (category) params.category = category
  if (condition) params.condition = condition
  if (priceMin != null) params.price_min = priceMin
  if (priceMax != null) params.price_max = priceMax

  const { data } = await api.get('/market', { params })
  return data   // { total, page, page_size, total_pages, items }
}

// ============================================================
// 价格历史
// ============================================================
export async function getPriceHistory(brand, model, days = 90, basePrice = 0) {
  const params = { brand, model, days }
  if (basePrice > 0) params.base_price = basePrice
  const { data } = await api.get('/price-history', {
    params,
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data
}

export async function getAvailableModels(keyword = '', category = '') {
  const { data } = await api.get('/price-history/models', {
    params: { keyword, category },
    headers: {
      ...getAuthHeaders(),
    }
  })
  return data
}

// ============================================================
// 以图搜图 & 以文搜图
// ============================================================
export async function searchByImage(formData) {
  const token = getToken()
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
  
  const resp = await fetch('/api/v1/search/image', {
    method: 'POST',
    headers,
    body: formData
  })
  
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '搜索失败' }))
    throw new Error(error.detail || '搜索失败')
  }
  
  return resp.json()
}

export async function searchSemantic(text, topK = 10) {
  const formData = new FormData()
  formData.append('text', text)
  formData.append('top_k', topK.toString())
  const resp = await fetch('/api/v1/search/semantic', {
    method: 'POST',
    body: formData
  })
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '搜索失败' }))
    throw new Error(error.detail || '搜索失败')
  }
  return resp.json()
}

export async function searchByText(params) {
  const formData = new FormData()
  formData.append('text', params.text)
  formData.append('top_k', params.top_k?.toString() || '10')
  if (params.category) {
    formData.append('category', params.category)
  }
  
  const token = getToken()
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
  
  const resp = await fetch('/api/v1/search/text', {
    method: 'POST',
    headers,
    body: formData
  })
  
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '搜索失败' }))
    throw new Error(error.detail || '搜索失败')
  }
  
  return resp.json()
}

// ============================================================
// 双模型协同识别
// ============================================================
export async function recognizeImage(imageFile) {
  const formData = new FormData()
  formData.append('image', imageFile)
  
  const token = getToken()
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
  
  const resp = await fetch('/api/v1/recognize', {
    method: 'POST',
    headers,
    body: formData
  })
  
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '识别失败' }))
    throw new Error(error.detail || '识别失败')
  }
  
  return resp.json()
}

export async function getRecognitionCategories() {
  const resp = await fetch('/api/v1/recognize/categories')
  if (!resp.ok) {
    throw new Error('获取类别失败')
  }
  return resp.json()
}

// ============================================================
// 管理员接口
// ============================================================
export async function getAdminSystemStats() {
  const { data } = await api.get('/admin/system/stats', {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function testModel(formData) {
  const { data } = await api.post('/admin/test-model', formData, {
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'multipart/form-data'
    }
  })
  return data
}

export async function getAdminReviewItems(params = {}) {
  const { data } = await api.get('/admin/items/review', {
    params,
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function forceDelistItem(itemId, reason) {
  const { data } = await api.post(`/admin/items/${itemId}/force-delist`, { reason }, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function getAdminModelMetrics(params = {}) {
  const { data } = await api.get('/admin/model/metrics', {
    params,
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function getCheckpointMetrics() {
  const { data } = await api.get('/admin/model/checkpoint-metrics', {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function triggerModelTraining(modelName, epochs) {
  const { data } = await api.post('/admin/model/train', null, {
    params: { model_name: modelName, epochs },
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function getTrainingStatus() {
  const { data } = await api.get('/admin/model/train/status', {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function getAdminHardCases(params = {}) {
  const { data } = await api.get('/admin/hard-cases', {
    params,
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function markHardCaseFixed(caseId) {
  const { data } = await api.post(`/admin/hard-cases/${caseId}/mark-fixed`, {}, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

// ============================================================
// 管理员用户管理
// ============================================================
export async function getAdminUsers(role = '') {
  const { data } = await api.get('/admin/users', {
    params: role ? { role } : {},
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function createAdminUser(username, password, role = 'user') {
  const { data } = await api.post('/admin/users', { username, password, role }, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function deleteAdminUser(userId) {
  const { data } = await api.delete(`/admin/users/${userId}`, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function syncQdrant() {
  const { data } = await api.post('/admin/sync-qdrant', {}, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function toggleUserStatus(userId) {
  const { data } = await api.post(`/admin/users/${userId}/toggle-status`, {}, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

// ============================================================
// 通知接口
// ============================================================
export async function getNotifications() {
  const { data } = await api.get('/notifications', {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function markNotificationRead(notificationId) {
  const { data } = await api.post(`/notifications/${notificationId}/read`, {}, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function markAllNotificationsRead() {
  const { data } = await api.post('/notifications/read-all', {}, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

// ============================================================
// 按类别/品牌/型号直接搜索（数据库查询）
// ============================================================
export async function searchByFilter({ category, brand, model, page = 1, pageSize = 20 } = {}) {
  const formData = new FormData()
  if (category) formData.append('category', category)
  if (brand) formData.append('brand', brand)
  if (model) formData.append('model', model)
  formData.append('page', page.toString())
  formData.append('page_size', pageSize.toString())

  const resp = await fetch('/api/v1/search/by-filter', {
    method: 'POST',
    body: formData
  })

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '搜索失败' }))
    throw new Error(error.detail || '搜索失败')
  }

  return resp.json()
}

// ============================================================
// 获取品类和品牌（级联选择器）
// ============================================================
export async function getAdminCategories() {
  const { data } = await api.get('/admin/categories', {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function addAdminCategory(category, brand) {
  const { data } = await api.post('/admin/categories/add', { category, brand }, {
    headers: { ...getAuthHeaders() }
  })
  return data
}

export async function getCategoriesAndBrands(category = null) {
  const params = category ? `?category=${encodeURIComponent(category)}` : ''
  const resp = await fetch(`/api/v1/search/categories-brands${params}`)
  if (!resp.ok) throw new Error('获取品类失败')
  return resp.json()
}

export async function getSearchAvailableModels(category = null, brand = null) {
  const params = new URLSearchParams()
  if (category) params.append('category', category)
  if (brand) params.append('brand', brand)
  const resp = await fetch(`/api/v1/search/available-models?${params.toString()}`)
  if (!resp.ok) throw new Error('获取型号列表失败')
  return resp.json()
}

// ============================================================
// 添加到索引
// ============================================================
export async function addToIndex(itemId, imageUrl, title = '', category = '') {
  const formData = new FormData()
  formData.append('item_id', itemId.toString())
  formData.append('image_url', imageUrl)
  formData.append('title', title)
  formData.append('category', category)

  const token = getToken()
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}

  const resp = await fetch('/api/v1/search/index', {
    method: 'POST',
    headers,
    body: formData
  })

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: '操作失败' }))
    throw new Error(error.detail || '操作失败')
  }

  return resp.json()
}

export async function searchStats() {
  const resp = await fetch('/api/v1/search/stats')
  if (!resp.ok) throw new Error('获取统计失败')
  return resp.json()
}

// ============================================================
// Axios 拦截器（统一处理认证）
// ============================================================

api.interceptors.request.use(
  (config) => {
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json'
    }
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ✅ 修复：防止多次 401 并发重定向竞态
let _redirecting = false

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      // ✅ 只有当请求携带了 token 时才视为"登录态过期"
      // 避免公开接口偶发 401 时误伤已登录用户
      const hadAuth = !!error.config?.headers?.['Authorization']
      if (!hadAuth) {
        console.warn('[Auth] 公开接口返回 401（未携带 token），忽略退出登录')
        return Promise.reject(error)
      }

      console.warn('[Auth] 检测到 401，token 已过期或无效，正在退出登录...')
      localStorage.removeItem('token')
      localStorage.removeItem('user_info')

      if (!_redirecting && window.location.pathname !== '/login') {
        _redirecting = true
        // ✅ 30 秒后重置标记，防止用户手动回到登录页后标记不重置
        setTimeout(() => { _redirecting = false }, 30000)
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)