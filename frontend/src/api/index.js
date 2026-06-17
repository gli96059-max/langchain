const BASE = '/api'

let _token = localStorage.getItem('token') || null

export function setToken(token) {
  _token = token
  if (token) {
    localStorage.setItem('token', token)
  } else {
    localStorage.removeItem('token')
  }
}

export function getToken() {
  return _token
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (_token) {
    opts.headers['Authorization'] = `Bearer ${_token}`
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  if (res.status === 401) {
    // Token expired or invalid — clear and let App handle redirect
    setToken(null)
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    throw new Error('未登录，请重新登录')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────

export function register(username, password) {
  return request('POST', '/auth/register', { username, password })
}

export function login(username, password) {
  return request('POST', '/auth/login', { username, password })
}

// ── Sessions ──────────────────────────────────────────────────────────────

export function createSession() {
  return request('POST', '/sessions')
}

export function listSessions() {
  return request('GET', '/sessions')
}

export function getSession(id) {
  return request('GET', `/sessions/${id}`)
}

export function deleteSession(id) {
  return request('DELETE', `/sessions/${id}`)
}

export function updateSessionTitle(id, title) {
  return request('PUT', `/sessions/${id}`, { message: title })
}

export function batchDeleteSessions(ids) {
  return request('POST', '/sessions/batch-delete', { ids })
}

// ── Recipe Library ────────────────────────────────────────────────────────

export function listRecipes(params = {}) {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.ingredient) qs.set('ingredient', params.ingredient)
  if (params.cuisine_type) qs.set('cuisine_type', params.cuisine_type)
  if (params.taste) qs.set('taste', params.taste)
  const query = qs.toString()
  return request('GET', `/recipes${query ? '?' + query : ''}`)
}

export function deleteRecipe(id) {
  return request('DELETE', `/recipes/${id}`)
}

export function batchDeleteRecipes(ids) {
  return request('POST', '/recipes/batch-delete', { ids })
}

// ── Shopping Lists ─────────────────────────────────────────────

export function listShoppingLists() {
  return request('GET', '/shopping-lists')
}

export function getShoppingList(id) {
  return request('GET', `/shopping-lists/${id}`)
}

export function saveShoppingList(name, sessionId, items) {
  return request('POST', '/shopping-lists', { name, session_id: sessionId, items })
}

export function updateShoppingList(id, items) {
  return request('PUT', `/shopping-lists/${id}`, { items })
}

export function deleteShoppingList(id) {
  return request('DELETE', `/shopping-lists/${id}`)
}

// ── Dietary Profile ───────────────────────────────────────────────────────

export function getDietaryProfile() {
  return request('GET', '/dietary-profile')
}

export function updateDietaryProfile(allergies, restrictions, preferences, difficulty_preference = '') {
  return request('PUT', '/dietary-profile', { allergies, restrictions, preferences, difficulty_preference })
}

// ── Recipe library save ───────────────────────────────────────────────────

export function saveRecipe(sessionId, recipeData) {
  return request('POST', '/recipes', { name: recipeData.name || '', session_id: sessionId, recipe_data: recipeData })
}

// ── Image upload ──────────────────────────────────────────────────────────

export async function uploadImage(base64Data) {
  return request('POST', '/upload', { image_base64: base64Data })
}

// ── Chat (SSE streaming) ──────────────────────────────────────────────────

export function chatStream(sessionId, message, imageBase64) {
  const body = { message }
  if (imageBase64) body.image_base64 = imageBase64

  const headers = { 'Content-Type': 'application/json' }
  if (_token) {
    headers['Authorization'] = `Bearer ${_token}`
  }

  // Abort after 120s to prevent hanging
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 120_000)

  return fetch(`${BASE}/chat/${sessionId}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal: controller.signal,
  }).finally(() => clearTimeout(timer))
}

/**
 * Parse SSE stream from a fetch Response.
 * Yields { event, data } objects.
 */
export async function* readSSE(response) {
  if (!response.body) {
    // Fallback for browsers without ReadableStream support
    const text = await response.text()
    for (const { event, data } of parseSSEText(text)) {
      yield { event, data }
    }
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let eventType = ''
    let dataRaw = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        dataRaw = line.slice(6)
      } else if (line === '' && eventType && dataRaw) {
        try {
          yield { event: eventType, data: JSON.parse(dataRaw) }
        } catch { /* skip malformed */ }
        eventType = ''
        dataRaw = ''
      }
    }
  }

  // Flush remaining buffer
  if (buffer.trim()) {
    for (const { event, data } of parseSSEText(buffer)) {
      yield { event, data }
    }
  }
}

function* parseSSEText(text) {
  const blocks = text.split('\n\n')
  for (const block of blocks) {
    if (!block.trim()) continue
    const lines = block.split('\n')
    let eventType = ''
    let dataRaw = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) eventType = line.slice(7).trim()
      else if (line.startsWith('data: ')) dataRaw = line.slice(6)
    }
    if (eventType && dataRaw) {
      try {
        yield { event: eventType, data: JSON.parse(dataRaw) }
      } catch { /* skip */ }
    }
  }
}
