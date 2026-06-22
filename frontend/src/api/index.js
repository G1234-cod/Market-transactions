/**
 * 前端 API 封装层
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// ============================================================
// 用户
// ============================================================
export async function login(username, password) {
  const { data } = await api.post('/login', { username, password })
  return data // { id, username }
}

export async function register(username, password) {
  const { data } = await api.post('/register', { username, password })
  return data
}

// ============================================================
// 图片提取
// ============================================================
export async function extractImage(file, userId = 1) {
  const form = new FormData()
  form.append('image', file)
  form.append('user_id', String(userId))
  const { data } = await api.post('/extract', form)
  return data
}

// ============================================================
// 查价
// ============================================================
export async function queryPrice(brand, model) {
  const { data } = await api.get('/price', { params: { brand, model } })
  return data
}

// ============================================================
// 流式生成文案 (SSE)
// ============================================================
export function generateStream(payload) {
  let aborted = false
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const resp = await fetch('/api/v1/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        while (true) {
          if (aborted) break
          const { done, value } = await reader.read()
          if (done) break
          const text = decoder.decode(value, { stream: true })
          for (const line of text.split('\n')) {
            if (line.startsWith('data: ')) {
              controller.enqueue(JSON.parse(line.slice(6)))
            }
          }
        }
      } catch (e) {
        controller.error(e)
      } finally {
        controller.close()
      }
    },
  })
  return { stream, abort() { aborted = true } }
}

// ============================================================
// 发布历史
// ============================================================
export async function getHistory(userId) {
  const { data } = await api.get('/history', { params: { user_id: userId } })
  return data.items || []
}
export async function saveHistory(payload) {
  const { data } = await api.post('/history/save', payload)
  return data
}
export async function delistItem(id) {
  const { data } = await api.post(`/history/${id}/delist`)
  return data
}
export async function publishItem(id) {
  const { data } = await api.post(`/history/${id}/publish`)
  return data
}

// ============================================================
// 商城
// ============================================================
export async function getMarket(keyword = '', category = '') {
  const { data } = await api.get('/market', { params: { keyword, category } })
  return data.items || []
}
