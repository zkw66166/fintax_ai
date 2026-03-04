import BalanceSheetRaw from './raw/BalanceSheetRaw'
import IncomeStatementRaw from './raw/IncomeStatementRaw'
import CashFlowRaw from './raw/CashFlowRaw'
import VatReturnRaw from './raw/VatReturnRaw'
import EitReturnRaw from './raw/EitReturnRaw'

const RAW_COMPONENTS = {
  balance_sheet: BalanceSheetRaw,
  income_statement: IncomeStatementRaw,
  cash_flow: CashFlowRaw,
  vat_general: VatReturnRaw,
  vat_small: VatReturnRaw,
  eit_annual: EitReturnRaw,
  eit_quarter: EitReturnRaw,
}

export default function RawFormatView({ data }) {
  if (!data) return <div style={{ color: '#999', padding: '40px 0', textAlign: 'center', fontSize: 13 }}>暂无数据</div>

  const Component = RAW_COMPONENTS[data.format_type]
  if (!Component) {
    return (
      <div style={{ color: '#999', padding: '40px 0', textAlign: 'center', fontSize: 13 }}>
        该数据表不支持原表格式
      </div>
    )
  }

  return <Component data={data} />
}
