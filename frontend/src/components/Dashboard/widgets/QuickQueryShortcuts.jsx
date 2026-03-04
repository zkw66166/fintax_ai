import { Zap, TrendingUp, DollarSign, Activity, FileText, Gift } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import s from './QuickQueryShortcuts.module.css'

export default function QuickQueryShortcuts({ companyId, companyName, onQueryClick }) {
  if (!companyId || !companyName) {
    return (
      <WidgetCard title="快捷查询" icon={Zap} size="large">
        <div className={s.empty}>请选择公司</div>
      </WidgetCard>
    )
  }

  const shortcuts = [
    {
      icon: DollarSign,
      label: '本月增值税',
      desc: '查询本月增值税申报情况',
      query: `${companyName}本月增值税是多少?`
    },
    {
      icon: TrendingUp,
      label: '本年净利润',
      desc: '查询本年累计净利润',
      query: `${companyName}本年净利润是多少?`
    },
    {
      icon: Activity,
      label: '资产负债率',
      desc: '查询最新资产负债率',
      query: `${companyName}资产负债率是多少?`
    },
    {
      icon: FileText,
      label: '现金流',
      desc: '查询经营活动现金流',
      query: `${companyName}本年经营活动现金流是多少?`
    },
    {
      icon: FileText,
      label: '发票统计',
      desc: '查询本月发票情况',
      query: `${companyName}本月开了多少发票?`
    },
    {
      icon: Gift,
      label: '税收优惠',
      desc: '查询适用的税收优惠政策',
      query: `${companyName}有哪些税收优惠政策?`
    }
  ]

  const handleShortcutClick = (query) => {
    if (onQueryClick) {
      onQueryClick(query)
    }
  }

  return (
    <WidgetCard title="快捷查询" icon={Zap} size="large">
      <div className={s.grid}>
        {shortcuts.map((shortcut, i) => {
          const Icon = shortcut.icon
          return (
            <div
              key={i}
              className={s.shortcut}
              onClick={() => handleShortcutClick(shortcut.query)}
            >
              <Icon size={20} className={s.shortcutIcon} />
              <div className={s.shortcutLabel}>{shortcut.label}</div>
              <div className={s.shortcutDesc}>{shortcut.desc}</div>
            </div>
          )
        })}
      </div>
    </WidgetCard>
  )
}
