import c from './rawCommon.module.css'
import s from './BalanceSheetRaw.module.css'
import { formatAmount } from './rawUtils'

export default function BalanceSheetRaw({ data }) {
  if (!data) return <div className={c.empty}>暂无数据</div>

  const rawLeft = data.left_items || []
  const rawRight = data.right_items || []

  const isGrandTotal = (item) =>
    item && item.item_name && (item.item_name.includes('总计') || item.item_name.includes('资产合计'))

  // Pad the shorter side so both grand-total rows align on the same row
  const padToAlign = (shorter, longer) => {
    const diff = longer.length - shorter.length
    if (diff <= 0) return shorter
    const last = shorter[shorter.length - 1]
    const body = shorter.slice(0, -1)
    const padding = Array.from({ length: diff }, () => null)
    return [...body, ...padding, last]
  }

  const left = rawLeft.length >= rawRight.length ? rawLeft : padToAlign(rawLeft, rawRight)
  const right = rawRight.length >= rawLeft.length ? rawRight : padToAlign(rawRight, rawLeft)
  const maxLen = Math.max(left.length, right.length)

  return (
    <div className={`${c.rawContainer} ${s.bsContainer}`}>
      <div className={c.reportTitle}>资 产 负 债 表</div>
      <div className={c.headerInfo}>
        <span>编制单位：{data.company_name}</span>
        <span>{data.period_label}</span>
        <span>单位：{data.unit || '元'}</span>
      </div>

      <table className={c.rawTable}>
        <thead>
          <tr>
            <th className={s.colName}>资　　产</th>
            <th className={s.colLine}>行次</th>
            <th className={s.colAmt}>期末余额</th>
            <th className={s.colAmt}>年初余额</th>
            <th className={s.colName}>负债和所有者权益</th>
            <th className={s.colLine}>行次</th>
            <th className={s.colAmt}>期末余额</th>
            <th className={s.colAmt}>年初余额</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: maxLen }, (_, i) => {
            const l = left[i]
            const r = right[i]
            const lTotal = l && l.is_total
            const rTotal = r && r.is_total
            const lGrand = isGrandTotal(l)
            const rGrand = isGrandTotal(r)
            const rowCls = (lGrand || rGrand) ? c.grandTotalRow : (lTotal || rTotal) ? c.totalRow : ''

            return (
              <tr key={i} className={rowCls}>
                <td className={s.nameCell}>{l ? l.item_name : ''}</td>
                <td className={c.alignCenter}>{l ? l.line_number : ''}</td>
                <td className={c.alignRight}>{l ? formatAmount(l.ending_balance) : ''}</td>
                <td className={c.alignRight}>{l ? formatAmount(l.beginning_balance) : ''}</td>
                <td className={s.nameCell}>{r ? r.item_name : ''}</td>
                <td className={c.alignCenter}>{r ? r.line_number : ''}</td>
                <td className={c.alignRight}>{r ? formatAmount(r.ending_balance) : ''}</td>
                <td className={c.alignRight}>{r ? formatAmount(r.beginning_balance) : ''}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
