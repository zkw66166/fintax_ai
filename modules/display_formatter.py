"""展示层格式化：列名中文映射、数值格式化、分域展示"""
import json
import sqlite3
import re
from typing import Optional
from pathlib import Path

from config.settings import DB_PATH
from config.config_loader import load_json as _load_json
from modules.schema_catalog import DOMAIN_VIEWS

_CFG_display = _load_json(Path(__file__).resolve().parent.parent / "config" / "display" / "display_constants.json", {})

# ── 常量 ──────────────────────────────────────────────────────────

HIDDEN_COLUMNS = set(_CFG_display.get("hidden_columns", [
    'revision_no', 'etl_batch_id', 'etl_confidence',
    'submitted_at', 'source_doc_id', 'source_unit', 'filing_id',
]))

COMMON_COLUMN_CN = _CFG_display.get("common_column_cn", {
    'taxpayer_id': '纳税人识别号', 'taxpayer_name': '纳税人名称',
    'taxpayer_type': '纳税人类型', 'accounting_standard': '会计准则',
    'accounting_standard_name': '会计准则',
    'period_year': '年度', 'period_month': '月份', 'period_quarter': '季度',
    'period_type': '期间类型',
    'period': '期间',
    'item_type': '项目类型', 'time_range': '时间范围',
    'account_code': '科目编码', 'account_name': '科目名称',
    'level': '科目级次', 'category': '科目类别',
    'balance_direction': '余额方向', 'is_gaap': '企业会计准则', 'is_small': '小企业会计准则',
    'opening_balance': '期初余额', 'debit_amount': '借方发生额',
    'credit_amount': '贷方发生额', 'closing_balance': '期末余额',
    'invoice_format': '发票格式', 'invoice_pk': '发票主键',
    'line_no': '行号', 'invoice_code': '发票代码',
    'invoice_number': '发票号码', 'digital_invoice_no': '数电票号码',
    'seller_tax_id': '销方税号', 'seller_name': '销方名称',
    'buyer_tax_id': '购方税号', 'buyer_name': '购方名称',
    'invoice_date': '开票日期', 'invoice_source': '发票来源',
    'invoice_type': '发票类型', 'invoice_status': '发票状态',
    'is_positive': '正数发票', 'risk_level': '风险等级',
    'issuer': '开票人', 'remark': '备注',
    'amount': '金额', 'tax_amount': '税额', 'total_amount': '价税合计',
    'tax_rate': '税率', 'tax_category_code': '税收分类编码',
    'special_business_type': '特殊业务类型',
    'goods_name': '商品名称', 'specification': '规格型号',
    'unit': '单位', 'quantity': '数量', 'unit_price': '单价',
    # 财务指标
    'metric_category': '指标类别', 'metric_code': '指标编码',
    'metric_name': '指标名称', 'metric_value': '指标值',
    'metric_unit': '指标单位', 'evaluation_level': '评价等级',
    'calculated_at': '计算时间',
    # 跨域
    '_source_domain': '来源域',
    '差异': '差异', '差异率(%)': '差异率(%)',
    '比率(%)': '比率(%)', '一致': '一致', '最大差异': '最大差异',
})

PERCENTAGE_COLUMNS = set(_CFG_display.get("percentage_columns", [
    'tax_rate', 'branch_share_ratio',
]))
PERCENTAGE_SUFFIXES = tuple(_CFG_display.get("percentage_suffixes", ['_rate', '_ratio']))

DOMAIN_CN_DISPLAY = _CFG_display.get("domain_cn_display", {
    'vat': '增值税', 'eit': '企业所得税',
    'balance_sheet': '资产负债表', 'profit': '利润表',
    'cash_flow': '现金流量表', 'account_balance': '科目余额',
    'invoice': '发票', 'financial_metrics': '财务指标',
    'cross_domain': '跨域', 'profile': '企业画像',
})

# ── ColumnMapper（懒加载单例）──────────────────────────────────

class ColumnMapper:
    _instance = None
    _loaded = False
    _map = {}  # (view, column_name) → cn_name

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        try:
            from modules.db_utils import get_connection
            conn = get_connection()
            cur = conn.cursor()
            self._load_column_mappings(cur)
            self._load_item_dicts(cur)
            self._load_inv_mappings(cur)
            conn.close()
        except Exception as e:
            print(f"[ColumnMapper] 加载映射失败: {e}")

    def _load_column_mappings(self, cur):
        """加载 *_column_mapping 表"""
        tables = {
            'vat_general_column_mapping': 'vw_vat_return_general',
            'vat_small_column_mapping': 'vw_vat_return_small',
            'eit_annual_main_column_mapping': 'vw_eit_annual_main',
            'eit_quarter_main_column_mapping': 'vw_eit_quarter_main',
        }
        for table, view in tables.items():
            try:
                rows = cur.execute(
                    f"SELECT column_name, business_name FROM {table}"
                ).fetchall()
                for col, cn in rows:
                    self._map[(view, col)] = cn
            except Exception:
                pass

    def _load_item_dicts(self, cur):
        """加载资产负债表/利润表/现金流量表 item_dict"""
        # 资产负债表
        gaap_view = {'ASBE': 'vw_balance_sheet_eas', 'ASSE': 'vw_balance_sheet_sas'}
        try:
            rows = cur.execute(
                "SELECT gaap_type, item_code, item_name FROM fs_balance_sheet_item_dict"
            ).fetchall()
            for gaap, code, name in rows:
                view = gaap_view.get(gaap)
                if view:
                    col_lower = code.lower()
                    self._map[(view, f"{col_lower}_begin")] = f"{name}(年初余额)"
                    self._map[(view, f"{col_lower}_end")] = f"{name}(期末余额)"
        except Exception:
            pass

        # 利润表
        gaap_view_is = {'CAS': 'vw_profit_eas', 'SAS': 'vw_profit_sas'}
        try:
            rows = cur.execute(
                "SELECT gaap_type, item_code, item_name FROM fs_income_statement_item_dict"
            ).fetchall()
            for gaap, code, name in rows:
                view = gaap_view_is.get(gaap)
                if view:
                    self._map[(view, code.lower())] = name
        except Exception:
            pass

        # 现金流量表
        gaap_view_cf = {'CAS': 'vw_cash_flow_eas', 'SAS': 'vw_cash_flow_sas'}
        try:
            rows = cur.execute(
                "SELECT gaap_type, item_code, item_name FROM fs_cash_flow_item_dict"
            ).fetchall()
            for gaap, code, name in rows:
                view = gaap_view_cf.get(gaap)
                if view:
                    self._map[(view, code.lower())] = name
        except Exception:
            pass

    def _load_inv_mappings(self, cur):
        """加载发票字段映射"""
        table_view = {
            'inv_spec_purchase': 'vw_inv_spec_purchase',
            'inv_spec_sales': 'vw_inv_spec_sales',
        }
        try:
            rows = cur.execute(
                "SELECT source_column, target_field, table_name, description FROM inv_column_mapping"
            ).fetchall()
            for src, target, tbl, desc in rows:
                view = table_view.get(tbl)
                if view and target:
                    self._map[(view, target)] = desc or src
        except Exception:
            pass

    def translate(self, column_name: str, domain: str = '', view: str = '') -> str:
        """列名 → 中文。查找优先级：精确view → domain候选views → 通用 → 跨域前缀拆分 → 原名"""
        self._load()

        # 1. 精确 view 映射
        if view:
            cn = self._map.get((view, column_name))
            if cn:
                return cn

        # 2. domain → 候选 views
        if domain:
            for v in DOMAIN_VIEWS.get(domain, []):
                cn = self._map.get((v, column_name))
                if cn:
                    return cn

        # 3. 通用映射
        cn = COMMON_COLUMN_CN.get(column_name)
        if cn:
            return cn

        # 4. 跨域前缀拆分: "profit_net_profit" → "利润表-净利润"
        for d, views in DOMAIN_VIEWS.items():
            prefix = d + '_'
            if column_name.startswith(prefix):
                inner = column_name[len(prefix):]
                for v in views:
                    cn = self._map.get((v, inner))
                    if cn:
                        domain_cn = DOMAIN_CN_DISPLAY.get(d, d)
                        return f"{domain_cn}-{cn}"

        # 5. 兜底
        return column_name

_mapper = ColumnMapper()


# ── 数值格式化 ────────────────────────────────────────────────

def _is_percentage_col(col_name: str) -> bool:
    if col_name in PERCENTAGE_COLUMNS:
        return True
    return col_name.endswith(PERCENTAGE_SUFFIXES) or col_name.endswith('(%)')


_INTEGER_COLUMNS = {
    'period_year', 'period_month', 'period_quarter', 'level',
    'line_no', 'quantity', 'is_gaap', 'is_small', 'is_positive',
}


def format_number(value, is_percentage: bool = False, col_name: str = '') -> str:
    """格式化数值：None→'-', 整数列→原值, 百分比→'25.50%', ≥1亿→'1.50亿', ≥1万→'12.35万', 其他→千分位"""
    if value is None:
        return '-'
    if isinstance(value, str):
        return value
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    # 整数列直接显示
    if col_name in _INTEGER_COLUMNS:
        return str(int(num))

    if is_percentage:
        return f"{num:.2f}%"

    if num == 0:
        return '0.00'

    abs_num = abs(num)
    if abs_num >= 1e8:
        return f"{num / 1e8:,.2f}亿"
    if abs_num >= 1e4:
        return f"{num / 1e4:,.2f}万"
    return f"{num:,.2f}"


# ── 视图推断 ──────────────────────────────────────────────────

def _infer_domain_and_view(result: dict) -> tuple:
    """从 result['intent'] 推断 (domain, view)"""
    intent = result.get('intent') or {}
    domain = intent.get('domain', '')

    # 尝试从 {domain}_scope.views[0] 获取精确视图
    scope = intent.get(f'{domain}_scope', {})
    views = scope.get('views', [])
    view = views[0] if views else ''

    return domain, view


# ── 格式化函数 ────────────────────────────────────────────────

def _filter_columns(row: dict) -> dict:
    """过滤隐藏列"""
    return {k: v for k, v in row.items() if k not in HIDDEN_COLUMNS}


def _format_as_kv_list(rows: list, domain: str, view: str) -> str:
    """单行少列 → 列表格式"""
    lines = []
    for row in rows:
        filtered = _filter_columns(row)
        for col, val in filtered.items():
            if val is None or val == '':
                continue
            cn = _mapper.translate(col, domain, view)
            is_pct = _is_percentage_col(col)
            # _source_domain 值翻译
            if col == '_source_domain' and isinstance(val, str):
                val = DOMAIN_CN_DISPLAY.get(val, val)
            formatted = format_number(val, is_pct, col)
            lines.append(f"- **{cn}**: {formatted}")
    return '\n'.join(lines)


def _format_as_table(rows: list, domain: str, view: str) -> str:
    """多行 → Markdown 表格（中文表头 + 格式化数值 + 去除全空列）"""
    if not rows:
        return ''
    # 过滤隐藏列
    filtered_rows = [_filter_columns(row) for row in rows]
    # 收集所有行的列名（不只取第一行，因为跨域合并时不同行可能有不同列）
    all_cols_ordered = {}
    for row in filtered_rows:
        for k in row.keys():
            if k not in all_cols_ordered:
                all_cols_ordered[k] = None
    all_cols = list(all_cols_ordered.keys())

    # 检测是否为跨域多指标查询（包含多个 domain_ 前缀的列）
    domain_prefixed_cols = [c for c in all_cols if '_' in c and c.split('_')[0] in
                            ['vat', 'eit', 'profit', 'balance_sheet', 'cash_flow',
                             'account_balance', 'financial_metrics', 'invoice']]
    is_cross_domain_multi_metric = (
        domain == 'cross_domain' and
        len(domain_prefixed_cols) >= 2 and
        len(set(c.split('_')[0] for c in domain_prefixed_cols)) >= 2
    )

    # 去除所有行中值均为 None/空字符串/0 的列（保留维度列）
    _DIM_COLS = {
        'taxpayer_id', 'taxpayer_name', 'taxpayer_type', 'period_year',
        'period_month', 'period_quarter', 'period', 'time_range',
        'item_type', 'account_code', 'account_name', '_source_domain',
        'accounting_standard', 'accounting_standard_name',
    }
    cols = []
    for c in all_cols:
        if c in _DIM_COLS:
            cols.append(c)
            continue
        # 跨域多指标查询：保留所有 domain_metric 列（即使全为0/NULL）
        if is_cross_domain_multi_metric and c in domain_prefixed_cols:
            cols.append(c)
            continue
        # 其他场景：过滤全空/全零列
        has_value = any(
            row.get(c) is not None and row.get(c) != '' and row.get(c) != 0
            for row in filtered_rows
        )
        if has_value:
            cols.append(c)

    if not cols:
        cols = all_cols

    headers = [_mapper.translate(c, domain, view) for c in cols]

    lines = ['| ' + ' | '.join(headers) + ' |']
    lines.append('| ' + ' | '.join('---' for _ in cols) + ' |')
    for row in filtered_rows:
        cells = []
        for c in cols:
            val = row.get(c)
            is_pct = _is_percentage_col(c)
            if c == '_source_domain' and isinstance(val, str):
                cells.append(DOMAIN_CN_DISPLAY.get(val, val))
            else:
                cells.append(format_number(val, is_pct, c))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def _format_metric_computed(result: dict) -> str:
    """计算指标专用展示"""
    metric_results = result.get('metric_results', [])
    if not metric_results:
        return _format_as_table(result.get('results', []), 'financial_metrics', '')

    lines = []
    for m in metric_results:
        label = m.get('label', '?')
        value = m.get('value')
        unit = m.get('unit', '')
        if value is None:
            lines.append(f"**{label}**: 数据不足，无法计算")
            if m.get('error'):
                lines.append(f"  _{m['error']}_")
        else:
            if unit == '%':
                lines.append(f"**{label}**: {value:.2f}%")
            elif unit:
                lines.append(f"**{label}**: {value:.2f} {unit}")
            else:
                lines.append(f"**{label}**: {format_number(value)}")

        # 展开 sources
        sources = m.get('sources', {})
        if sources:
            parts = []
            for var, val in sources.items():
                parts.append(f"{var}={format_number(val)}")
            lines.append(f"  计算依据: {', '.join(parts)}")

    return '\n\n'.join(lines)


def _format_cross_domain(result: dict) -> str:
    """跨域结果展示：compare/ratio/reconcile 直接表格，list 按子域分组"""
    summary = result.get('cross_domain_summary', '')
    rows = result.get('results', [])
    operation = result.get('cross_domain_operation', 'list')
    parts = []
    if summary:
        parts.append(f"**{summary}**")

    if not rows:
        return '\n\n'.join(parts) if parts else '无数据'

    if operation in ('compare', 'ratio', 'reconcile'):
        # 这些操作的 merged_data 已经是紧凑结构，直接翻译表头
        # 列名可能含 domain 前缀如 "profit_operating_revenue"
        parts.append(_format_as_table(rows, 'cross_domain', ''))
    else:
        # list 操作：按 _source_domain 分组，每组独立展示
        sub_results = result.get('sub_results', [])
        domain_view_map = {}
        for sr in sub_results:
            d = sr.get('domain', '')
            # 从 sub_result 的 constraints 或 intent 推断 view
            constraints = sr.get('constraints', {})
            views = constraints.get('allowed_views', [])
            domain_view_map[d] = views[0] if views else ''

        groups = {}
        for row in rows:
            d = row.get('_source_domain', 'unknown')
            # 分组时去掉冗余的 _source_domain 列
            row_copy = {k: v for k, v in row.items() if k != '_source_domain'}
            groups.setdefault(d, []).append(row_copy)

        for d, group_rows in groups.items():
            domain_cn = DOMAIN_CN_DISPLAY.get(d, d)
            view = domain_view_map.get(d, '')
            parts.append(f"**{domain_cn}**")
            parts.append(_format_as_table(group_rows, d, view))

    return '\n\n'.join(parts)


# ── 主入口 ────────────────────────────────────────────────────

def format_display(result: dict) -> str:
    """根据结果类型分发格式化。

    Args:
        result: run_pipeline() 返回的完整 dict

    Returns:
        Markdown 格式化字符串
    """
    rows = result.get('results', [])
    if not rows:
        return '无数据'

    # 计算指标路径
    if result.get('metric_results'):
        return _format_metric_computed(result)

    # 跨域路径
    if result.get('cross_domain_summary') or result.get('sub_results'):
        return _format_cross_domain(result)

    # 标准路径
    domain, view = _infer_domain_and_view(result)

    # 单行且列数 ≤ 8 → KV 列表
    visible_cols = [k for k in rows[0] if k not in HIDDEN_COLUMNS]
    if len(rows) == 1 and len(visible_cols) <= 8:
        return _format_as_kv_list(rows, domain, view)

    return _format_as_table(rows, domain, view)


# ── 结构化展示数据（供 React 前端）─────────────────────────────

_PERIOD_COLS = {'period_year', 'period_month', 'period_quarter'}
_DIM_COLS_SET = {
    'taxpayer_id', 'taxpayer_name', 'taxpayer_type', 'period_year',
    'period_month', 'period_quarter', 'period', 'time_range',
    'item_type', 'account_code', 'account_name', '_source_domain',
    'accounting_standard', 'accounting_standard_name',
}

CHART_COLORS = [
    'rgba(54, 162, 235, 0.8)',
    'rgba(255, 99, 132, 0.8)',
    'rgba(75, 192, 192, 0.8)',
    'rgba(255, 206, 86, 0.8)',
    'rgba(153, 102, 255, 0.8)',
    'rgba(255, 159, 64, 0.8)',
]
CHART_BORDERS = [c.replace('0.8', '1') for c in CHART_COLORS]

PIE_COLORS = [
    'rgba(59, 130, 246, 0.8)',
    'rgba(139, 92, 246, 0.8)',
    'rgba(16, 185, 129, 0.8)',
    'rgba(245, 158, 11, 0.8)',
    'rgba(239, 68, 68, 0.8)',
    'rgba(6, 182, 212, 0.8)',
    'rgba(236, 72, 153, 0.8)',
    'rgba(132, 204, 22, 0.8)',
    'rgba(251, 146, 60, 0.8)',
    'rgba(168, 85, 247, 0.8)',
]


def _make_period_label(row: dict) -> str:
    """从行数据生成期间标签"""
    y = row.get('period_year', '')
    m = row.get('period_month')
    q = row.get('period_quarter')
    p = row.get('period')
    if p:
        return str(p)
    if y and m:
        return f"{y}年{int(m)}月"
    if y and q:
        return f"{y}年Q{int(q)}"
    if y:
        return f"{y}年"
    return ''


def _period_sort_key(row: dict) -> tuple:
    y = row.get('period_year', 0) or 0
    m = row.get('period_month', 0) or 0
    q = row.get('period_quarter', 0) or 0
    return (y, q, m)


def _extract_metric_cols(rows: list, preserve_zero_cols: bool = False) -> list:
    """提取数值指标列（排除维度列和隐藏列）

    Args:
        rows: 数据行列表
        preserve_zero_cols: 是否保留全零列（跨域查询时为True）
    """
    if not rows:
        return []
    first = rows[0]
    cols = []
    for k, v in first.items():
        if k in HIDDEN_COLUMNS or k in _DIM_COLS_SET:
            continue
        if isinstance(v, (int, float)) or v is None:
            # PHASE 1 FIX: 跨域查询时保留所有指标列（包括全零列）
            if preserve_zero_cols:
                cols.append(k)
            else:
                has_val = any(
                    isinstance(r.get(k), (int, float)) and r.get(k) is not None and r.get(k) != 0
                    for r in rows
                )
                if has_val:
                    cols.append(k)
    return cols


def _is_cross_domain_multi_metric(rows: list) -> bool:
    """检测是否为跨域多指标查询（多个域前缀的指标列）

    PHASE 1 FIX: 用于判断是否需要保留全零列
    """
    if not rows:
        return False
    first = rows[0]
    # 提取所有指标列的域前缀
    domain_prefixes = set()
    for k in first.keys():
        if k in HIDDEN_COLUMNS or k in _DIM_COLS_SET:
            continue
        if isinstance(first[k], (int, float)) or first[k] is None:
            # 检查是否有域前缀（如"利润表-", "增值税-", "企业所得税-"）
            if '-' in k:
                prefix = k.split('-')[0]
                domain_prefixes.add(prefix)
    # 如果有2个或以上不同的域前缀，认为是跨域查询
    return len(domain_prefixes) >= 2


def _compute_growth(rows: list, metric_cols: list, domain: str, view: str) -> list:
    """计算多期间数据的环比增长率。返回增长分析列表。

    支持两种数据结构：
    1. EAV结构（如financial_metrics）：metric_name为维度，期间为列（横向比较）
    2. 时间序列结构：每行为一个期间（纵向比较）
    """
    if len(rows) < 2 or not metric_cols:
        return []

    # 检测EAV结构：有metric_name列 + 多个期间列
    first_row = rows[0]
    has_metric_name = 'metric_name' in first_row
    period_cols = [k for k in first_row.keys()
                   if '年' in k and ('月' in k or '末' in k or '初' in k)]

    if has_metric_name and len(period_cols) >= 2:
        # EAV结构：按metric_name分组，横向比较期间列
        return _compute_growth_eav(rows, period_cols, domain, view)

    # 时间序列结构：纵向比较行（原有逻辑）
    sorted_rows = sorted(rows, key=_period_sort_key)
    growth_rows = []
    for i in range(1, len(sorted_rows)):
        prev = sorted_rows[i - 1]
        curr = sorted_rows[i]
        label = _make_period_label(curr)
        entry = {'period': label}
        for col in metric_cols:
            prev_val = prev.get(col)
            curr_val = curr.get(col)
            cn = _mapper.translate(col, domain, view)
            if isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float)) and prev_val != 0:
                change = curr_val - prev_val
                change_pct = round(change / abs(prev_val) * 100, 2)
                entry[cn] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': round(change, 2),
                    'change_pct': change_pct,
                    'trend': 'up' if change_pct > 1 else ('down' if change_pct < -1 else 'stable'),
                }
            else:
                entry[cn] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': None,
                    'change_pct': None,
                    'trend': 'unknown',
                }
        growth_rows.append(entry)
    return growth_rows


def _compute_growth_eav(rows: list, period_cols: list, domain: str, view: str) -> list:
    """计算EAV结构数据的环比增长率（按metric_name分组，横向比较期间列）。

    Args:
        rows: 数据行，每行包含 metric_name + 多个期间列
        period_cols: 期间列名列表（如 ['2024年末', '2025年末']）
        domain: 域名
        view: 视图名

    Returns:
        增长分析列表，每个元素对应一个指标的跨期变动
    """
    # 按期间列排序（假设格式为 "YYYY年MM月" 或 "YYYY年末"）
    def parse_period(col_name):
        import re
        match = re.search(r'(\d{4})年(\d{1,2})?月?', col_name)
        if match:
            year = int(match.group(1))
            month = int(match.group(2)) if match.group(2) else 12  # "年末" 视为12月
            return (year, month)
        return (0, 0)

    sorted_period_cols = sorted(period_cols, key=parse_period)

    growth_rows = []
    for row in rows:
        metric_name = row.get('metric_name', '未知指标')

        # 对每对相邻期间计算变动
        for i in range(1, len(sorted_period_cols)):
            prev_col = sorted_period_cols[i - 1]
            curr_col = sorted_period_cols[i]

            prev_val = row.get(prev_col)
            curr_val = row.get(curr_col)

            entry = {
                'period': f"{metric_name}",  # 使用指标名称作为标识
                'prev_period': prev_col,
                'curr_period': curr_col,
            }

            if isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float)) and prev_val != 0:
                change = curr_val - prev_val
                change_pct = round(change / abs(prev_val) * 100, 2)
                entry[metric_name] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': round(change, 2),
                    'change_pct': change_pct,
                    'trend': 'up' if change_pct > 1 else ('down' if change_pct < -1 else 'stable'),
                }
            else:
                entry[metric_name] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': None,
                    'change_pct': None,
                    'trend': 'unknown',
                }

            growth_rows.append(entry)

    return growth_rows

def _build_chart_data(rows: list, metric_cols: list, domain: str, view: str) -> Optional[dict]:
    """为多期间数据生成 Chart.js 兼容的图表数据。"""
    if len(rows) < 2 or not metric_cols:
        return None

    sorted_rows = sorted(rows, key=_period_sort_key)
    labels = [_make_period_label(r) for r in sorted_rows]

    datasets = []
    for idx, col in enumerate(metric_cols[:6]):  # 最多6个指标
        cn = _mapper.translate(col, domain, view)
        data = []
        for r in sorted_rows:
            v = r.get(col)
            data.append(round(v, 2) if isinstance(v, (int, float)) and v is not None else None)
        datasets.append({
            'label': cn,
            'data': data,
            'type': 'bar',
            'backgroundColor': CHART_COLORS[idx % len(CHART_COLORS)],
            'borderColor': CHART_BORDERS[idx % len(CHART_BORDERS)],
            'borderWidth': 1,
            'borderRadius': 4,
            'yAxisID': 'y',
        })

    # 如果只有1个指标且≥3期，加增长率折线
    if len(metric_cols) == 1 and len(sorted_rows) >= 3:
        col = metric_cols[0]
        cn = _mapper.translate(col, domain, view)
        growth_data = [None]
        for i in range(1, len(sorted_rows)):
            prev = sorted_rows[i - 1].get(col)
            curr = sorted_rows[i].get(col)
            if isinstance(prev, (int, float)) and isinstance(curr, (int, float)) and prev != 0:
                growth_data.append(round((curr - prev) / abs(prev) * 100, 2))
            else:
                growth_data.append(None)
        datasets.append({
            'label': f'{cn}环比增长率(%)',
            'data': growth_data,
            'type': 'line',
            'borderColor': 'rgba(255, 99, 132, 1)',
            'backgroundColor': 'rgba(255, 99, 132, 0.1)',
            'borderWidth': 2,
            'fill': False,
            'yAxisID': 'y1',
            'tension': 0.3,
            'pointRadius': 4,
        })

    chart_type = 'combo' if any(d['type'] == 'line' for d in datasets) else 'bar'
    domain_cn = DOMAIN_CN_DISPLAY.get(domain, domain)
    metric_names = [_mapper.translate(c, domain, view) for c in metric_cols[:3]]
    title = f"{domain_cn} {'、'.join(metric_names)} 趋势分析"

    chart = {
        'chartType': chart_type,
        'title': title,
        'labels': labels,
        'datasets': datasets,
    }
    if chart_type == 'combo':
        chart['options'] = {
            'scales': {
                'y': {'type': 'linear', 'position': 'left'},
                'y1': {
                    'type': 'linear', 'position': 'right',
                    'grid': {'drawOnChartArea': False},
                    'ticks': {'callback': 'PERCENT_SUFFIX'},
                },
            }
        }
    return chart


def _detect_pie_chart(rows: list, query: str = '') -> bool:
    """检测结果是否应使用饼图展示（结构/占比分析）。

    检测规则（满足任一即可）：
    1. 数据包含"占比"列 + 标签列（原有逻辑）
    2. 查询包含"构成"/"结构"/"组成"等关键词 + 数据包含"占比"列
    """
    if not rows or len(rows) < 2:
        return False
    first = rows[0]
    cols = list(first.keys())
    has_pct = any('占比' in str(c) for c in cols)
    if not has_pct:
        return False
    has_label = any(
        isinstance(first.get(c), str) and c not in _DIM_COLS_SET and c not in HIDDEN_COLUMNS
        for c in cols
    )

    # 原有逻辑：有占比列 + 标签列
    if has_label:
        return True

    # 新增逻辑：查询包含构成/结构关键词 + 有占比列
    if query:
        composition_keywords = ['构成', '结构', '组成', '明细','占比分析', '比重', '份额']
        if any(kw in query for kw in composition_keywords):
            return True

    return False


def _build_pie_chart_data(rows: list, domain: str, view: str) -> Optional[dict]:
    """为结构/占比分析结果生成 Chart.js 饼图数据。

    如果数据包含多个期间，返回多个饼图的列表；否则返回单个饼图。
    """
    if len(rows) < 2:
        return None
    first = rows[0]
    cols = list(first.keys())

    label_col = None
    for c in cols:
        if isinstance(first.get(c), str) and c not in _DIM_COLS_SET and c not in HIDDEN_COLUMNS:
            label_col = c
            break
    if not label_col:
        return None

    pct_col = None
    for c in cols:
        if '占比' in str(c):
            pct_col = c
            break
    if not pct_col:
        return None

    # 检测是否有多个期间
    has_period = any(r.get('period_year') or r.get('period_month') or r.get('period_quarter') or r.get('period') for r in rows)

    if has_period:
        # 按期间分组
        period_groups = {}
        for r in rows:
            period_label = _make_period_label(r)
            if not period_label:
                period_label = '未知期间'
            if period_label not in period_groups:
                period_groups[period_label] = []
            period_groups[period_label].append(r)

        # 如果只有一个期间，按单期间处理
        if len(period_groups) == 1:
            has_period = False
        else:
            # 生成多个饼图
            charts = []
            for period_label in sorted(period_groups.keys()):
                group_rows = period_groups[period_label]
                labels = []
                data = []
                for r in group_rows:
                    lbl = r.get(label_col, '')
                    val = r.get(pct_col)
                    if lbl and val is not None and isinstance(val, (int, float)) and val > 0:
                        labels.append(str(lbl))
                        data.append(round(val, 2))

                if len(labels) >= 2:
                    charts.append({
                        'chartType': 'pie',
                        'title': f'{period_label} {label_col} 占比分析',
                        'labels': labels,
                        'datasets': [{
                            'data': data,
                            'backgroundColor': PIE_COLORS[:len(labels)],
                            'borderColor': '#ffffff',
                            'borderWidth': 2,
                        }],
                    })

            if not charts:
                return None

            # 返回多饼图结构
            return {
                'chartType': 'multi_pie',
                'charts': charts,
            }

    # 单期间或无期间：生成单个饼图
    labels = []
    data = []
    for r in rows:
        lbl = r.get(label_col, '')
        val = r.get(pct_col)
        if lbl and val is not None and isinstance(val, (int, float)) and val > 0:
            labels.append(str(lbl))
            data.append(round(val, 2))

    if len(labels) < 2:
        return None

    return {
        'chartType': 'pie',
        'title': f'{label_col} 占比分析',
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': PIE_COLORS[:len(labels)],
            'borderColor': '#ffffff',
            'borderWidth': 2,
        }],
    }


def _format_table_rows(rows: list, domain: str, view: str) -> dict:
    """生成前端表格所需的结构化数据：headers + formatted rows"""
    if not rows:
        return {'headers': [], 'rows': [], 'columns': []}

    filtered_rows = [_filter_columns(row) for row in rows]
    # 收集所有行的列名（不只取第一行，因为跨域合并时不同行可能有不同列）
    all_cols_ordered = {}
    for row in filtered_rows:
        for k in row.keys():
            if k not in all_cols_ordered:
                all_cols_ordered[k] = None
    all_cols = list(all_cols_ordered.keys())

    # 检测是否为跨域多指标查询（包含多个 domain_ 前缀的列）
    # 场景：用户查询"利润总额、增值税应纳税额、企业所得税应纳税额"
    # 结果包含：profit_total_profit, vat_tax_payable, eit_actual_tax_payable
    # 即使某列全为0/NULL，也应保留（用户明确请求了该指标）
    domain_prefixed_cols = [c for c in all_cols if '_' in c and c.split('_')[0] in
                            ['vat', 'eit', 'profit', 'balance_sheet', 'cash_flow',
                             'account_balance', 'financial_metrics', 'invoice']]
    is_cross_domain_multi_metric = (
        domain == 'cross_domain' and
        len(domain_prefixed_cols) >= 2 and
        len(set(c.split('_')[0] for c in domain_prefixed_cols)) >= 2
    )

    # 去除全空列（但跨域多指标查询保留所有指标列）
    cols = []
    for c in all_cols:
        if c in _DIM_COLS_SET:
            cols.append(c)
            continue
        # 跨域多指标查询：保留所有 domain_metric 列（即使全为0/NULL）
        if is_cross_domain_multi_metric and c in domain_prefixed_cols:
            cols.append(c)
            continue
        # 其他场景：过滤全空/全零列
        has_value = any(
            r.get(c) is not None and r.get(c) != '' and r.get(c) != 0
            for r in filtered_rows
        )
        if has_value:
            cols.append(c)
    if not cols:
        cols = all_cols

    headers = [_mapper.translate(c, domain, view) for c in cols]
    formatted = []
    for row in filtered_rows:
        frow = {}
        for c, h in zip(cols, headers):
            val = row.get(c)
            if c == '_source_domain' and isinstance(val, str):
                frow[h] = DOMAIN_CN_DISPLAY.get(val, val)
            else:
                frow[h] = format_number(val, _is_percentage_col(c), c)
        formatted.append(frow)

    return {'headers': headers, 'rows': formatted, 'columns': cols}

def _build_empty_data_message(result: dict) -> str:
    """构建空结果的上下文提示信息。

    Args:
        result: 查询结果字典，包含 taxpayer_name, taxpayer_id, period, domain 等字段

    Returns:
        格式化的空结果提示信息
    """
    # 提取公司名称
    company_name = result.get('taxpayer_name') or result.get('taxpayer_id', '')

    # 提取期间信息
    period = result.get('period', '')

    # 提取领域信息并转换为中文
    domain = result.get('domain', '')
    domain_cn_map = {
        'vat': '增值税申报',
        'eit': '企业所得税',
        'balance_sheet': '资产负债表',
        'account_balance': '科目余额',
        'profit': '利润表',
        'cash_flow': '现金流量表',
        'invoice': '发票',
        'financial_metrics': '财务指标',
        'cross_domain': '跨域查询',
    }
    domain_cn = domain_cn_map.get(domain, '')

    # 构建消息
    if company_name and period and domain_cn:
        return f"{company_name} 在 {period} 暂无{domain_cn}数据，请导入数据或更换查询期间"
    elif company_name and domain_cn:
        return f"{company_name} 暂无{domain_cn}数据，请导入数据或更换查询期间"
    elif company_name and period:
        return f"{company_name} 在 {period} 暂无数据，请导入数据或更换查询期间"
    elif company_name:
        return f"{company_name} 暂无数据，请导入数据"
    else:
        return "当前查询条件下暂无数据，请检查查询期间或导入相关数据"

def build_display_data(result: dict, query: str = '') -> dict:
    """构建前端展示所需的完整结构化数据。

    Returns:
        {
            'table': {'headers': [...], 'rows': [...], 'columns': [...]},
            'chart_data': {...} | None,
            'growth': [...] | None,
            'summary': str | None,
            'display_type': 'kv' | 'table' | 'metric' | 'cross_domain',
            'metric_display': [...] | None,
            'sub_tables': [...] | None,  # 跨域 list 分组
            'empty_data_message': str | None,  # 空结果提示信息
        }
    """
    rows = result.get('results', [])
    if not rows:
        # 构建空结果提示信息
        empty_msg = _build_empty_data_message(result)
        return {
            'table': {'headers': [], 'rows': [], 'columns': []},
            'display_type': 'table',
            'chart_data': None,
            'growth': None,
            'empty_data_message': empty_msg
        }

    # 计算指标路径
    if result.get('metric_results'):
        metrics = result['metric_results']
        display = []
        for m in metrics:
            entry = {
                'label': m.get('label', '?'),
                'value': m.get('value'),
                'unit': m.get('unit', ''),
                'formatted_value': _fmt_metric_value(m),
                'sources': {},
                'error': m.get('error'),
            }
            for var, val in m.get('sources', {}).items():
                entry['sources'][var] = format_number(val)
            display.append(entry)
        return {
            'display_type': 'metric',
            'metric_display': display,
            'table': {'headers': [], 'rows': [], 'columns': []},
            'chart_data': None,
            'growth': None,
        }

    # 概念管线路径：虽然有 cross_domain_summary，但数据已合并为单一表格，走标准表格路径
    if result.get('concept_pipeline') and not result.get('sub_results'):
        domain, view = _infer_domain_and_view(result)
        table = _format_table_rows(rows, domain, view)
        metric_cols = _extract_metric_cols(rows)
        chart_data = _build_chart_data(rows, metric_cols, domain, view)
        growth = _compute_growth(rows, metric_cols, domain, view)
        return {
            'display_type': 'table',
            'table': table,
            'chart_data': chart_data,
            'growth': growth if growth else None,
            'summary': result.get('cross_domain_summary'),
        }

    # 跨域路径
    if result.get('cross_domain_summary') or result.get('sub_results'):
        return _build_cross_domain_display(result)

    # 标准路径
    domain, view = _infer_domain_and_view(result)
    visible_cols = [k for k in rows[0] if k not in HIDDEN_COLUMNS]

    # PHASE 1 FIX: 检测是否为跨域多指标查询
    is_cross_domain_multi_metric = _is_cross_domain_multi_metric(rows)

    # 单行少列 → KV
    if len(rows) == 1 and len(visible_cols) <= 8:
        table = _format_table_rows(rows, domain, view)
        return {
            'display_type': 'kv',
            'table': table,
            'chart_data': None,
            'growth': None,
        }

    # 多行 → 表格 + 图表 + 增长
    table = _format_table_rows(rows, domain, view)
    # PHASE 1 FIX: 跨域查询时保留全零列
    metric_cols = _extract_metric_cols(rows, preserve_zero_cols=is_cross_domain_multi_metric)

    # 饼图检测：结构/占比分析结果
    if _detect_pie_chart(rows, query):
        pie_data = _build_pie_chart_data(rows, domain, view)
        if pie_data:
            return {
                'display_type': 'table',
                'table': table,
                'chart_data': pie_data,
                'growth': None,
            }

    chart_data = _build_chart_data(rows, metric_cols, domain, view)
    growth = _compute_growth(rows, metric_cols, domain, view)

    return {
        'display_type': 'table',
        'table': table,
        'chart_data': chart_data,
        'growth': growth if growth else None,
    }


def _fmt_metric_value(m: dict) -> str:
    value = m.get('value')
    unit = m.get('unit', '')
    if value is None:
        return '数据不足'
    if unit == '%':
        return f"{value:.2f}%"
    if unit:
        return f"{value:.2f} {unit}"
    return format_number(value)


def _build_cross_domain_display(result: dict) -> dict:
    """跨域结果的结构化展示数据"""
    rows = result.get('results', [])
    operation = result.get('cross_domain_operation', 'list')
    summary = result.get('cross_domain_summary', '')

    # PHASE 1 FIX: 检测是否为跨域多指标查询（在分组前检测）
    is_cross_domain_multi_metric = _is_cross_domain_multi_metric(rows)

    if operation in ('compare', 'ratio', 'reconcile'):
        table = _format_table_rows(rows, 'cross_domain', '')
        # PHASE 1 FIX: 跨域查询时保留全零列
        metric_cols = _extract_metric_cols(rows, preserve_zero_cols=is_cross_domain_multi_metric)
        chart_data = _build_chart_data(rows, metric_cols, 'cross_domain', '')
        growth = _compute_growth(rows, metric_cols, 'cross_domain', '')
        return {
            'display_type': 'cross_domain',
            'table': table,
            'chart_data': chart_data,
            'growth': growth if growth else None,
            'summary': summary,
        }

    # list: 按子域分组
    sub_results = result.get('sub_results', [])
    domain_view_map = {}
    for sr in sub_results:
        d = sr.get('domain', '')
        constraints = sr.get('constraints', {})
        views = constraints.get('allowed_views', [])
        domain_view_map[d] = views[0] if views else ''

    groups = {}
    for row in rows:
        d = row.get('_source_domain', 'unknown')
        row_copy = {k: v for k, v in row.items() if k != '_source_domain'}
        groups.setdefault(d, []).append(row_copy)

    sub_tables = []
    for d, group_rows in groups.items():
        domain_cn = DOMAIN_CN_DISPLAY.get(d, d)
        view = domain_view_map.get(d, '')
        table = _format_table_rows(group_rows, d, view)
        # PHASE 1 FIX: list操作也保留全零列（传递跨域标志）
        metric_cols = _extract_metric_cols(group_rows, preserve_zero_cols=is_cross_domain_multi_metric)
        chart_data = _build_chart_data(group_rows, metric_cols, d, view)
        growth = _compute_growth(group_rows, metric_cols, d, view)
        sub_tables.append({
            'domain': d,
            'domain_cn': domain_cn,
            'table': table,
            'chart_data': chart_data,
            'growth': growth if growth else None,
        })

    return {
        'display_type': 'cross_domain',
        'table': {'headers': [], 'rows': [], 'columns': []},
        'sub_tables': sub_tables,
        'summary': summary,
        'chart_data': None,
        'growth': None,
    }

