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

export async function register(username, password) {
  const { data } = await api.post('/register', { username, password })
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
          console.log('SSE 请求已被取消')
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
// ✅ Axios 拦截器（统一处理认证）
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

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)