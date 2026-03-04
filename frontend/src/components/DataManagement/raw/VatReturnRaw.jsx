import c from './rawCommon.module.css'
import s from './VatReturnRaw.module.css'
import { formatAmount } from './rawUtils'

export default function VatReturnRaw({ data }) {
  if (!data || !data.rows) return <div className={c.empty}>暂无数据</div>

  const isGeneral = data.format_type === 'vat_general'
  const rows = data.rows || []

  const title = isGeneral
    ? '增值税及附加税费申报表（一般纳税人适用）'
    : '增值税及附加税费申报表（小规模纳税人适用）'

  const col1Label = isGeneral ? '一般项目' : '货物及劳务'
  const col2Label = isGeneral ? '即征即退项目' : '服务、不动产和无形资产'
  const tr1Label = isGeneral ? '本月数' : '本期数'
  const tr2Label = '本年累计'

  const k1 = isGeneral ? 'general_current' : 'goods_current'
  const k2 = isGeneral ? 'general_cumulative' : 'goods_cumulative'
  const k3 = isGeneral ? 'immediate_current' : 'services_current'
  const k4 = isGeneral ? 'immediate_cumulative' : 'services_cumulative'

  return (
    <div className={`${c.rawContainer} ${s.vatContainer}`}>
      <div className={c.reportTitle}>{title}</div>
      <div className={c.headerInfoStacked}>
        <div className={s.metaRow}>
          税款所属时间：{data.period_label}　　填表日期：　　单位：{data.unit || '元'}
        </div>
        <div className={s.metaRow}>
          纳税人识别号：{data.taxpayer_id}
        </div>
        <div className={s.metaRow}>
          纳税人名称：{data.company_name}
        </div>
      </div>

      <table className={c.rawTable}>
        <thead>
          <tr>
            <th rowSpan={2} className={s.colSection}></th>
            <th rowSpan={2} className={s.colName}>项　　目</th>
            <th rowSpan={2} className={s.colLine}>栏次</th>
            <th colSpan={2}>{col1Label}</th>
            <th colSpan={2}>{col2Label}</th>
          </tr>
          <tr>
            <th className={s.colAmt}>{tr1Label}</th>
            <th className={s.colAmt}>{tr2Label}</th>
            <th className={s.colAmt}>{tr1Label}</th>
            <th className={s.colAmt}>{tr2Label}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const hasSection = row.section && row.section_span > 0

            return (
              <tr key={i}>
                {hasSection && (
                  <td rowSpan={row.section_span} className={c.sectionCell}>
                    {row.section}
                  </td>
                )}
                <td>{row.item_name}</td>
                <td className={c.alignCenter}>{row.line_number}</td>
                <td className={c.alignRight}>{formatAmount(row[k1])}</td>
                <td className={c.alignRight}>{formatAmount(row[k2])}</td>
                <td className={c.alignRight}>{formatAmount(row[k3])}</td>
                <td className={c.alignRight}>{formatAmount(row[k4])}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
