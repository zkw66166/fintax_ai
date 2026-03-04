const BASE = '/api'

function authHeaders(extra = {}) {
  const token = localStorage.getItem('access_token')
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchCompanies() {
  const res = await fetch(`${BASE}/companies`, { headers: authHeaders() })
  return res.json()
}

export async function fetchHistory(limit = 100) {
  const res = await fetch(`${BASE}/chat/history?limit=${limit}`, { headers: authHeaders() })
  return res.json()
}

export async function saveHistoryEntry(entry) {
  return fetch(`${BASE}/chat/history`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(entry),
  })
}

export async function deleteHistory(ids) {
  return fetch(`${BASE}/chat/history`, {
    method: 'DELETE',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ids }),
  })
}

/**
 * POST /api/chat/history/reinvoke with SSE streaming.
 * Re-invokes a query from history with specified thinking mode.
 * Returns the raw Response for SSE parsing.
 */
export function reinvokeFromHistory(historyIndex, thinkingMode, signal) {
  const payload = {
    history_index: historyIndex,
    thinking_mode: thinkingMode || 'quick',
  }
  return fetch(`${BASE}/chat/history/reinvoke`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
    signal,
  })
}

export async function fetchProfile(taxpayerId, year) {
  const res = await fetch(`${BASE}/profile/${taxpayerId}?year=${year}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Profile fetch failed: ${res.status}`)
  return res.json()
}

/**
 * POST /api/chat with SSE streaming.
 * Returns the raw Response for SSE parsing.
 */
export function chatStream(query, signal, { responseMode, companyId, thinkingMode, conversationHistory, conversationDepth } = {}) {
  const payload = {
    query,
    response_mode: responseMode || 'detailed',
    company_id: companyId || '',
    thinking_mode: thinkingMode || 'quick',
  }

  // Add conversation history if provided
  if (conversationHistory && conversationHistory.length > 0) {
    payload.conversation_history = conversationHistory
    payload.conversation_depth = conversationDepth || 3
  }

  return fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
    signal,
  })
}

/**
 * POST /api/chat/interpret with SSE streaming.
 * Returns the raw Response for SSE parsing.
 */
export function interpretStream(query, result, signal, { responseMode, companyId, cacheKey } = {}) {
  return fetch(`${BASE}/chat/interpret`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query,
      result,
      response_mode: responseMode || 'detailed',
      company_id: companyId || '',
      cache_key: cacheKey || '',
    }),
    signal,
  })
}
