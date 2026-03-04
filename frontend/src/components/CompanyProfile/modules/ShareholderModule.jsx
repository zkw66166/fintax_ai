import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import { fmtAmount } from '../utils'
import s from '../CompanyProfile.module.css'
import shareholderStyles from './ShareholderModule.module.css'

export default function ShareholderModule({ data }) {
  const sh = data?.shareholders
  if (!sh) return <div style={{ padding: '16px 0', textAlign: 'center', color: '#999', fontSize: 13 }}>暂无股权数据</div>

  const holders = sh.shareholders || []
  const companyName = data?.basic_info?.taxpayer_name || '本公司'

  return (
    <div className={s.subGrid2}>
      <div className={s.subCard}>
        <SectionTitle name="股权架构" />
        <div className={shareholderStyles.structureContainer}>
          {/* Shareholders at top */}
          <div className={shareholderStyles.shareholdersRow}>
            {holders.map((holder, idx) => (
              <div key={idx} className={shareholderStyles.shareholderNode}>
                <div className={shareholderStyles.shareholderBox}>
                  <div className={shareholderStyles.shareholderName}>{holder.name}</div>
                  <div className={shareholderStyles.shareholderRatio}>{holder.ratio}%</div>
                </div>
                <div className={shareholderStyles.verticalLine} />
              </div>
            ))}
          </div>

          {/* Horizontal connector line */}
          {holders.length > 0 && (
            <div className={shareholderStyles.horizontalLine} />
          )}

          {/* Company at bottom */}
          <div className={shareholderStyles.companyRow}>
            <div className={shareholderStyles.companyNode}>
              <div className={shareholderStyles.companyBox}>
                {companyName}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={s.subCard}>
        <SectionTitle name="股权信息" />
        <CompactMetric label="股东总数" value={`${sh.total_count}人`} />
        <CompactMetric label="最大股东" value={sh.top_shareholder}
          evalData={sh.is_controlling ? { level: '控股', type: 'positive' } : null} />
        <CompactMetric label="最大股东持股" value={sh.top_ratio != null ? `${sh.top_ratio}%` : '—'}
          evalData={sh.is_controlling ? { level: '控股', type: 'positive' } : null} />
        <CompactMetric label="分红总额" value={fmtAmount(sh.total_dividend)} />
        <CompactMetric label="对外投资数" value="0家" />

        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e5e7eb' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#475569', marginBottom: 8 }}>公司治理</div>
          <CompactMetric label="财务审计意见" value="标准无保留意见"
            evalData={{ level: '良好', type: 'positive' }} />
          <CompactMetric label="内控缺陷数" value="0个"
            evalData={{ level: '规范', type: 'positive' }} />
        </div>
      </div>
    </div>
  )
}
