import c from './rawCommon.module.css'
import s from './EitReturnRaw.module.css'
import { formatAmount, formatRate } from './rawUtils'

export default function EitReturnRaw({ data }) {
  if (!data || !data.rows) return <div className={c.empty}>暂无数据</div>

  const isAnnual = data.format_type === 'eit_annual'
  const rows = data.rows || []

  if (isAnnual) return <AnnualView data={data} rows={rows} />
  return <QuarterlyView data={data} rows={rows} />
}

function AnnualView({ data, rows }) {
  return (
    <div className={`${c.rawContainer} ${s.eitContainer}`}>
      <div className={c.reportTitle}>A100000</div>
      <div className={c.reportSubtitle}>中华人民共和国企业所得税年度纳税申报表（A类）</div>
      <div className={c.headerInfoStacked}>
        <div>纳税人名称：{data.company_name}　　纳税人识别号：{data.taxpayer_id}</div>
        <div>所属年度：{data.period_label}　　单位：{data.unit || '元'}</div>
      </div>

      <table className={c.rawTable}>
        <thead>
          <tr>
            <th className={s.colLine}>行次</th>
            <th className={s.colCategory}>类　别</th>
            <th className={s.colName}>项　　目</th>
            <th className={s.colAmt}>金　额</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const hasSection = row.section && row.section_span > 0
            const isRate = row.item_name && row.item_name.includes('税率')
            const val = isRate ? formatRate(row.amount) : formatAmount(row.amount)

            return (
              <tr key={i}>
                <td className={c.alignCenter}>{row.line_number}</td>
                {hasSection && (
                  <td rowSpan={row.section_span} className={c.sectionCell}>
                    {row.section}
                  </td>
                )}
                <td>{row.item_name}</td>
                <td className={c.alignRight}>{val}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function QuarterlyView({ data, rows }) {
  const extra = data.extra_info || {}

  return (
    <div className={`${c.rawContainer} ${s.eitContainer}`}>
      <div className={c.reportTitle}>A200000</div>
      <div className={c.reportSubtitle}>中华人民共和国企业所得税月（季）度预缴纳税申报表（A类）</div>
      <div className={c.headerInfoStacked}>
        <div>纳税人名称：{data.company_name}　　纳税人识别号：{data.taxpayer_id}</div>
        <div>所属期间：{data.period_label}　　单位：{data.unit || '元'}</div>
        {(extra.employee_quarter_avg != null || extra.asset_quarter_avg != null) && (
          <div className={s.extraInfo}>
            {extra.employee_quarter_avg != null && <span>从业人数季度平均值：{extra.employee_quarter_avg}人</span>}
            {extra.asset_quarter_avg != null && <span>　资产总额季度平均值：{formatAmount(extra.asset_quarter_avg)}万元</span>}
            {extra.small_micro_enterprise != null && (
              <span>　是否小型微利企业：{extra.small_micro_enterprise ? '是' : '否'}</span>
            )}
          </div>
        )}
      </div>

      <table className={c.rawTable}>
        <thead>
          <tr>
            <th className={s.colLine}>行次</th>
            <th className={s.colNameWide}>项　　目</th>
            <th className={s.colAmt}>本年累计金额</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const hasSection = row.section && row.section_span > 0
            const isRate = row.item_name && row.item_name.includes('税率')
            const val = isRate ? formatRate(row.amount) : formatAmount(row.amount)

            return hasSection ? (
              <>
                <tr key={`sec-${i}`} className={s.sectionRow}>
                  <td colSpan={3} className={c.sectionCell}>{row.section}</td>
                </tr>
                <tr key={i}>
                  <td className={c.alignCenter}>{row.line_number}</td>
                  <td>{row.item_name}</td>
                  <td className={c.alignRight}>{val}</td>
                </tr>
              </>
            ) : (
              <tr key={i}>
                <td className={c.alignCenter}>{row.line_number}</td>
                <td>{row.item_name}</td>
                <td className={c.alignRight}>{val}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
