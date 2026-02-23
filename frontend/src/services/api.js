const BASE = '/api'

export async function fetchCompanies() {
  const res = await fetch(`${BASE}/companies`)
  return res.json()
}

export async function fetchHistory(limit = 100) {
  const res = await fetch(`${BASE}/chat/history?limit=${limit}`)
  return res.json()
}

export async function saveHistoryEntry(entry) {
  return fetch(`${BASE}/chat/history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
}

export async function deleteHistory(ids) {
  return fetch(`${BASE}/chat/history`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
}

export async function fetchProfile(taxpayerId, year) {
  const res = await fetch(`${BASE}/profile/${taxpayerId}?year=${year}`)
  if (!res.ok) throw new Error(`Profile fetch failed: ${res.status}`)
  return res.json()
}

/**
 * POST /api/chat with SSE streaming.
 * Returns the raw Response for SSE parsing.
 */
export function chatStream(query, signal, { responseMode, companyId } = {}) {
  return fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      response_mode: responseMode || 'detailed',
      company_id: companyId || '',
    }),
    signal,
  })
}
