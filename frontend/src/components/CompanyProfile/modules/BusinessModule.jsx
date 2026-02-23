import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import { fmtAmount } from '../utils'
import s from '../CompanyProfile.module.css'

export default function BusinessModule({ data }) {
  const profit = data?.profit_data
  const inv = data?.invoice_summary

  return (
    <div className={s.subGrid3}>
      <div className={s.subCard}>
        <SectionTitle name="业务结构" color="green" />
        <CompactMetric label="主营业务收入" value={fmtAmount(profit?.revenue)} />
        <CompactMetric label="发票数量(销售)" value={inv?.sales_count != null ? `${inv.sales_count}张` : '—'} />
        <CompactMetric label="发票数量(采购)" value={inv?.purchase_count != null ? `${inv.purchase_count}张` : '—'} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="供应商集中度" color="purple" />
        <div style={{ padding: '16px 0', textAlign: 'center', color: '#999', fontSize: 13 }}>暂无供应商数据</div>
      </div>
      <div className={s.subCard}>
        <SectionTitle name="客户集中度" color="orange" />
        <div style={{ padding: '16px 0', textAlign: 'center', color: '#999', fontSize: 13 }}>暂无客户数据</div>
      </div>
    </div>
  )
}
