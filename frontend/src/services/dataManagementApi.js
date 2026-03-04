const BASE = '/api'

function authHeaders(extra = {}) {
  const token = localStorage.getItem('access_token')
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchStats(companyId) {
  const res = await fetch(
    `${BASE}/data-management/stats?company_id=${encodeURIComponent(companyId)}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error(`Stats fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchCompaniesOverview() {
  const res = await fetch(`${BASE}/data-management/companies-overview`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Companies overview fetch failed: ${res.status}`)
  return res.json()
}

export async function runQualityCheck(companyId) {
  const res = await fetch(
    `${BASE}/data-management/quality-check?company_id=${encodeURIComponent(companyId)}`,
    { method: 'POST', headers: authHeaders() },
  )
  if (!res.ok) throw new Error(`Quality check failed: ${res.status}`)
  return res.json()
}

export async function fetchBrowseTables(companyId) {
  const res = await fetch(
    `${BASE}/data-browser/tables?company_id=${encodeURIComponent(companyId)}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error(`Tables fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchBrowsePeriods(companyId, domain) {
  const res = await fetch(
    `${BASE}/data-browser/periods?company_id=${encodeURIComponent(companyId)}&domain=${encodeURIComponent(domain)}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error(`Periods fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchBrowseData(companyId, domain, period, format) {
  const params = new URLSearchParams({
    company_id: companyId,
    domain,
    period: period || 'all',
    format: format || 'general',
  })
  const res = await fetch(`${BASE}/data-browser/data?${params}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Data fetch failed: ${res.status}`)
  return res.json()
}

/**
 * 重新计算财务指标
 * @param {string} companyId - 纳税人ID
 * @param {string} version - 指标版本 ('v1'|'v2'|'both')
 * @returns {Promise<{success: boolean, message: string, details: object}>}
 */
export async function recalculateMetrics(companyId, version = 'both') {
  const response = await fetch(
    `${BASE}/data-management/recalculate-metrics?company_id=${encodeURIComponent(companyId)}&version=${version}`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '重算失败')
  }

  return response.json()
}

/**
 * 批量重新计算所有企业的财务指标
 * @param {string} version - 指标版本 ('v1'|'v2'|'both')
 * @returns {Promise<{success: boolean, message: string, details: object}>}
 */
export async function recalculateMetricsAll(version = 'both') {
  const response = await fetch(
    `${BASE}/data-management/recalculate-metrics-all?version=${version}`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '批量重算失败')
  }

  return response.json()
}

/**
 * 重新加载参考数据（同义词表、科目字典等）
 * @returns {Promise<{success: boolean, message: string, affected_tables: array, duration_seconds: number}>}
 */
export async function reloadReferenceData() {
  const response = await fetch(
    `${BASE}/data-management/reload-reference-data`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '参考数据重载失败')
  }

  return response.json()
}

/**
 * 批量数据质量检查
 * @param {string} taxpayerIds - 纳税人ID列表（逗号分隔）或 'all'
 * @returns {Promise<{success: boolean, total_taxpayers: number, results: object, summary: object}>}
 */
export async function batchQualityCheck(taxpayerIds = 'all') {
  const response = await fetch(
    `${BASE}/data-management/batch-quality-check?taxpayer_ids=${encodeURIComponent(taxpayerIds)}`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '批量质量检查失败')
  }

  return response.json()
}

/**
 * 清空内存缓存
 * @param {string} cacheTypes - 缓存类型 ('all', 'intent', 'sql', 'result', 'cross_domain')
 * @returns {Promise<{success: boolean, cleared_entries: object, message: string}>}
 */
export async function clearCache(cacheTypes = 'all') {
  const response = await fetch(
    `${BASE}/data-management/clear-cache?cache_types=${encodeURIComponent(cacheTypes)}`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '缓存清理失败')
  }

  return response.json()
}

/**
 * 重新加载意图路由配置
 * @returns {Promise<{success: boolean, config_version: string, loaded_at: string, message: string}>}
 */
export async function reloadConfig() {
  const response = await fetch(
    `${BASE}/data-management/reload-config`,
    {
      method: 'POST',
      headers: authHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '配置重载失败')
  }

  return response.json()
}
