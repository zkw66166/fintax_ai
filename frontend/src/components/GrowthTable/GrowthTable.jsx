import { Fragment } from 'react'
import s from './GrowthTable.module.css'

const TREND_ICON = { up: '📈', down: '📉', stable: '➡️', unknown: '-' }

export default function GrowthTable({ growth }) {
  if (!growth || growth.length === 0) return null

  // Collect all metric names from growth entries
  const metricNames = []
  for (const entry of growth) {
    for (const key of Object.keys(entry)) {
      if (key !== 'period' && !metricNames.includes(key)) metricNames.push(key)
    }
  }

  const fmtVal = (v) => {
    if (v == null) return '-'
    if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
    if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(2)}万`
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  const fmtPct = (v) => {
    if (v == null) return '-'
    const sign = v > 0 ? '+' : ''
    return `${sign}${v.toFixed(2)}%`
  }

  return (
    <div className={s.wrap}>
      <div className={s.title}>环比变动分析</div>
      <div className={s.tableWrap}>
        <table className={s.table}>
          <thead>
            <tr>
              <th>期间</th>
              {metricNames.map((m) => (
                <th key={m} colSpan={3}>{m}</th>
              ))}
            </tr>
            <tr>
              <th></th>
              {metricNames.map((m) => (
                <Fragment key={m}>
                  <th className={s.sub}>本期</th>
                  <th className={s.sub}>变动额</th>
                  <th className={s.sub}>变动率</th>
                </Fragment>
              ))}
            </tr>
          </thead>
          <tbody>
            {growth.map((row, i) => (
              <tr key={i}>
                <td>{row.period}</td>
                {metricNames.map((m) => {
                  const d = row[m] || {}
                  const trendCls = d.trend === 'up' ? s.up : d.trend === 'down' ? s.down : ''
                  return (
                    <Fragment key={m}>
                      <td className={s.num}>{fmtVal(d.current)}</td>
                      <td className={`${s.num} ${trendCls}`}>
                        {d.change != null ? fmtVal(d.change) : '-'}
                      </td>
                      <td className={`${s.num} ${trendCls}`}>
                        {TREND_ICON[d.trend] || ''} {fmtPct(d.change_pct)}
                      </td>
                    </Fragment>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
