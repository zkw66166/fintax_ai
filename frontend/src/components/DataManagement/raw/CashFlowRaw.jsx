import c from './rawCommon.module.css'
import s from './CashFlowRaw.module.css'
import { formatAmount } from './rawUtils'

export default function CashFlowRaw({ data }) {
  if (!data || !data.items) return <div className={c.empty}>暂无数据</div>

  const items = data.items || []

  return (
    <div className={`${c.rawContainer} ${s.cfContainer}`}>
      <div className={c.reportTitle}>现 金 流 量 表</div>
      <div className={c.headerInfo}>
        <span>编制单位：{data.company_name}</span>
        <span>{data.period_label}</span>
        <span>单位：{data.unit || '元'}</span>
      </div>

      <table className={c.rawTable}>
        <thead>
          <tr>
            <th className={s.colName}>项　　目</th>
            <th className={s.colLine}>行次</th>
            <th className={s.colAmt}>本期金额</th>
            <th className={s.colAmt}>本年累计金额</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => {
            const isTotal = item.is_total
            const isGrand = item.item_name && (
              item.item_name.includes('期末现金') || item.item_name.includes('现金及现金等价物余额')
            )
            const rowCls = isGrand ? c.grandTotalRow : isTotal ? c.totalRow : ''

            return (
              <tr key={i} className={rowCls}>
                <td>{item.item_name}</td>
                <td className={c.alignCenter}>{item.line_number}</td>
                <td className={c.alignRight}>{formatAmount(item.current_amount)}</td>
                <td className={c.alignRight}>{formatAmount(item.cumulative_amount)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
