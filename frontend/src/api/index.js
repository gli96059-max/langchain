const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

// ── Sessions ──────────────────────────────────────────────────────

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

// ── Recipe Library ────────────────────────────────────────────────

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

// ── Shopping Lists ─────────────────────────────────────

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

// ── Dietary Profile ───────────────────────────────────────────────

export function getDietaryProfile() {
  return request('GET', '/dietary-profile')
}

export function updateDietaryProfile(allergies, restrictions, preferences) {
  return request('PUT', '/dietary-profile', { allergies, restrictions, preferences })
}

// ── Recipe library save ───────────────────────────────────────────

export function saveRecipe(sessionId, recipeData) {
  return request('POST', '/recipes', { name: recipeData.name || '', session_id: sessionId, recipe_data: recipeData })
}

// ── Image upload ──────────────────────────────────────────────────

export async function uploadImage(base64Data) {
  return request('POST', '/upload', { image_base64: base64Data })
}

// ── Chat (SSE streaming) ──────────────────────────────────────────

export function chatStream(sessionId, message, imageBase64) {
  const body = { message }
  if (imageBase64) body.image_base64 = imageBase64

  return fetch(`${BASE}/chat/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/**
 * Parse SSE stream from a fetch Response.
 * Yields { event, data } objects.
 */
export async function* readSSE(response) {
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
}
