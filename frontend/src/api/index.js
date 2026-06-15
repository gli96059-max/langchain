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

// ── Recipe Library ────────────────────────────────────────────────

export function listRecipes() {
  return request('GET', '/recipes')
}

// ── Dietary Profile ───────────────────────────────────────────────

export function getDietaryProfile() {
  return request('GET', '/dietary-profile')
}

export function updateDietaryProfile(allergies, restrictions, preferences) {
  return request('PUT', '/dietary-profile', { allergies, restrictions, preferences })
}

// ── Favorites ─────────────────────────────────────────────────────

export function listFavorites() {
  return request('GET', '/favorites')
}

export function addFavorite(name, recipeData) {
  return request('POST', '/favorites', { name, recipe_data: recipeData })
}

export function removeFavorite(id) {
  return request('DELETE', `/favorites/${id}`)
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
