/**
 * 格式化工具函数
 */

/** 金额格式化：自动万元/亿元缩放 */
export function fmtAmount(val) {
  if (val == null) return '—'
  const abs = Math.abs(val)
  if (abs >= 1e8) return `${(val / 1e8).toFixed(2)}亿`
  if (abs >= 1e4) return `${(val / 1e4).toFixed(2)}万`
  return val.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/** 百分比格式化 */
export function fmtPct(val, digits = 1) {
  if (val == null) return '—'
  return `${Number(val).toFixed(digits)}%`
}

/** 增长率格式化，带正负号 */
export function fmtGrowth(g) {
  if (!g || g.rate == null) return null
  const sign = g.rate > 0 ? '+' : ''
  return `${sign}${g.rate.toFixed(1)}%`
}
