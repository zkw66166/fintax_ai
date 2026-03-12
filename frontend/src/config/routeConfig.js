// 路由配置（4种路由类型）
// cls 字段用于 ChatMessage 组件的样式兼容性
export const ROUTE_CONFIG = {
  financial_data: {
    label: '📊 财税数据查询',
    shortLabel: '财税数据',
    color: '#3b82f6',
    description: '财税数据查询',
    cls: 'routeFinancial'
  },
  tax_incentive: {
    label: '📋 本地知识库查询结果',
    shortLabel: '税收优惠',
    color: '#10b981',
    description: '本地知识库查询',
    cls: 'routeTax'
  },
  regulation: {
    label: '🤖 法规知识库',
    shortLabel: '法规知识',
    color: '#f59e0b',
    description: '法规知识库查询',
    cls: 'routeRegulation'
  },
  mixed_analysis: {
    label: '🔄 综合分析',
    shortLabel: '综合分析',
    color: '#8b5cf6',
    description: '跨路由混合分析',
    cls: 'routeMixed'
  }
}

// 域配置（9种域类型，仅适用于 financial_data 路由）
export const DOMAIN_CONFIG = {
  vat: { label: '增值税', color: '#ef4444', shortLabel: 'VAT' },
  eit: { label: '企业所得税', color: '#f97316', shortLabel: 'EIT' },
  balance_sheet: { label: '资产负债表', color: '#06b6d4', shortLabel: '资负表' },
  profit: { label: '利润表', color: '#14b8a6', shortLabel: '利润表' },
  cash_flow: { label: '现金流量表', color: '#10b981', shortLabel: '现金流' },
  account_balance: { label: '科目余额', color: '#6366f1', shortLabel: '科目' },
  invoice: { label: '发票', color: '#8b5cf6', shortLabel: '发票' },
  financial_metrics: { label: '财务指标', color: '#ec4899', shortLabel: '指标' },
  cross_domain: { label: '跨域查询', color: '#f59e0b', shortLabel: '跨域' }
}

// 分类树结构（用于导航，预留给未来功能）
export const CATEGORY_TREE = [
  {
    id: 'tax_incentive',
    label: '税收优惠',
    icon: '📋',
    route: 'tax_incentive'
  },
  {
    id: 'regulation',
    label: '法规知识',
    icon: '🤖',
    route: 'regulation'
  },
  {
    id: 'financial_data',
    label: '财务数据',
    icon: '📊',
    route: 'financial_data',
    children: [
      { id: 'account_balance', label: '科目余额', domain: 'account_balance' },
      { id: 'financial_statements', label: '财务报表', domains: ['balance_sheet', 'profit', 'cash_flow'] },
      { id: 'tax_returns', label: '纳税申报', domains: ['vat', 'eit'] },
      { id: 'financial_metrics', label: '财务指标', domain: 'financial_metrics' },
      { id: 'invoice', label: '发票', domain: 'invoice' },
      { id: 'comprehensive', label: '综合分析', domains: ['cross_domain', 'mixed_analysis'] }
    ]
  }
]

// 工具函数
export function getRouteBadge(route) {
  return ROUTE_CONFIG[route] || { label: '未知', icon: '❓', color: '#6b7280' }
}

export function getDomainBadge(domain) {
  return DOMAIN_CONFIG[domain] || null
}

export function extractDomain(historyItem) {
  // 优先从顶层 domain 字段读取（后端派生）
  if (historyItem.domain) {
    return historyItem.domain
  }

  // 向后兼容：从 result.entities.domain_hint 提取
  return historyItem?.result?.entities?.domain_hint || null
}
