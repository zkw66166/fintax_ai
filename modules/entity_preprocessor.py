"""实体预处理：提取纳税人/期次 + 同义词标准化（最长匹配优先）+ 域检测 + 相对日期解析"""
import re
import sqlite3
from datetime import date, timedelta

# 模块级缓存：纳税人列表（启动时加载一次）
_taxpayer_cache = None

# 科目余额域关键词（最高优先级 — 仅科目余额表独有）
_ACCOUNT_BALANCE_KEYWORDS_HIGH = [
    '科目余额', '借方发生额', '贷方发生额', '期初余额', '期末余额',
    '借方发生', '贷方发生', '科目余额表',
    # 补充：总账、明细账、科目汇总表等专有词汇
    '总账', '明细账', '科目汇总表', '三栏式明细账', '多栏式明细账', '数量金额式明细账',
    '科目余额查询', '科目发生额', '科目期初', '科目期末', '累计发生额', '本期发生额',
]
# 科目余额域关键词（中优先级 — 需结合上下文）
_ACCOUNT_BALANCE_KEYWORDS_MED = [
    '发生额', '借方', '贷方', '会计科目', '科目编码', '余额方向',
    '账上', '账面', '账载',
    # 补充：常用账务术语
    '借或贷', '余额方向', '期初借方余额', '期初贷方余额', '期末借方余额', '期末贷方余额',
    '本期借方发生额', '本期贷方发生额', '本年累计借方', '本年累计贷方',
    '银行存款日记账', '现金日记账',
]
# 科目余额表特有科目名称（具体会计科目，不是资产负债表行项目）
# 此处仅保留资产负债表主表中不直接列示的明细科目（如存货明细、备抵科目、过渡科目等）
_ACCOUNT_SPECIFIC_NAMES = [
    # 货币资金明细
    '银行存款', '库存现金', '其他货币资金',
    # 收入成本明细
    '主营业务收入', '主营业务成本', '其他业务收入', '其他业务成本',
    # 所有者权益类过渡科目
    '本年利润', '利润分配',
    # 明确指向科目级余额
    '现金余额',
    # 备抵科目（不在主表单独列示）
    '坏账准备', '累计折旧', '累计摊销', '存货跌价准备', '固定资产减值准备', '无形资产减值准备',
    # 成本差异科目
    '材料成本差异', '商品进销差价',
    # 过渡/清理科目
    '固定资产清理', '待处理财产损溢',
    # 存货明细（主表仅列示“存货”总额）
    '原材料', '材料采购', '在途物资', '库存商品', '发出商品', '委托加工物资',
    '周转材料', '包装物', '低值易耗品', '生产成本', '制造费用',
    # 其他明细（不直接对应主表项目）
    '现金等价物', '备用金', '存出保证金', '存出投资款', '买入返售金融资产',
    '应收出口退税', '应收补贴款', '内部往来', '拨付所属资金',
    '长期应付款——专项应付款', '专项应付款', '递延收益——未实现售后租回损益',
    # 补充更多常用明细（但需确保不在资产负债表主表直接列示）
    '以前年度损益调整', '公允价值变动损益', '汇兑损益', '手续费支出',
    '利息支出', '利息收入', '其他业务支出',
]

# 资产负债表域关键词（高优先级 — 直接命中）
_BALANCE_SHEET_KEYWORDS_HIGH = [
    '资产负债表', '资产负债',
]
# 资产负债表域关键词（中优先级 — 需结合上下文判断）
_BALANCE_SHEET_KEYWORDS_MED = [
    '资产总计', '负债合计', '所有者权益合计', '股东权益合计',
    '负债和所有者权益', '流动资产合计', '非流动资产合计',
    '流动负债合计', '非流动负债合计', '负债及权益总计',
    '总资产', '总负债',
]
# 资产负债表特有项目（不与科目余额表/EIT重叠的项目）
# 此处仅保留主表独有的汇总项或新准则下不常见于科目余额表的项目，
# 其余具体项目移入 _BS_SHARED_ITEMS 中，通过上下文消歧。
_BALANCE_SHEET_ITEMS_UNIQUE = [
    # 合计项
    '流动资产合计', '非流动资产合计', '资产总计',
    '流动负债合计', '非流动负债合计', '负债合计',
    '所有者权益合计', '股东权益合计', '负债和所有者权益总计', '负债及权益总计',
    # 新准则下可能单独列示的项目（科目余额表可能不单独设账）
    '应收款项融资', '合同资产', '持有待售资产', '一年内到期的非流动资产',
    '债权投资', '其他债权投资', '长期应收款', '其他权益工具投资',
    '其他非流动金融资产', '投资性房地产', '使用权资产', '商誉', '递延所得税资产',
    '交易性金融负债', '衍生金融负债', '合同负债', '持有待售负债',
    '一年内到期的非流动负债', '应付债券', '租赁负债', '预计负债',
    '递延所得税负债', '库存股', '其他综合收益', '专项储备',
    # 合并报表特有
    '少数股东权益', '归属于母公司所有者权益合计',
    '其中：利息收入', '汇兑收益', '手续费及佣金支出',
]
# 资产负债表与科目余额表共有项目 — 需要"年初"/"期末"等修饰词区分
_BS_SHARED_ITEMS = [
    '货币资金', '应收票据', '应收账款', '预付账款', '其他应收款',
    '存货', '固定资产', '无形资产', '在建工程', '长期待摊费用',
    '长期股权投资', '生产性生物资产', '开发支出',
    '短期借款', '应付票据', '应付账款', '预收款项', '预收账款',
    '应付职工薪酬', '应交税费', '其他应付款', '长期借款',
    '长期应付款', '递延收益', '实收资本', '资本公积', '盈余公积',
    '未分配利润',
    # 以下是从原 _BALANCE_SHEET_ITEMS_UNIQUE 移过来的共享项目
    '应收股利', '应收利息', '应付利息', '应付利润',
    '工程物资', '固定资产账面价值', '短期投资', '长期债券投资',
    '固定资产原价', '累计折旧', '固定资产净值', '固定资产净额',
    '在建工程减值准备', '无形资产减值准备', '商誉减值准备',
    '长期股权投资减值准备', '投资性房地产减值准备',
    '信用减值损失', '资产减值损失',  # 这些虽然是利润表项目，但资产负债表也有相关披露
    '递延税款', '其他流动资产', '其他非流动资产',
    '其他流动负债', '其他非流动负债', '专项应付款',
    '永续债', '其他权益工具',
]
# "年初"指向资产负债表，"期初"指向科目余额表
_BS_TIME_MARKERS = ['年初', '年初余额', '年末', '年末余额']
_AB_TIME_MARKERS = ['期初', '期初余额', '期末余额']  # 注意"期末"单独出现时默认BS

# EIT 域关键词（用于域提示检测）
_EIT_KEYWORDS = [
    '企业所得税', '应纳税所得额', '纳税调整',
    '纳税调增', '纳税调减', '弥补亏损', '减免所得税', '实际利润额',
    '预缴所得税', '应补退所得税', '实际应纳所得税', '所得税年报', '所得税季报',
    '年度申报', '季度预缴', 'EIT', '税前利润', '会计利润',
    # 补充企业所得税申报表特有名词
    '营业收入', '营业成本', '利润总额', '纳税调整增加额', '纳税调整减少额',
    '免税收入', '减计收入', '加计扣除', '所得减免', '抵扣应纳税所得额',
    '抵免所得税额', '境外所得应纳所得税额', '实际应纳所得税额', '本年累计实际已预缴的所得税额',
    '本年应补退所得税额', '以前年度多缴在本年抵缴', '以前年度应缴未缴在本年入库',
    '减免所得税额', '小型微利企业减免所得税额', '高新技术企业减免所得税额',
    '研发费用加计扣除', '固定资产加速折旧', '一次性扣除', '不征税收入',
    '创业投资抵扣', '弥补以前年度亏损',
    '企业所得税年度纳税申报表', '企业所得税月（季）度预缴纳税申报表', 'A类', 'B类',
    '查账征收', '核定征收', '应税所得率', '收入总额', '成本费用总额',
    '核定应纳税所得额', '所得税汇算清缴', '汇算清缴', '季度预缴', '年度汇算',
    '退税', '补税', '滞纳金', '跨地区经营', '汇总纳税', '分支机构分摊',
]
_EIT_KEYWORD_SUODESHUI = '所得税'
_EIT_SUODESHUI_EXCLUSIONS = ['所得税费用']

# EIT/VAT共享关键词：需上下文消歧（"增值税应纳税额"→VAT，"应纳税额"单独出现→EIT）
_EIT_CONTEXT_KEYWORDS = ['应纳税额', '适用税率']
_EIT_CONTEXT_EXCLUSIONS = ['增值税应纳税额', '增值税适用税率']


def _has_eit_keyword(query: str) -> bool:
    """检查查询中是否包含EIT域关键词。

    对共享关键词（'所得税'、'应纳税额'、'适用税率'）做上下文排除：
    - '所得税' 排除 '所得税费用'
    - '应纳税额'/'适用税率' 排除 '增值税应纳税额'/'增值税适用税率'
    """
    for kw in _EIT_KEYWORDS:
        if kw in query:
            return True
    # 单独检查"所得税"：排除"所得税费用"
    if _EIT_KEYWORD_SUODESHUI in query:
        if _check_context_keyword(query, _EIT_KEYWORD_SUODESHUI, _EIT_SUODESHUI_EXCLUSIONS):
            return True
    # 单独检查"应纳税额"/"适用税率"：排除"增值税应纳税额"/"增值税适用税率"
    for kw in _EIT_CONTEXT_KEYWORDS:
        if kw in query:
            if _check_context_keyword(query, kw, _EIT_CONTEXT_EXCLUSIONS):
                return True
    return False


def _check_context_keyword(query: str, keyword: str, exclusions: list) -> bool:
    """检查关键词在查询中是否有未被排除词覆盖的出现。"""
    idx = 0
    while True:
        pos = query.find(keyword, idx)
        if pos == -1:
            break
        excluded = False
        for excl in exclusions:
            excl_pos = query.find(excl)
            if excl_pos != -1 and excl_pos <= pos < excl_pos + len(excl):
                excluded = True
                break
        if not excluded:
            return True
        idx = pos + 1
    return False

# VAT 域关键词
_VAT_KEYWORDS = [
    '增值税', '销项税', '进项税', '留抵', '征收率', '简易计税',
    '免抵退', '即征即退', 'VAT',
    # 补充增值税申报表特有名词
    '销售额', '应纳税额', '本期应补退税额', '本期已缴税额', '期初未缴税额', '期末未缴税额',
    '进项税额', '销项税额', '进项税额转出', '免抵退应退税额', '简易计税方法应纳税额',
    '一般计税方法应纳税额', '应税销售额', '免税销售额', '出口销售额', '适用税率',
    '本期实际抵扣税额', '上期留抵税额', '本期留抵税额', '期末留抵税额',
    '按适用税率计税销售额', '按简易办法计税销售额', '免抵退销售额', '出口免抵退销售额',
    '进项税额抵扣', '进项转出', '进项税票', '增值税专用发票', '增值税普通发票',
    '发票抵扣', '勾选确认', '申报抵扣', '进项税额结构明细', '增值税减免税明细',
    '加计抵减', '加计扣除', '留抵退税', '增量留抵', '存量留抵',
    '增值税纳税申报表', '增值税及附加税费申报表', '附列资料', '附表一', '附表二', '附表三', '附表四',
    '减免税明细表', '税控设备', '税控盘', '税务UKey',
    '小微企业免税销售额', '未达起征点销售额', '其他免税销售额', '本期应纳税额', '本期应纳税额减征额',
    '进项税额结构明细表', '本期进项税额明细', '增值税减免税申报明细表',
    '加计抵减政策', '留抵退税政策', '即征即退政策', '先征后退', '出口退税',
]

# 发票域关键词（在VAT之前检测，含"发票"字样优先走invoice域）
_INVOICE_KEYWORDS = [
    '进项发票', '销项发票', '采购发票', '销售发票',
    '专用发票', '普通发票', '数电票', '红冲发票', '红字发票', '蓝字发票',
    '开票人', '发票号码', '发票代码', '价税合计', '发票金额', '票面金额',
    '采购金额', '采购额',
    '发票',  # 最短的放最后，避免误匹配
    # 补充发票域特有名词
    '增值税专用发票', '增值税普通发票', '电子发票', '纸质发票', '全电发票',
    '机动车销售统一发票', '二手车销售统一发票', '通行费发票', '农产品收购发票',
    '海关进口增值税专用缴款书', '完税凭证',
    '已开具', '未开具', '作废', '红冲', '冲红', '有效', '异常', '失控', '滞留', '缺联',
    '红字发票信息表', '蓝字发票',
    '发票代码', '发票号码', '开票日期', '购买方名称', '销售方名称', '货物或应税劳务名称',
    '规格型号', '单位', '数量', '单价', '金额', '税率', '税额', '价税合计', '备注',
    '收款人', '复核人', '开票人', '校验码',
    '发票查验', '发票勾选', '发票认证', '发票抵扣', '发票确认', '发票上传', '发票下载',
    '发票查询', '发票开具', '发票作废', '发票红冲', '发票冲红', '发票冲销', '发票更正',
    '发票补开', '发票领用', '发票库存', '发票限额', '发票限量', '发票增量', '发票降版', '发票升版',
    '进项发票明细', '销项发票明细', '发票汇总表', '发票统计',
]

# 利润表域关键词（高优先级 — 直接命中）
_PROFIT_KEYWORDS_HIGH = [
    '利润表', '损益表',
]
# 利润表特有项目（不与EIT/科目余额表重叠的项目）
_PROFIT_ITEMS_UNIQUE = [
    '综合收益总额', '每股收益', '基本每股收益', '稀释每股收益',
    '持续经营净利润', '终止经营净利润',
    '其他综合收益的税后净额', '不能重分类进损益',
    '重新计量设定受益计划', '权益法下不能转损益',
    '其他权益工具投资公允价值变动', '企业自身信用风险公允价值变动',
    '将重分类进损益', '权益法下可转损益',
    '其他债权投资公允价值变动', '金融资产重分类',
    '其他债权投资信用减值', '现金流量套期', '外币财务报表折算差额',
    '利息费用', '利息收入',
    # 补充利润表特有项目
    '扣除非经常性损益后的净利润', '归属于母公司所有者的净利润', '少数股东损益',
    '营业总收入', '营业总成本', '其中：利息收入', '汇兑收益', '手续费及佣金收入',
    '资产处置收益', '其他收益', '信用减值损失', '资产减值损失',
    '公允价值变动收益', '投资收益',
]
# 利润表与EIT共有项目（需要上下文消歧）
_PROFIT_EIT_SHARED_ITEMS = [
    '营业收入', '营业成本', '税金及附加', '销售费用', '管理费用',
    '研发费用', '财务费用', '其他收益', '投资收益',
    '公允价值变动收益', '信用减值损失', '资产减值损失', '资产处置收益',
    '营业利润', '营业外收入', '营业外支出', '利润总额',
    '所得税费用', '净利润',
]
# 利润表时间标记
_PROFIT_TIME_MARKERS = ['本期金额', '本年累计金额', '本年累计']
# 利润表默认指向项目：无修饰词+有月份时，这些项目默认指向利润表
_PROFIT_DEFAULT_ITEMS = [
    '营业收入', '营业成本', '营业利润', '利润总额', '净利润',
    '所得税费用', '税金及附加',
    # 注意：'销售金额'/'销售额' 已移至概念注册表处理，不再默认指向利润表
]

# 现金流量表域关键词（高优先级 — 直接命中）
_CASH_FLOW_KEYWORDS_HIGH = [
    '现金流量表', '现金流量',
]
# 现金流量表特有项目（不与其他域重叠）
_CASH_FLOW_ITEMS_UNIQUE = [
    '经营活动现金流量净额', '投资活动现金流量净额', '筹资活动现金流量净额',
    '经营活动现金流入', '经营活动现金流出', '投资活动现金流入', '投资活动现金流出',
    '筹资活动现金流入', '筹资活动现金流出',
    '经营活动净现金', '投资活动净现金', '筹资活动净现金',
    '经营现金净额', '投资现金净额', '筹资现金净额',
    # 常见简称（用户常省略"活动"/"量"等字）
    '经营现金流净额', '投资现金流净额', '筹资现金流净额',
    '经营现金流入', '经营现金流出', '投资现金流入', '投资现金流出',
    '筹资现金流入', '筹资现金流出',
    '经营现金流', '投资现金流', '筹资现金流', '现金流净额',
    '现金净增加额', '现金及现金等价物净增加额',
    '期初现金及现金等价物', '期末现金及现金等价物',
    '销售商品收到的现金', '提供劳务收到的现金', '购买商品支付的现金',
    '支付给职工的现金', '支付的各项税费', '收到的税费返还',
    '收回投资收到的现金', '取得投资收益收到的现金',
    '处置固定资产收回的现金', '购建固定资产支付的现金',
    '投资支付的现金', '吸收投资收到的现金', '取得借款收到的现金',
    '偿还债务支付的现金', '分配股利支付的现金',
    '汇率变动对现金的影响', '汇率变动影响',
    '经营活动产生的现金', '投资活动产生的现金', '筹资活动产生的现金',
    # 补充现金流量表特有项目
    '收到的其他与经营活动有关的现金', '支付的其他与经营活动有关的现金',
    '收到的其他与投资活动有关的现金', '支付的其他与投资活动有关的现金',
    '收到的其他与筹资活动有关的现金', '支付的其他与筹资活动有关的现金',
    '现金及现金等价物净增加额', '期末现金及现金等价物余额', '期初现金及现金等价物余额',
    '直接法', '间接法', '现金流量表补充资料',
    '现金流', '现金流入', '现金流出', '净现金流', '经营活动现金流', '投资活动现金流', '筹资活动现金流',
]

# 财务指标域关键词（高优先级 — 直接命中）
_FINANCIAL_METRICS_KEYWORDS_HIGH = [
    '财务指标', '财务比率', '财税指标', '指标分析', '指标计算',
]
# 财务指标域特有项目（不与其他域重叠的指标名称）
_FINANCIAL_METRICS_ITEMS_UNIQUE = [
    '毛利率', '净利率', '销售净利率', '净资产收益率', 'ROE',
    '资产负债率', '负债率', '流动比率', '速动比率',
    '应收账款周转率', '存货周转率', '总资产周转率',
    '营业收入增长率', '收入增长率', '销售收现比',
    '增值税税负率', '增值税税负', '企业所得税税负率', '所得税税负率',
    '综合税负率', '综合税负', '销项进项配比率', '进项税额转出占比',
    '应税所得率', '零申报率', '现金债务保障比率',
    '净利润增长率', '利润增长率',
    '管理费用率', '管理费用占比',
    '销售费用率', '销售费用占比',
    '应收款周转天数', '应收账款周转天数', '回款天数',
    '资产增长率', '总资产增长率',
    '发票开具异常率', '发票异常率', '顶额开具率',
    # 补充更多财务指标
    '权益乘数', '产权比率', '长期资本负债率', '利息保障倍数', '现金流量利息保障倍数',
    '现金流比率', '现金流动负债比率', '总资产净利率', '总资产报酬率', 'ROA',
    '投入资本回报率', 'ROIC', '营业收入毛利率', '营业利润率', '成本费用利润率',
    '净资产增长率', '可持续增长率', '营业利润增长率', '每股收益', '每股净资产',
    '市盈率', '市净率', '所得税贡献率', '增值税贡献率', '印花税税负率', '城建税税负率',
    '发票作废率', '红冲率', '发票连号率', '发票开具金额', '发票份数',
    '流动负债率', '流动资产率', '固定资产比率', '资产负债结构', '资产结构', '资本结构',
]


def _resolve_relative_dates(query: str, today: date = None) -> str:
    """将相对日期表达式替换为绝对日期字符串，再走现有解析逻辑。

    支持的表达式：
      今年/本年 → 当前年份
      去年/上年 → 当前年份-1
      前年 → 当前年份-2
      本月/这个月 → 当前年+月
      上个月/上月 → 当前月-1
      上个季度 → 上一季度展开为月份范围
      今年上半年 → 当前年1月到6月
      今年下半年 → 当前年7月到12月
      今年前N个月 → 当前年1月到N月
      最近N个月/近N个月 → 从当前月往前推N个月
      最近N个季度末 → 最近N个季度末月份列表
      过去N个纳税年度 → 当前年-N到当前年-1
      近N年/最近N年 → 当前年-N+1到当前年
      去年底/年底 → 去年12月 / 当前年12月
      去年全年 → 去年1月到12月
      今年全年 → 今年1月到12月
    """
    if today is None:
        today = date.today()
    cur_year = today.year
    cur_month = today.month
    cur_quarter = (cur_month - 1) // 3 + 1

    # --- 中文数字→阿拉伯数字辅助 ---
    _CN_NUM = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
               '十一': 11, '十二': 12}

    def _cn_to_int(s):
        """中文数字转int，支持'三'→3, '十二'→12, '3'→3"""
        s = s.strip()
        if s in _CN_NUM:
            return _CN_NUM[s]
        if s.isdigit():
            return int(s)
        # "十N" → 10+N
        if s.startswith('十') and len(s) == 2 and s[1] in _CN_NUM:
            return 10 + _CN_NUM[s[1]]
        return int(s) if s.isdigit() else None

    # 数字模式（匹配阿拉伯数字或中文数字）
    _NUM_PAT = r'(\d{1,2}|[一二两三四五六七八九十]+)'

    # --- 复合表达式（先处理长模式，避免被短模式截断） ---

    # "今年上半年" → "YYYY年1月到6月"
    query = re.sub(r'今年上半年|本年上半年', f'{cur_year}年1月到6月', query)
    # "今年下半年" → "YYYY年7月到12月"
    query = re.sub(r'今年下半年|本年下半年', f'{cur_year}年7月到12月', query)
    # "去年上半年" → "(YYYY-1)年1月到6月"
    query = re.sub(r'去年上半年|上年上半年', f'{cur_year - 1}年1月到6月', query)
    # "去年下半年" → "(YYYY-1)年7月到12月"
    query = re.sub(r'去年下半年|上年下半年', f'{cur_year - 1}年7月到12月', query)

    # "今年前N个月" → "YYYY年1月到N月"
    def _replace_first_n_months(m):
        n = _cn_to_int(m.group(1))
        if n is None:
            return m.group(0)
        n = min(n, 12)
        return f'{cur_year}年1月到{n}月'
    query = re.sub(r'(?:今年|本年)前' + _NUM_PAT + r'个月', _replace_first_n_months, query)

    # "最近N个月" / "近N个月" → 展开为 "YYYY年M月到YYYY年M月"
    def _replace_recent_n_months(m):
        n = _cn_to_int(m.group(1))
        if n is None:
            return m.group(0)
        end_y, end_m = cur_year, cur_month
        total_months = cur_year * 12 + cur_month - (n - 1)
        start_y = (total_months - 1) // 12
        start_m = (total_months - 1) % 12 + 1
        if start_y == end_y:
            return f'{start_y}年{start_m}月到{end_m}月'
        return f'{start_y}年{start_m}月到{end_y}年{end_m}月'
    query = re.sub(r'(?:最近|近)' + _NUM_PAT + r'个月', _replace_recent_n_months, query)

    # "最近N个季度末" → 展开为枚举月份
    def _replace_recent_n_quarter_ends(m):
        n = _cn_to_int(m.group(1))
        if n is None:
            return m.group(0)
        quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
        results = []
        q, y = cur_quarter, cur_year
        if cur_month != quarter_end_months[q]:
            q -= 1
            if q == 0:
                q = 4
                y -= 1
        for _ in range(n):
            results.append(f'{y}年{quarter_end_months[q]}月')
            q -= 1
            if q == 0:
                q = 4
                y -= 1
        results.reverse()
        return '、'.join(results)
    query = re.sub(r'(?:最近|近)' + _NUM_PAT + r'个季度末', _replace_recent_n_quarter_ends, query)

    # "过去N个纳税年度" → "YYYY年到YYYY年"
    def _replace_past_n_tax_years(m):
        n = _cn_to_int(m.group(1))
        if n is None:
            return m.group(0)
        start_y = cur_year - n
        end_y = cur_year - 1
        if n == 1:
            return f'{end_y}年度'
        return f'{start_y}年到{end_y}年'
    query = re.sub(r'过去' + _NUM_PAT + r'个纳税年度', _replace_past_n_tax_years, query)

    # "近N年" / "最近N年" → "YYYY年到YYYY年"
    def _replace_recent_n_years(m):
        n = _cn_to_int(m.group(1))
        if n is None:
            return m.group(0)
        start_y = cur_year - n + 1
        return f'{start_y}年到{cur_year}年'
    query = re.sub(r'(?:最近|近)' + _NUM_PAT + r'年', _replace_recent_n_years, query)

    # "去年和今年" / "今年和去年" → compound year comparison (before 全年 patterns)
    query = re.sub(r'去年\s*[和与]\s*今年', f'{cur_year - 1}年和{cur_year}年', query)
    query = re.sub(r'今年\s*[和与]\s*去年', f'{cur_year}年和{cur_year - 1}年', query)

    # "去年全年" → "(YYYY-1)年全年"  (保留"全年"让后续逻辑处理)
    query = re.sub(r'去年全年', f'{cur_year - 1}年全年', query)
    # "今年全年" / "本年全年"
    query = re.sub(r'(?:今年|本年)全年', f'{cur_year}年全年', query)

    # "去年底" / "去年年底" → "(YYYY-1)年12月"
    query = re.sub(r'去年(?:年)?底', f'{cur_year - 1}年12月', query)
    # "年底" (无修饰) → "当前年12月" — 仅当前面没有数字年份时
    query = re.sub(r'(?<!\d)年底', f'{cur_year}年12月', query)

    # "上个季度" → 展开为月份范围
    def _replace_last_quarter(m):
        q = cur_quarter - 1
        y = cur_year
        if q == 0:
            q = 4
            y -= 1
        start_m = (q - 1) * 3 + 1
        end_m = q * 3
        return f'{y}年{start_m}月到{end_m}月'
    query = re.sub(r'上个?季度', _replace_last_quarter, query)

    # "上个月" / "上月" → "(YYYY)年(M-1)月"
    def _replace_last_month(m):
        y, mo = cur_year, cur_month - 1
        if mo == 0:
            mo = 12
            y -= 1
        return f'{y}年{mo}月'
    query = re.sub(r'上个?月', _replace_last_month, query)

    # "本月" / "这个月" → "YYYY年M月"  (注意：VAT的"本月"是time_range维度值，不替换)
    # 仅当"本月"不是作为VAT time_range使用时才替换
    # 策略：如果查询中有VAT关键词，不替换"本月"
    has_vat_context = any(kw in query for kw in ['增值税', '销项税', '进项税', '留抵', 'VAT', '征收率', '简易计税'])
    if not has_vat_context:
        query = re.sub(r'(?:本月|这个月)', f'{cur_year}年{cur_month}月', query)

    # --- 2位年份范围 → 4位年份 ---

    # "23-25年" / "23至25年" / "23到25年" → "2023年到2025年"
    def _replace_short_year_range(m):
        y1, y2 = int(m.group(1)), int(m.group(2))
        if y1 < 100:
            y1 += 2000
        if y2 < 100:
            y2 += 2000
        return f'{y1}年到{y2}年'

    query = re.sub(r'(?<!\d)(\d{2})\s*[-到至]\s*(\d{2})\s*年', _replace_short_year_range, query)
    query = re.sub(r'(?<!\d)(\d{2})\s*年\s*[-到至]\s*(\d{2})\s*年', _replace_short_year_range, query)

    # --- 简单年份替换（放在最后，避免干扰复合表达式） ---

    # "今年Q1" / "今年第一季度" 等 — 先处理"今年"+"季度"组合
    query = re.sub(r'今年\s*(?=Q|第?\s*[一二三四1-4]\s*季度)', f'{cur_year}年', query)
    query = re.sub(r'去年\s*(?=Q|第?\s*[一二三四1-4]\s*季度)', f'{cur_year - 1}年', query)

    # "今年N-M月" / "今年N月到M月" → "YYYY年N月到M月"
    query = re.sub(r'(?:今年|本年)(\d{1,2})\s*[-到至]\s*(\d{1,2})\s*月',
                   lambda m: f'{cur_year}年{m.group(1)}月到{m.group(2)}月', query)
    query = re.sub(r'(?:去年|上年)(\d{1,2})\s*[-到至]\s*(\d{1,2})\s*月',
                   lambda m: f'{cur_year - 1}年{m.group(1)}月到{m.group(2)}月', query)

    # "今年N月" → "YYYY年N月"
    query = re.sub(r'(?:今年|本年)(\d{1,2})月', lambda m: f'{cur_year}年{m.group(1)}月', query)
    query = re.sub(r'去年(\d{1,2})月', lambda m: f'{cur_year - 1}年{m.group(1)}月', query)

    # 独立的 "今年" / "本年" → "YYYY年" (仅当后面不紧跟数字/月/季度/特殊词)
    query = re.sub(r'(?:今年|本年)(?!\d|年|月|季|上|下|前|全|和|与)', f'{cur_year}年', query)
    query = re.sub(r'(?:去年|上年)(?!\d|年|月|季|上|下|全|底|和|与)', f'{cur_year - 1}年', query)
    query = re.sub(r'前年(?!\d|年|月|季|和|与)', f'{cur_year - 2}年', query)

    return query


def _load_taxpayer_cache(db_conn: sqlite3.Connection):
    """加载纳税人列表到缓存"""
    global _taxpayer_cache
    if _taxpayer_cache is None:
        cur = db_conn.cursor()
        _taxpayer_cache = cur.execute(
            "SELECT taxpayer_id, taxpayer_name, taxpayer_type FROM taxpayer_info"
        ).fetchall()
    return _taxpayer_cache


def detect_entities(user_query: str, db_conn: sqlite3.Connection) -> dict:
    """从用户问题中提取实体信息（含域检测）"""
    # 引号标准化：去除中文引号，避免干扰关键词匹配
    user_query = re.sub(r'[""''「」『』【】]', '', user_query)

    # P0: 相对日期→绝对日期预处理
    resolved_query = _resolve_relative_dates(user_query)

    result = {
        'taxpayer_id': None, 'taxpayer_name': None, 'taxpayer_type': None,
        'period_year': None, 'period_month': None,
        'period_end_month': None,  # 范围查询用
        'period_quarter': None,    # EIT季度用
        'period_years': None,      # 多年对比用
        'period_months': None,     # 枚举月份用
        'time_range_hint': None, 'item_type_hint': None,
        'domain_hint': None,       # 域提示: 'vat' / 'eit' / 'balance_sheet' / 'account_balance' / None
        'time_granularity': None,  # 时间粒度: 'quarterly' / 'monthly' / 'yearly' / None
        'original_query': user_query,  # 保留原始查询
        'resolved_query': resolved_query,  # 日期解析后的查询
    }

    # 0. 域提示检测（先判断域，再做其他处理）
    # 0a-1. 财务指标高优先级关键词（最先检测 — 指标名称非常独特）
    for kw in _FINANCIAL_METRICS_KEYWORDS_HIGH:
        if kw in user_query:
            result['domain_hint'] = 'financial_metrics'
            break

    # 0a-1b. 财务指标特有项目（直接命中）
    if result['domain_hint'] is None:
        for kw in _FINANCIAL_METRICS_ITEMS_UNIQUE:
            if kw in user_query:
                result['domain_hint'] = 'financial_metrics'
                break

    # 0a0. 现金流量表高优先级关键词（最先检测，直接命中 — 与其他域无重叠）
    for kw in _CASH_FLOW_KEYWORDS_HIGH:
        if kw in user_query:
            result['domain_hint'] = 'cash_flow'
            break

    # 0a0b. 现金流量表特有项目（直接命中）
    if result['domain_hint'] is None:
        for kw in _CASH_FLOW_ITEMS_UNIQUE:
            if kw in user_query:
                result['domain_hint'] = 'cash_flow'
                break

    # 0a. 科目余额高优先级关键词（最先检测，直接命中）
    for kw in _ACCOUNT_BALANCE_KEYWORDS_HIGH:
        if kw in user_query:
            result['domain_hint'] = 'account_balance'
            break

    # 0a1. 科目余额表特有科目名称（如"银行存款"、"库存现金"等明细科目）
    if result['domain_hint'] is None:
        for kw in _ACCOUNT_SPECIFIC_NAMES:
            if kw in user_query:
                result['domain_hint'] = 'account_balance'
                break

    # 0a2. 利润表高优先级关键词（直接命中）
    if result['domain_hint'] is None:
        for kw in _PROFIT_KEYWORDS_HIGH:
            if kw in user_query:
                result['domain_hint'] = 'profit'
                break

    # 0a3. 利润表特有项目（直接命中）
    if result['domain_hint'] is None:
        for kw in _PROFIT_ITEMS_UNIQUE:
            if kw in user_query:
                result['domain_hint'] = 'profit'
                break

    # 0b. 资产负债表高优先级关键词
    if result['domain_hint'] is None:
        for kw in _BALANCE_SHEET_KEYWORDS_HIGH:
            if kw in user_query:
                result['domain_hint'] = 'balance_sheet'
                break

    # 0c. 资产负债表中优先级关键词（合计项等）
    if result['domain_hint'] is None:
        for kw in _BALANCE_SHEET_KEYWORDS_MED:
            if kw in user_query:
                result['domain_hint'] = 'balance_sheet'
                break

    # 0d. 资产负债表特有项目（直接命中）
    if result['domain_hint'] is None:
        for kw in _BALANCE_SHEET_ITEMS_UNIQUE:
            if kw in user_query:
                result['domain_hint'] = 'balance_sheet'
                break

    # 0e. 共有项目消歧：资产负债表 vs 科目余额表
    if result['domain_hint'] is None:
        has_shared_item = any(item in user_query for item in _BS_SHARED_ITEMS)
        if has_shared_item:
            # 含"借"、"贷"或"发生额" → 科目余额表
            has_ab_signal = any(kw in user_query for kw in ['借方', '贷方', '发生额', '借', '贷', '账上', '账面', '账载'])
            # 含"年初" → 资产负债表
            has_bs_time = any(kw in user_query for kw in _BS_TIME_MARKERS)
            # 含"期初" → 科目余额表
            has_ab_time = any(kw in user_query for kw in _AB_TIME_MARKERS)

            if has_ab_signal:
                result['domain_hint'] = 'account_balance'
            elif has_bs_time:
                result['domain_hint'] = 'balance_sheet'
            elif has_ab_time:
                result['domain_hint'] = 'account_balance'
            else:
                # 无修饰词时，"XX余额"默认资产负债表（期末）
                # 但如果有VAT/EIT关键词则不判断
                has_vat = any(v in user_query for v in _VAT_KEYWORDS)
                has_eit = _has_eit_keyword(user_query)
                if not has_vat and not has_eit:
                    result['domain_hint'] = 'balance_sheet'

    # 0f. 科目余额中优先级关键词（需排除VAT/EIT上下文）
    if result['domain_hint'] is None:
        for kw in _ACCOUNT_BALANCE_KEYWORDS_MED:
            if kw in user_query:
                has_vat = any(v in user_query for v in _VAT_KEYWORDS)
                has_eit = _has_eit_keyword(user_query)
                if not has_vat and not has_eit:
                    result['domain_hint'] = 'account_balance'
                    break

    # 0f2. 利润表与EIT/科目余额表共有项目消歧
    if result['domain_hint'] is None:
        has_profit_item = any(item in user_query for item in _PROFIT_EIT_SHARED_ITEMS)
        if has_profit_item:
            # 含"借"、"贷"或"发生额" → 科目余额表（最高优先级）
            has_ab_signal = any(kw in user_query for kw in ['借方', '贷方', '发生额', '借', '贷', '账上', '账面', '账载'])
            # 含"期初" → 科目余额表
            has_ab_time = any(kw in user_query for kw in _AB_TIME_MARKERS)
            # 含利润表时间标记 → 利润表
            has_profit_time = any(kw in user_query for kw in _PROFIT_TIME_MARKERS)
            # 含EIT专有关键词 → EIT（排除"所得税费用"误触发）
            has_eit_exclusive = _has_eit_keyword(user_query)

            if has_ab_signal or has_ab_time:
                result['domain_hint'] = 'account_balance'
            elif has_eit_exclusive:
                result['domain_hint'] = 'eit'
            elif has_profit_time:
                result['domain_hint'] = 'profit'
            else:
                # 无修饰词时：有"年度"→EIT，有月份→利润表，否则利润表
                has_annual = bool(re.search(r'\d{4}\s*年度', user_query))
                has_quarter = bool(re.search(r'第?\s*[一二三四1-4]\s*季度', user_query))
                if has_annual or has_quarter:
                    result['domain_hint'] = 'eit'
                else:
                    # 默认指向利润表（利润表是财务报表，EIT是税务申报）
                    result['domain_hint'] = 'profit'

    # 0g. EIT关键词
    if result['domain_hint'] is None:
        if _has_eit_keyword(user_query):
            result['domain_hint'] = 'eit'

    # 0g2. 发票域关键词（在VAT之前检测：含"发票"字样优先走invoice域）
    if result['domain_hint'] is None:
        for kw in _INVOICE_KEYWORDS:
            if kw in user_query:
                result['domain_hint'] = 'invoice'
                # 方向检测
                if '进项发票' in user_query or '采购发票' in user_query:
                    result['invoice_direction'] = 'purchase'
                elif '销项发票' in user_query or '销售发票' in user_query:
                    result['invoice_direction'] = 'sales'
                else:
                    result['invoice_direction'] = 'both'
                break

    # 0h. VAT关键词
    if result['domain_hint'] is None:
        for kw in _VAT_KEYWORDS:
            if kw in user_query:
                result['domain_hint'] = 'vat'
                break

    # 0i. 跨域检测：如果已检测到一个域，但查询中还包含其他域的独有关键词，升级为cross_domain
    # 注意：共有项目（如"营业收入"同属利润表和EIT）不触发跨域，只有域独有关键词才触发
    if result['domain_hint'] and result['domain_hint'] != 'cross_domain':
        detected = result['domain_hint']
        other_domains = set()

        # 检查是否同时包含VAT独有关键词（增值税、销项税等不与其他域共享）
        if detected != 'vat' and any(kw in user_query for kw in _VAT_KEYWORDS):
            other_domains.add('vat')
        # 检查是否同时包含发票域关键词
        if detected != 'invoice' and any(kw in user_query for kw in _INVOICE_KEYWORDS):
            other_domains.add('invoice')
        # 检查是否同时包含利润表独有关键词/项目（排除与EIT共有的项目）
        if detected != 'profit':
            has_profit_unique = (
                any(kw in user_query for kw in _PROFIT_KEYWORDS_HIGH) or
                any(kw in user_query for kw in _PROFIT_ITEMS_UNIQUE)
            )
            # 当已检测到非EIT域时，共有项目（如"营业收入"）也应触发profit跨域
            if not has_profit_unique and detected not in ('eit',):
                has_profit_shared = any(kw in user_query for kw in _PROFIT_DEFAULT_ITEMS)
                if has_profit_shared:
                    has_profit_unique = True
            if has_profit_unique:
                other_domains.add('profit')
        # 检查是否同时包含资产负债表关键词（含共有项目如"存货"）
        # 注意：account_balance 和 balance_sheet 共享大量项目，已在0e步骤消歧，
        # 不应因共有项目触发跨域升级
        if detected not in ('balance_sheet', 'account_balance'):
            has_bs = (
                any(kw in user_query for kw in _BALANCE_SHEET_KEYWORDS_HIGH) or
                any(kw in user_query for kw in _BALANCE_SHEET_KEYWORDS_MED) or
                any(kw in user_query for kw in _BALANCE_SHEET_ITEMS_UNIQUE) or
                any(kw in user_query for kw in _BS_SHARED_ITEMS)
            )
            if has_bs:
                other_domains.add('balance_sheet')
        # 检查是否同时包含EIT独有关键词
        if detected != 'eit' and _has_eit_keyword(user_query):
            other_domains.add('eit')
        # 检查是否同时包含科目余额表独有关键词
        # 注意：balance_sheet 和 account_balance 已在0e步骤消歧
        if detected not in ('account_balance', 'balance_sheet'):
            has_ab = (
                any(kw in user_query for kw in _ACCOUNT_BALANCE_KEYWORDS_HIGH) or
                any(kw in user_query for kw in ['账上', '账面', '账载'])
            )
            if has_ab:
                other_domains.add('account_balance')
        # 检查是否同时包含现金流量表独有关键词
        if detected != 'cash_flow':
            has_cf = (
                any(kw in user_query for kw in _CASH_FLOW_KEYWORDS_HIGH) or
                any(kw in user_query for kw in _CASH_FLOW_ITEMS_UNIQUE)
            )
            if has_cf:
                other_domains.add('cash_flow')
        # 检查是否同时包含财务指标独有关键词
        if detected != 'financial_metrics':
            has_fm = (
                any(kw in user_query for kw in _FINANCIAL_METRICS_KEYWORDS_HIGH) or
                any(kw in user_query for kw in _FINANCIAL_METRICS_ITEMS_UNIQUE)
            )
            if has_fm:
                other_domains.add('financial_metrics')

        if other_domains:
            all_domains = sorted({detected} | other_domains)
            result['domain_hint'] = 'cross_domain'
            result['cross_domain_list'] = all_domains

    # 1. 提取纳税人（支持全名和简称模糊匹配）
    names = _load_taxpayer_cache(db_conn)

    # 先尝试精确匹配（全名在query中）
    for tid, tname, ttype in names:
        if tname in user_query:
            result['taxpayer_id'] = tid
            result['taxpayer_name'] = tname
            result['taxpayer_type'] = ttype
            break
        if tid in user_query:
            result['taxpayer_id'] = tid
            result['taxpayer_name'] = tname
            result['taxpayer_type'] = ttype
            break
    # 再尝试模糊匹配
    if not result['taxpayer_id']:
        best_match = None
        best_len = 0
        for tid, tname, ttype in names:
            for length in range(len(tname), 1, -1):
                prefix = tname[:length]
                if prefix in user_query and length > best_len:
                    best_match = (tid, tname, ttype)
                    best_len = length
        if best_match and best_len >= 2:
            result['taxpayer_id'] = best_match[0]
            result['taxpayer_name'] = best_match[1]
            result['taxpayer_type'] = best_match[2]

    # 2. 提取季度（优先于月份检测）— 使用resolved_query
    # G4修复：仅当无其他域信号时才默认EIT；已有域检测结果时保留该域并展开季度为月份
    q_map = {'一': 1, '二': 2, '三': 3, '四': 4, '1': 1, '2': 2, '3': 3, '4': 4}
    m_quarter = re.search(r'(\d{4})\s*年\s*第?\s*([一二三四1-4])\s*季度', resolved_query)
    if m_quarter:
        result['period_year'] = int(m_quarter.group(1))
        result['period_quarter'] = q_map.get(m_quarter.group(2))
        if result['domain_hint'] is None:
            result['domain_hint'] = 'eit'  # 仅无域信号时默认EIT
        elif result['domain_hint'] != 'eit':
            # 非EIT域：季度→月份范围展开
            q = result['period_quarter']
            result['period_month'] = (q - 1) * 3 + 1
            result['period_end_month'] = q * 3
    # "Q1 2025" / "2025Q1" 格式
    if not result['period_quarter']:
        m_q2 = re.search(r'(\d{4})\s*[Qq]\s*([1-4])', resolved_query)
        if m_q2:
            result['period_year'] = int(m_q2.group(1))
            result['period_quarter'] = int(m_q2.group(2))
            if result['domain_hint'] is None:
                result['domain_hint'] = 'eit'
            elif result['domain_hint'] != 'eit':
                q = result['period_quarter']
                result['period_month'] = (q - 1) * 3 + 1
                result['period_end_month'] = q * 3

    # 2b. "各季度"/"每个季度"/"每季度"/"所有季度"/"每季" → 全部4个季度
    if not result['period_quarter']:
        has_all_quarters = bool(re.search(r'各季度|每个?季度|所有季度|全部季度', resolved_query))
        if has_all_quarters:
            result['all_quarters'] = True
            # 对于EIT域，不设置具体季度，让SQL生成 period_quarter IN (1,2,3,4)
            # 对于其他域，展开为全年月份范围
            if result['domain_hint'] == 'eit' or result['domain_hint'] is None:
                pass  # 保持period_quarter为None，通过all_quarters标志告知LLM
            else:
                # 非EIT域：展开为1-12月
                if not result['period_month']:
                    result['period_month'] = 1
                    result['period_end_month'] = 12

    # 2c. 时间粒度检测（供概念管线使用）
    if re.search(r'各季度?|每个?季度?|按季度?|分季度?|逐季度?|季度对比|季度趋势|季度变化', resolved_query):
        result['time_granularity'] = 'quarterly'
    elif re.search(r'各月|每个?月|按月|分月|逐月|月度对比|月度趋势|月度变化', resolved_query):
        result['time_granularity'] = 'monthly'
    elif re.search(r'各年|每年|按年|分年|逐年|年度对比|年度趋势|年度变化', resolved_query):
        result['time_granularity'] = 'yearly'

    # 3. 提取年度（"2024年度" 格式，EIT年度申报）
    m_annual = re.search(r'(\d{4})\s*年度', resolved_query)
    if m_annual and not result['period_year']:
        result['period_year'] = int(m_annual.group(1))
        if result['domain_hint'] is None:
            result['domain_hint'] = 'eit'  # "年度"查询默认EIT

    # 4. 提取期次（月份）— 使用resolved_query
    if not result['period_year']:
        m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月', resolved_query)
        if m:
            result['period_year'] = int(m.group(1))
            result['period_month'] = int(m.group(2))

    if not result['period_year']:
        m = re.search(r'(\d{4})[-/](\d{1,2})', resolved_query)
        if m:
            result['period_year'] = int(m.group(1))
            result['period_month'] = int(m.group(2))

    # 范围: "2025年1月到3月"
    m_range = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*[到至-]\s*(\d{1,2})\s*月', resolved_query)
    if m_range:
        result['period_year'] = int(m_range.group(1))
        result['period_month'] = int(m_range.group(2))
        result['period_end_month'] = int(m_range.group(3))

    # 跨年范围: "2024年1月到2025年3月"
    m_cross_year = re.search(
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*[到至-]\s*(\d{4})\s*年\s*(\d{1,2})\s*月',
        resolved_query
    )
    if m_cross_year:
        start_y = int(m_cross_year.group(1))
        start_m = int(m_cross_year.group(2))
        end_y = int(m_cross_year.group(3))
        end_m = int(m_cross_year.group(4))
        result['period_year'] = start_y
        result['period_month'] = start_m
        if start_y == end_y:
            result['period_end_month'] = end_m
        else:
            # 跨年：记录结束年月，pipeline需要特殊处理
            result['period_end_year'] = end_y
            result['period_end_month'] = end_m

    # 多年范围: "2024年到2026年"
    m_year_range = re.search(r'(\d{4})\s*年\s*[到至-]\s*(\d{4})\s*年', resolved_query)
    if m_year_range and not result.get('period_end_year'):
        start_y = int(m_year_range.group(1))
        end_y = int(m_year_range.group(2))
        result['period_year'] = start_y
        result['period_years'] = list(range(start_y, end_y + 1))

    # 枚举月份: "2025年1月、2月、3月" 或 "1月、2月、3月"
    m_enum = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*[、,]\s*(\d{1,2})\s*月(?:\s*[、,]\s*(\d{1,2})\s*月)?', resolved_query)
    if m_enum:
        result['period_year'] = int(m_enum.group(1))
        months = [int(m_enum.group(2)), int(m_enum.group(3))]
        if m_enum.group(4):
            months.append(int(m_enum.group(4)))
        result['period_months'] = months
        result['period_month'] = months[0]
        result['period_end_month'] = months[-1]

    # "全年" / "2025年" 年度范围（无月份时兜底提取年份）
    if not result['period_year']:
        m_full_year = re.search(r'(\d{4})\s*年\s*全年', resolved_query)
        if m_full_year:
            result['period_year'] = int(m_full_year.group(1))
            result['period_month'] = 1
            result['period_end_month'] = 12

    # 年份兜底：仅"2025年"无月份/季度/年度后缀
    if not result['period_year']:
        m_year_only = re.search(r'(\d{4})\s*年', resolved_query)
        if m_year_only:
            result['period_year'] = int(m_year_only.group(1))

    # 当只有年份（无月份/季度）时，根据域设置默认时间范围
    # 注意：all_quarters=True时，需要全年月份范围而非单月
    if result['period_year'] and not result['period_month'] and not result['period_quarter']:
        if result.get('all_quarters'):
            # "各季度"查询：设置全年范围，让SQL按季度分组
            result['period_month'] = 1
            result['period_end_month'] = 12
        else:
            domain = result['domain_hint']
            if domain == 'vat':
                # 增值税默认"本年累计"
                result['time_range_hint'] = '累计'
                result['period_month'] = 12  # 设置为12月，表示全年
            elif domain == 'eit':
                # 企业所得税默认"年度"（已通过period_year设置）
                pass
            elif domain == 'profit':
                # 利润表默认"本年累计"
                result['time_range_hint'] = '本年累计'
                result['period_month'] = 12  # 设置为12月，表示全年
            elif domain == 'cash_flow':
                # 现金流量表默认"本年累计"
                result['time_range_hint'] = '本年累计'
                result['period_month'] = 12  # 设置为12月，表示全年
            elif domain == 'cross_domain':
                # 跨域查询：为每个子域设置默认时间范围
                # 对于VAT和利润表，设置为12月（本年累计）
                # 对于EIT，保持年度查询（不设置月份）
                cross_list = result.get('cross_domain_list', [])
                if 'vat' in cross_list or 'profit' in cross_list or 'cash_flow' in cross_list:
                    result['period_month'] = 12  # 设置为12月，表示全年
                if 'vat' in cross_list:
                    result['time_range_hint'] = '累计'
            elif domain == 'financial_metrics':
                # 财务指标默认取最新月份（12月）
                result['period_month'] = 12

    # 域推断兜底：有月份无季度 → 检查是否有利润表项目，否则默认VAT
    if result['domain_hint'] is None and result['period_month'] and not result['period_quarter']:
        has_profit_item = any(item in user_query for item in _PROFIT_DEFAULT_ITEMS)
        if has_profit_item:
            result['domain_hint'] = 'profit'
        else:
            result['domain_hint'] = 'vat'

    # 5. 纳税人类型关键词推断（仅VAT域有意义）
    if not result['taxpayer_type']:
        if any(kw in user_query for kw in ['小规模', '3%征收率', '5%征收率', '小微']):
            result['taxpayer_type'] = '小规模纳税人'
        elif any(kw in user_query for kw in ['一般纳税人', '销项', '进项', '留抵']):
            result['taxpayer_type'] = '一般纳税人'

    # 6. time_range / item_type 提示（VAT专用）
    if '累计' in user_query:
        result['time_range_hint'] = '累计'
    elif '本月' in user_query:
        result['time_range_hint'] = '本月'
    elif '本期' in user_query:
        result['time_range_hint'] = '本期'

    if '即征即退' in user_query:
        result['item_type_hint'] = '即征即退项目'
    elif '服务不动产' in user_query or '无形资产' in user_query:
        result['item_type_hint'] = '服务不动产无形资产'

    return result


def normalize_query(user_query: str, scope_view: str, taxpayer_type: str,
                    db_conn: sqlite3.Connection, domain: str = None) -> tuple:
    """同义词替换：最长匹配优先 + 不重叠替换（域感知）"""
    cur = db_conn.cursor()

    # 根据域选择同义词表
    if domain == 'eit':
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM eit_synonyms
            WHERE (scope_view IS NULL OR scope_view = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (scope_view,)
        ).fetchall()
    elif domain == 'account_balance':
        # 科目余额使用 account_synonyms 表，column_name 取 account_name
        rows = cur.execute(
            """SELECT phrase, COALESCE(account_name, account_code) AS column_name, priority
            FROM account_synonyms
            ORDER BY priority DESC, LENGTH(phrase) DESC"""
        ).fetchall()
    elif domain == 'balance_sheet':
        # 资产负债表使用 fs_balance_sheet_synonyms 表
        gaap_filter = None
        if scope_view == 'vw_balance_sheet_sas':
            gaap_filter = 'ASSE'
        elif scope_view == 'vw_balance_sheet_eas':
            gaap_filter = 'ASBE'
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM fs_balance_sheet_synonyms
            WHERE (gaap_type IS NULL OR gaap_type = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (gaap_filter,)
        ).fetchall()
    elif domain == 'profit':
        # 利润表使用 fs_income_statement_synonyms 表
        gaap_filter = None
        if scope_view == 'vw_profit_sas':
            gaap_filter = 'SAS'
        elif scope_view == 'vw_profit_eas':
            gaap_filter = 'CAS'
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM fs_income_statement_synonyms
            WHERE (gaap_type IS NULL OR gaap_type = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (gaap_filter,)
        ).fetchall()
    elif domain == 'cash_flow':
        # 现金流量表使用 fs_cash_flow_synonyms 表
        gaap_filter = None
        if scope_view == 'vw_cash_flow_sas':
            gaap_filter = 'SAS'
        elif scope_view == 'vw_cash_flow_eas':
            gaap_filter = 'CAS'
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM fs_cash_flow_synonyms
            WHERE (gaap_type IS NULL OR gaap_type = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (gaap_filter,)
        ).fetchall()
    elif domain == 'financial_metrics':
        # 财务指标域不做同义词替换 — 指标名称需要保留在查询中供LLM生成WHERE条件
        rows = []
    elif domain == 'invoice':
        # 发票域使用 inv_synonyms 表
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM inv_synonyms
            WHERE (scope_view IS NULL OR scope_view = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (scope_view,)
        ).fetchall()
    else:
        # 默认VAT同义词表
        rows = cur.execute(
            """SELECT phrase, column_name, priority FROM vat_synonyms
            WHERE (scope_view IS NULL OR scope_view = ?)
              AND (taxpayer_type IS NULL OR taxpayer_type = ?)
            ORDER BY priority DESC, LENGTH(phrase) DESC""",
            (scope_view, taxpayer_type)
        ).fetchall()

    hits = []
    occupied = [False] * len(user_query)

    for phrase, col, pri in rows:
        start = 0
        while True:
            idx = user_query.find(phrase, start)
            if idx == -1:
                break
            end = idx + len(phrase)
            if not any(occupied[idx:end]):
                hits.append((idx, end, phrase, col, pri))
                for i in range(idx, end):
                    occupied[i] = True
            start = idx + 1

    # 按位置倒序替换
    hits.sort(key=lambda x: x[0], reverse=True)
    normalized = user_query
    for idx, end, phrase, col, pri in hits:
        normalized = normalized[:idx] + col + normalized[end:]

    # 正序返回hits
    hits.sort(key=lambda x: x[0])
    hit_list = [{'phrase': h[2], 'column_name': h[3], 'priority': h[4]} for h in hits]

    return normalized, hit_list


def get_scope_view(taxpayer_type: str, domain: str = None, report_type: str = None,
                    accounting_standard: str = None) -> str:
    """根据纳税人类型/域/报表类型/会计准则返回对应视图"""
    if domain == 'eit':
        if report_type == 'quarter':
            return 'vw_eit_quarter_main'
        return 'vw_eit_annual_main'  # 默认年度
    if domain == 'account_balance':
        return 'vw_account_balance'
    if domain == 'balance_sheet':
        # 根据会计准则选择视图
        if accounting_standard == '小企业会计准则':
            return 'vw_balance_sheet_sas'
        return 'vw_balance_sheet_eas'  # 默认企业会计准则
    if domain == 'profit':
        # 根据会计准则选择利润表视图
        if accounting_standard == '小企业会计准则':
            return 'vw_profit_sas'
        return 'vw_profit_eas'  # 默认企业会计准则
    if domain == 'cash_flow':
        # 根据会计准则选择现金流量表视图
        if accounting_standard == '小企业会计准则':
            return 'vw_cash_flow_sas'
        return 'vw_cash_flow_eas'  # 默认企业会计准则
    if domain == 'financial_metrics':
        return 'vw_financial_metrics'
    if domain == 'invoice':
        return 'vw_inv_spec_purchase'  # 默认进项视图，pipeline会根据direction调整
    # VAT
    if taxpayer_type == '一般纳税人':
        return 'vw_vat_return_general'
    elif taxpayer_type == '小规模纳税人':
        return 'vw_vat_return_small'
    return None