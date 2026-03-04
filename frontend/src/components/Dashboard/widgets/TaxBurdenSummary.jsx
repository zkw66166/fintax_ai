import { Receipt } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import MetricDisplay from '../shared/MetricDisplay'
import { useProfileData } from '../hooks/useDashboardData'
import s from './TaxBurdenSummary.module.css'

export default function TaxBurdenSummary({ companyId }) {
  const { data, loading, error, refetch } = useProfileData(companyId)

  if (!companyId) {
    return (
      <WidgetCard title="税负汇总" icon={Receipt} size="medium">
        <div className={s.empty}>请选择公司</div>
      </WidgetCard>
    )
  }

  const taxData = data?.tax_summary || {}

  // Format large numbers with Chinese units
  const formatAmount = (amount) => {
    if (!amount && amount !== 0) return '-'
    const num = parseFloat(amount)
    if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
    if (num >= 10000) return (num / 10000).toFixed(2) + '万'
    return num.toFixed(2)
  }

  const metrics = [
    {
      label: '增值税',
      value: formatAmount(taxData.vat_total),
      unit: '元'
    },
    {
      label: '企业所得税',
      value: formatAmount(taxData.eit_total),
      unit: '元'
    },
    {
      label: '总税负',
      value: formatAmount(taxData.tax_total),
      unit: '元'
    },
    {
      label: '税负率',
      value: taxData.tax_burden_rate || '-',
      unit: '%',
      level: taxData.tax_burden_level
    }
  ]

  return (
    <WidgetCard
      title="税负汇总"
      icon={Receipt}
      size="medium"
      loading={loading}
      error={error}
      onRefresh={refetch}
    >
      <div className={s.grid}>
        {metrics.map((metric, i) => (
          <MetricDisplay
            key={i}
            label={metric.label}
            value={metric.value}
            unit={metric.unit}
            level={metric.level}
          />
        ))}
      </div>
    </WidgetCard>
  )
}
