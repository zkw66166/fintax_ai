# 数据管理模块技术文档

## Context

用户请求对"数据管理"模块进行完整的前后端技术分析，生成详细技术文档。该模块是 MCP_coze 税务智能咨询平台的核心数据管理功能，包含单户企业数据管理、多户企业数据管理、数据浏览三大功能区。

本文档将作为最终交付物，涵盖前端组件架构、后端API设计、数据质量检查规则全集、ETL管道等完整内容。

---

## 一、模块总览

### 1.1 功能定位

数据管理模块负责企业财务数据的导入、浏览、质量检查和状态监控，是平台数据治理的核心入口。

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + Vite, Lucide Icons, CSS Modules |
| 后端 | FastAPI (Python), SQLite3 |
| ETL | 自研 Python ETL 管道 + YAML 规则引擎 |
| 数据库 | SQLite (`financial.db`) |

### 1.3 文件清单

**前端文件：**
- `frontend/src/components/DataManagement.jsx` — 主容器组件 (750行)
- `frontend/src/components/DataManagement.css` — 主样式 (399行)
- `frontend/src/components/DataBrowser.jsx` — 数据浏览子组件 (307行)
- `frontend/src/components/DataBrowser.css` — 数据浏览样式 (187行)
- `frontend/src/components/VatReturnRawView.jsx` + `.css` — 增值税原表
- `frontend/src/components/IncomeStatementRawView.jsx` + `.css` — 利润表原表
- `frontend/src/components/BalanceSheetRawView.jsx` + `.css` — 资产负债表原表
- `frontend/src/components/CashFlowStatementRawView.jsx` + `.css` — 现金流量表原表
- `frontend/src/components/CITReturnRawView.jsx` + `.css` — 企业所得税原表
- `frontend/src/services/api.js` — API 调用函数

**后端文件：**
- `server/routers/data_management.py` — 数据管理 API 路由
- `server/routers/data_browser.py` — 数据浏览 API 路由
- `server/services/data_quality.py` — 数据质量检查服务

**ETL 文件：**
- `etl/validators/rule_engine.py` — 校验规则引擎
- `etl/validators/validation_service.py` — 校验服务
- `etl/validators/import_validator.py` — 导入后即时校验
- `etl/config/validation_rules/intra_table/*.yaml` — 表内校验规则
- `etl/config/validation_rules/inter_table/cross_validation.yaml` — 表间校验规则

---

## 二、前端架构

### 2.1 组件层级关系

```
MainApp.jsx
  └── DataManagement (props: selectedCompanyId)
        ├── Tab: 单户企业数据 → SingleCompanyTab (内联组件)
        ├── Tab: 多户企业数据 → MultiCompanyTab (内联组件)
        └── Tab: 数据浏览 → DataBrowser (独立组件)
                                ├── VatReturnRawView
                                ├── IncomeStatementRawView
                                ├── BalanceSheetRawView
                                ├── CashFlowStatementRawView
                                └── CITReturnRawView
```

### 2.2 DataManagement 主组件

**文件：** `frontend/src/components/DataManagement.jsx`

**Props：**
| 属性 | 类型 | 说明 |
|------|------|------|
| `selectedCompanyId` | `number` | 当前选中的企业ID，由 MainApp Header 下拉框传入 |

**State 变量：**
| 变量 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `activeTab` | `string` | `'single'` | 当前激活的 Tab：`single`/`multi`/`browse` |
| `uploadedFiles` | `array` | `[]` | 模拟上传的文件列表 |
| `companySearchTerm` | `string` | `''` | 多户企业搜索关键词 |
| `selectedCompanies` | `array` | `[]` | 多户企业选中列表 |
| `stats` | `object` | `{summary, companies, quality_checks, mapping_synonyms, update_frequency}` | 统计数据 |
| `loading` | `boolean` | `false` | 加载状态 |
| `checkResults` | `object\|null` | `null` | 质量检查结果 |
| `checking` | `boolean` | `false` | 质量检查进行中 |

**核心函数：**

| 函数 | 说明 |
|------|------|
| `handleRunCheck()` | 调用 `runDataQualityCheck(selectedCompanyId)` 执行数据质量检查，结果存入 `checkResults` |
| `handleFileUpload(event)` | 模拟文件上传，创建文件对象并模拟进度条 (0→100%, 每200ms +10%) |
| `getStatusColor(status)` | 状态→颜色映射：Data Complete→green, Incomplete→yellow, 数据异常→red |
| `getMatchColor(match)` | 匹配度→颜色：≥90%→green, ≥70%→yellow, <70%→red |
| `handleCompanySelect(companyId)` | 多户企业 Tab 中切换企业选中状态 |
| `getIconForCheck(status)` | 检查状态→图标映射：Pass→CheckCircle, Warning→AlertTriangle, Pending→Clock |

**数据加载逻辑 (useEffect)：**
- 当 `activeTab` 或 `selectedCompanyId` 变化时触发
- 单户模式：传 `selectedCompanyId` 调用 `fetchDataManagementStats`
- 多户模式：传 `null` 获取聚合统计

### 2.3 Tab 1：单户企业数据 (SingleCompanyTab)

该 Tab 包含 6 个功能卡片，从上到下依次为：

#### 2.3.1 数据管理中心（仪表盘）

4 个统计卡片，网格布局 (`dm-stats-grid`, 4列)：

| 卡片 | 数据字段 | 颜色 | 图标 |
|------|----------|------|------|
| 财务指标数量 | `stats.summary.subject_count` | 蓝色 | Database |
| 报表/数据条目 | `stats.summary.report_count` | 绿色 | FileText |
| 数据期间（月） | `stats.summary.period_count` | 紫色 | Archive |
| 数据完整度 | `stats.summary.completeness` + "%" | 黄色 | CheckCircle |

#### 2.3.2 智能数据映射（指标同义词）

表格展示标准指标与同义词的映射关系。

| 列名 | 数据来源 | 渲染方式 |
|------|----------|----------|
| 标准指标名称 | `item.standard` | 文本 |
| 识别同义词 | `item.synonyms[]` | 灰色标签组 (`dm-tag gray`) |
| 状态 | `item.status` | 绿色标签 |
| 匹配度 | `item.match` + "%" | 数值 + 进度条 (颜色由 `getMatchColor` 决定) |

数据来源：后端 `_get_mapping_synonyms()` 硬编码返回 7 组映射。

#### 2.3.3 数据质量检查

这是单户 Tab 的核心功能区。

**头部区域：**
- 汇总统计：共 X 期 | 检查 X 项 | 通过率 X% (来自 `checkResults.summary`)
- "开始检测"按钮：触发 `handleRunCheck()`，检测中显示旋转图标

**检查结果展示：**

覆盖 7 种报表类型，每种以可展开的 `<details>` 元素呈现：

| 报表类型 key | 中文名 |
|-------------|--------|
| `subject_balance` | 科目余额表 |
| `balance_sheet` | 资产负债表 |
| `income_statement` | 利润表 |
| `cash_flow` | 现金流量表 |
| `vat_return` | 增值税申报表 |
| `cit_return` | 企业所得税申报表 |
| `stamp_duty` | 印花税申报表 |

每种报表的展示结构：
- **Summary 行**：图标(✓/✗/⏱) + 表名 + "X期数据 | 通过X | 异常X" + 状态标签
- **展开详情**：网格布局 (`grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`)，每期一个 `PeriodCard`

**PeriodCard 子组件** (独立组件，支持 useState)：
- 显示期间名称 + 状态徽章 (✓/异常数)
- 异常项列表：默认显示前 2 项，超过 2 项可点击展开
- 每项显示：检查名称 + 错误消息

#### 2.3.4 数据更新频率

表格展示各数据源的更新频率信息。

| 列 | 说明 |
|----|------|
| 数据源 | 资产负债表/利润表/现金流量表/增值税申报表/企业所得税申报表/印花税申报表/科目余额表 |
| 更新频率 | 月度/季度 |
| 上次更新 | 日期字符串 |
| 状态 | 固定显示"正常"绿色标签 |

#### 2.3.5 数据使用统计

左侧 3 个指标 + 右侧 CSS 柱状图占位符：
- 本月查询次数：1,245 (Mock)
- 生成报告数：56 (Mock)
- API调用量：8,932 (Mock)
- 近6个月趋势图 (纯 CSS div 柱状图)

#### 2.3.6 智能数据导入（演示功能）

- 拖拽上传区域 (虚线边框)
- 支持格式提示：Excel、CSV、PDF
- "选择文件"按钮 → 触发 `handleFileUpload`
- 上传为模拟功能，不实际发送到后端

### 2.4 Tab 2：多户企业数据 (MultiCompanyTab)

#### 2.4.1 多户企业数据概览

单个统计卡片：
- 管理企业总数：`stats.companies.length`

#### 2.4.2 企业数据状况列表

**工具栏：**
- 搜索框：按企业名称或税号过滤 (`companySearchTerm`)
- 筛选按钮 (UI占位，无实际逻辑)
- 导出按钮 (UI占位，无实际逻辑)

**表格列：**

| 列 | 数据字段 | 渲染方式 |
|----|----------|----------|
| 复选框 | — | `<input type="checkbox">` |
| 企业信息 | `company.name` + `company.taxCode` | 名称(粗体) + 税号(灰色小字) |
| 数据状态 | `company.status` | 彩色标签 (由 `getStatusColor` 决定) |
| 数据完整度 | `company.completeness` | 百分比 + 进度条 |
| 最后更新 | `company.lastUpdate` | 日期文本 |

### 2.5 Tab 3：数据浏览 (DataBrowser)

**文件：** `frontend/src/components/DataBrowser.jsx`

独立组件，无 Props。

**State 变量：**

| 变量 | 类型 | 说明 |
|------|------|------|
| `companies` | `array` | 企业列表 |
| `tables` | `array` | 数据表列表 |
| `periods` | `array` | 可用期间列表 |
| `viewMode` | `string` | `'general'` 或 `'raw'` |
| `selectedCompany` | `string` | 选中企业ID |
| `selectedTable` | `string` | 选中表名 |
| `selectedPeriod` | `string` | 选中期间 |
| `tableData` | `object\|null` | 表数据 `{columns, data, total}` |
| `loading` | `boolean` | 加载状态 |
| `error` | `string\|null` | 错误信息 |

**初始化逻辑：**
1. 并行加载企业列表和表列表
2. 默认选中第一个企业
3. 默认选中 `income_statements` 表（若存在），否则选第一个

**筛选栏 (Filter Bar)：**
- 选择企业：下拉框 + Filter 图标
- 选择数据表：下拉框 + Database 图标（切换表时自动重置为通表格式）
- 选择期间：下拉框 + Calendar 图标（通表格式可选"全部期间"，原表格式必须选具体期间）
- 视图切换按钮组（右对齐）：通表格式 (List图标) / 原表格式 (FileText图标)

#### 2.5.1 通表格式 (General View)

标准数据表格展示：
- 表头：表名 + 数据条数
- 表格：动态列（来自 API `columns` 字段），sticky header，水平/垂直滚动
- 空状态："暂无数据"
- 加载状态：spinner + "加载中..."

#### 2.5.2 原表格式 (Raw View)

按官方报表格式渲染数据，仅支持以下 5 种表：

| 表名 | 组件 | 标题 |
|------|------|------|
| `tax_returns_vat` | `VatReturnRawView` | 增值税及附加税费申报表（一般纳税人适用） |
| `income_statements` | `IncomeStatementRawView` | 利润表 |
| `balance_sheets` | `BalanceSheetRawView` | 资产负债表 |
| `cash_flow_statements` | `CashFlowStatementRawView` | 现金流量表 |
| `tax_returns_income` | `CITReturnRawView` | 中华人民共和国企业所得税年度纳税申报表（A类） |

不支持的表显示提示信息 + "返回通表格式"按钮。

**原表组件通用 Props：**
| Prop | 类型 | 说明 |
|------|------|------|
| `data` | `object` | 单行数据（`tableData.data[0]`） |
| `companyInfo` | `object` | 企业信息 `{name, tax_code, industry, legal_person, address}` |

**原表组件通用特性：**
- 中文货币格式化 (2位小数)
- 企业信息头部（名称、税号、期间、单位）
- 按官方税务表格样式排版
- N/A 处理不适用字段

### 2.6 前端 API 调用汇总

| 函数 | 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|------|
| `fetchDataManagementStats(companyId)` | `/api/data-management/stats` | GET | `company_id` (可选) | 获取仪表盘统计 |
| `runDataQualityCheck(companyId)` | `/api/data-management/quality-check` | POST | `company_id` (可选) | 执行质量检查 |
| `fetchBrowseCompanies()` | `/api/data-browser/companies` | GET | 无 | 获取企业列表 |
| `fetchBrowseTables()` | `/api/data-browser/tables` | GET | 无 | 获取支持的表列表 |
| `fetchBrowsePeriods(companyId, tableName)` | `/api/data-browser/periods` | GET | `company_id`, `table_name` | 获取期间列表 |
| `fetchBrowseData(companyId, tableName, period)` | `/api/data-browser/data` | GET | `company_id`, `table_name`, `period`(可选) | 获取表数据 |

所有 API 调用通过 `frontend/src/services/api.js` 统一管理，使用 Bearer Token 认证。

---

## 三、后端 API 设计

### 3.1 数据管理路由 (`server/routers/data_management.py`)

**路由前缀：** `/api/data-management`

#### 3.1.1 GET `/api/data-management/stats`

获取数据管理仪表盘统计信息。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `company_id` | `int` | 否 | 传入则返回单户统计，不传返回多户聚合 |

**响应结构：**
```json
{
  "summary": {
    "subject_count": 30,
    "report_count": 156,
    "period_count": 24,
    "completeness": 95.0
  },
  "companies": [
    {
      "id": 1,
      "name": "XX公司",
      "taxCode": "91110...",
      "status": "Data Complete",
      "lastUpdate": "2024-12-15",
      "dataTypes": ["Financial Statements", "Tax Returns"],
      "completeness": 95,
      "issues": 0
    }
  ],
  "quality_checks": [...],
  "mapping_synonyms": [...],
  "update_frequency": [...]
}
```

**业务逻辑：**
1. 查询 `companies` 表获取企业信息
2. 遍历 7 张数据表统计记录数：`balance_sheet`, `income_statements`, `cash_flow_statements`, `tax_returns_income`, `tax_returns_vat`, `tax_returns_stamp`, `invoices`
3. 从 `financial_metrics` 表统计期间数
4. 完整度：有数据则 95%，无数据则 0%（简化逻辑）
5. 多户模式下遍历每个企业生成状态列表
6. 同义词映射和更新频率为硬编码数据

#### 3.1.2 POST `/api/data-management/quality-check`

执行数据质量检查。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `company_id` | `int` | 否 | 不传默认使用 company_id=5 |

**响应结构：**
```json
{
  "company_id": 5,
  "summary": {
    "total_tables": 7,
    "total_periods": 24,
    "total_checks": 120,
    "passed_checks": 115,
    "failed_checks": 5,
    "pass_rate": 95.8
  },
  "results_by_table": {
    "subject_balance": {
      "table_name": "科目余额表",
      "db_table": "account_balances",
      "period_count": 12,
      "status": "pass|fail|skip",
      "periods": [
        {
          "period": "2024Q4",
          "year": 2024,
          "month": 12,
          "status": "pass|fail|skip",
          "message": "",
          "total_checks": 5,
          "passed_checks": 5,
          "details": [
            {
              "check": "科目余额内部勾稽",
              "status": "pass|fail",
              "message": "所有科目勾稽正确"
            }
          ]
        }
      ]
    }
  }
}
```

**调用链：** `data_management.py` → `DataQualityChecker.check_all()` → 各 `check_*` 方法

### 3.2 数据浏览路由 (`server/routers/data_browser.py`)

**路由前缀：** `/api/data-browser`

**支持的数据表：**

| 表名 | 中文标签 |
|------|----------|
| `companies` | 工商登记信息 |
| `balance_sheets` | 资产负债表 |
| `income_statements` | 利润表 |
| `cash_flow_statements` | 现金流量表 |
| `account_balances` | 科目余额表 |
| `tax_returns_vat` | 增值税申报表 |
| `tax_returns_income` | 企业所得税申报表 |
| `tax_returns_stamp` | 印花税申报表 |
| `invoices` | 发票数据 |

#### 3.2.1 GET `/api/data-browser/tables`

返回所有支持的数据表名称和中文标签。

**响应：** `[{"name": "companies", "label": "工商登记信息"}, ...]`

#### 3.2.2 GET `/api/data-browser/companies`

返回所有企业列表（含全部字段）。

**响应：** `[{"id": 1, "name": "XX公司", "tax_code": "91110...", ...}]`

#### 3.2.3 GET `/api/data-browser/periods`

获取指定企业和表的可用数据期间。

**参数：** `company_id` (int), `table_name` (str)

**期间格式化逻辑：**
- 月度表 (有 `period_month`)：`"2024年12月"`
- 季度表 (有 `period_quarter`)：`"2024年Q4"`
- 年度表 (仅 `period_year`)：`"2024年"`
- 特殊处理：`tax_returns_vat` 优先使用月度格式

#### 3.2.4 GET `/api/data-browser/data`

获取表数据（不分页）。

**参数：** `company_id` (int), `table_name` (str), `period` (str, 可选)

**业务逻辑：**
1. 通过 `PRAGMA table_info` 获取表列信息
2. 调用 `get_column_mapping(table_name)` 获取中英文字段映射
3. 构建列头 `[{key, label}]`
4. 解析期间参数：支持 "2024年Q1"、"2024年12月"、"2024年" 三种格式
5. 按时间倒序排列
6. 增值税表特殊处理：计算 `start_date` 和 `end_date`

**字段映射系统 (`get_column_mapping`)：**

为每张表维护完整的英文字段→中文名映射，包括：
- 通用字段映射 (id, company_id, period_year 等)
- `metrics_config.json` 中的动态映射
- 各表专用映射（companies 20+字段, invoices 12字段, income_statements 25字段, balance_sheets 40+字段, tax_returns_vat 80+字段, tax_returns_income 15字段）

---

## 四、数据质量检查系统

### 4.1 架构概述

系统包含三层数据质量检查机制：

| 层级 | 实现 | 触发时机 | 用途 |
|------|------|----------|------|
| **运行时检查** | `server/services/data_quality.py` | 用户点击"开始检测" | 前端展示，7种表×所有期间 |
| **ETL规则引擎** | `etl/validators/rule_engine.py` + YAML | ETL管道执行时 | 数据导入校验 |
| **导入后即时校验** | `etl/validators/import_validator.py` | 数据导入完成后 | 即时反馈导入质量 |

### 4.2 运行时检查 (`DataQualityChecker`)

**文件：** `server/services/data_quality.py`

**表配置：**

| 检查键 | 中文名 | 期间类型 | 数据库表 |
|--------|--------|----------|----------|
| `subject_balance` | 科目余额表 | 月度 | `account_balances` |
| `balance_sheet` | 资产负债表 | 月度 | `balance_sheets` |
| `income_statement` | 利润表 | 月度 | `income_statements` |
| `cash_flow` | 现金流量表 | 月度 | `cash_flow_statements` |
| `vat_return` | 增值税申报表 | 月度 | `tax_returns_vat` |
| `cit_return` | 企业所得税申报表 | 季度 | `tax_returns_income` |
| `stamp_duty` | 印花税申报表 | 季度 | `tax_returns_stamp` |

**执行流程：**
1. `check_all(company_id)` → 获取所有表的可用期间
2. 遍历每张表的每个期间，调用对应的 `check_*` 方法
3. 汇总统计：总检查数、通过数、失败数、通过率
4. 表级状态：全部通过→pass，有失败→fail，无数据→skip

#### 4.2.1 科目余额表检查 (`check_subject_balance`)

**检查逻辑：** 逐行校验余额勾稽关系

| 规则 | 公式 | 容差 | 说明 |
|------|------|------|------|
| 余额勾稽 | `期初 + 借方 - 贷方 = 期末` 或 `期初 - 借方 + 贷方 = 期末` | 0.01 | 两个方向都尝试，任一满足即通过 |

- 无数据时返回 `skip`
- 全部通过时返回单条 "所有科目勾稽正确"
- 失败时返回每个异常科目的详细信息：`"期初({opening}) + 借方({debit}) - 贷方({credit}) ≠ 期末({closing})"`

#### 4.2.2 资产负债表检查 (`check_balance_sheet`)

| 规则 | 公式 | 容差 |
|------|------|------|
| 资产=负债+权益 | `total_assets == total_liabilities + total_equity` | 0.01 |
| 资产结构 | `total_assets == current_assets_total + non_current_assets_total` | 0.01 |
| 负债结构 | `total_liabilities == current_liabilities_total + non_current_liabilities_total` | 0.01 |
| 流动资产明细 | `current_assets_total == cash_and_equivalents + trading_financial_assets + accounts_receivable + prepayments + other_receivables + inventory + notes_receivable + contract_assets + current_assets` | 1000 |
| 非流动资产明细 | `non_current_assets_total == long_term_equity_investment + fixed_assets + construction_in_progress + intangible_assets + goodwill + long_term_deferred_expenses + deferred_tax_assets + other_non_current_assets` | 1000 |

#### 4.2.3 利润表检查 (`check_income_statement`)

| 规则 | 公式 | 容差 |
|------|------|------|
| 营业利润计算 | `operating_profit == operating_revenue - operating_costs - taxes_and_surcharges - selling_expenses - administrative_expenses - financial_expenses + other_income + investment_income` | 1.0 |
| 利润总额计算 | `total_profit == operating_profit + non_operating_income - non_operating_expenses` | 1.0 |
| 净利润计算 | `net_profit == total_profit - income_tax_expense` | 1.0 |

#### 4.2.4 现金流量表检查 (`check_cash_flow`)

| 规则 | 公式 | 容差 |
|------|------|------|
| 经营活动净额 | `net_cash_operating == subtotal_operate_inflow - subtotal_operate_outflow` | 0.01 |
| 投资活动净额 | `net_cash_investing == subtotal_invest_inflow - subtotal_invest_outflow` | 0.01 |
| 筹资活动净额 | `net_cash_financing == subtotal_finance_inflow - subtotal_finance_outflow` | 0.01 |
| 现金净增加额 | `net_increase_cash == net_cash_operating + net_cash_investing + net_cash_financing + exchange_rate_effect` | 0.01 |
| 期末现金余额 | `cash_ending == cash_beginning + net_increase_cash` | 0.01 |

#### 4.2.5 增值税申报表检查 (`check_vat_return`)

| 规则 | 公式 | 容差 | 说明 |
|------|------|------|------|
| 增值税进销项逻辑 | `gen_tax_payable_current ≈ gen_output_tax_current - gen_input_tax_current` | 1000.0 | 实际计算复杂（含转出、留抵等），使用大容差；超出容差也标记为 pass 并附注 |

#### 4.2.6 企业所得税申报表检查 (`check_cit_return`)

| 规则 | 公式 | 容差 |
|------|------|------|
| 利润总额计算 | `total_profit == revenue - cost - taxes_and_surcharges - selling_expenses - administrative_expenses - financial_expenses` | 1.0 |
| 应纳税额计算 | `nominal_tax == taxable_income × tax_rate` | 1.0 |
| 实际应纳税额 | `final_tax_payable == nominal_tax - tax_reduction` | 1.0 |

#### 4.2.7 印花税申报表检查 (`check_stamp_duty`)

| 规则 | 公式 | 容差 | 说明 |
|------|------|------|------|
| 印花税计算 | `tax_payable == tax_base × tax_rate` | 0.01 | 逐项检查 `tax_return_stamp_items` 表中每个税目 |

### 4.3 ETL 规则引擎校验规则 (YAML 配置)

**文件位置：** `etl/config/validation_rules/`

#### 4.3.1 资产负债表表内规则 (`intra_table/balance_sheet.yaml`)

| 规则ID | 规则名称 | 表达式 | 严重级别 | 容差 |
|--------|----------|--------|----------|------|
| BS001 | 资产总计=流动资产合计+非流动资产合计 | `total_assets == current_assets_total + non_current_assets_total` | ERROR | 0.01 |
| BS002 | 负债合计=流动负债合计+非流动负债合计 | `total_liabilities == current_liabilities_total + non_current_liabilities_total` | ERROR | 0.01 |
| BS003 | 资产总计=负债合计+所有者权益合计 | `total_assets == total_liabilities + total_equity` | ERROR | 0.01 |
| BS004 | 负债和所有者权益总计=资产总计 | `total_liabilities_and_equity == total_assets` | ERROR | 0.01 |
| BS005 | 所有者权益包含实收资本、资本公积、盈余公积、未分配利润 | `total_equity >= paid_in_capital + capital_surplus + surplus_reserves + retained_earnings` | WARNING | — |

> BS005 使用 `>=` 因为可能存在其他权益项目。

#### 4.3.2 利润表表内规则 (`intra_table/income_statement.yaml`)

| 规则ID | 规则名称 | 表达式 | 严重级别 | 容差 | 备注 |
|--------|----------|--------|----------|------|------|
| IS001 | 营业利润=营业收入-营业成本-税金及附加-销售费用-管理费用-财务费用 | `operating_profit == operating_revenue - operating_costs - taxes_and_surcharges - selling_expenses - administrative_expenses - financial_expenses` | WARNING | 0.05 | 简化公式，实际还需考虑其他项目 |
| IS002 | 利润总额=营业利润+营业外收入-营业外支出 | `total_profit == operating_profit + non_operating_income - non_operating_expenses` | ERROR | 0.01 | |
| IS003 | 净利润=利润总额-所得税费用 | `net_profit == total_profit - income_tax_expense` | ERROR | 0.01 | |
| IS004 | 营业收入应为正数或零 | `operating_revenue >= 0` | WARNING | — | 负数可能表示冲减 |
| IS005 | 所得税费用应与利润方向一致 | `(total_profit >= 0 and income_tax_expense >= 0) or (total_profit < 0 and income_tax_expense <= 0)` | INFO | — | 亏损企业一般无所得税费用 |

#### 4.3.3 现金流量表表内规则 (`intra_table/cash_flow.yaml`)

| 规则ID | 规则名称 | 表达式 | 严重级别 | 容差 |
|--------|----------|--------|----------|------|
| CF001 | 经营活动净现金流=流入小计-流出小计 | `net_cash_operating == subtotal_operate_inflow - subtotal_operate_outflow` | ERROR | 0.01 |
| CF002 | 投资活动净现金流=流入小计-流出小计 | `net_cash_investing == subtotal_invest_inflow - subtotal_invest_outflow` | ERROR | 0.01 |
| CF003 | 筹资活动净现金流=流入小计-流出小计 | `net_cash_financing == subtotal_finance_inflow - subtotal_finance_outflow` | ERROR | 0.01 |
| CF004 | 现金净增加额=经营+投资+筹资+汇率影响 | `net_increase_cash == net_cash_operating + net_cash_investing + net_cash_financing + exchange_rate_effect` | ERROR | 0.01 |
| CF005 | 期末现金=期初现金+现金净增加额 | `cash_ending == cash_beginning + net_increase_cash` | ERROR | 0.01 |

#### 4.3.4 增值税申报表表内规则 (`intra_table/vat_return.yaml`)

| 规则ID | 规则名称 | 表达式 | 严重级别 | 容差 | 备注 |
|--------|----------|--------|----------|------|------|
| VAT001 | 应抵扣税额合计=期初留抵+本期进项-进项转出-免抵退应退+检查补税 | `gen_total_deductible_current == gen_previous_credit_current + gen_input_tax_current - gen_input_transfer_out_current - gen_export_refund_current + gen_audit_payable_current` | ERROR | 0.01 | 一般纳税人增值税申报表校验 |
| VAT002 | 应纳税额=销项税额-实际抵扣税额 | `gen_tax_payable_current == gen_output_tax_current - gen_actual_deduction_current` | ERROR | 0.01 | |
| VAT003 | 期末留抵=应抵扣税额-实际抵扣税额 | `gen_ending_credit_current == gen_total_deductible_current - gen_actual_deduction_current` | WARNING | 0.01 | |
| VAT004 | 实际抵扣税额不能超过应抵扣税额 | `gen_actual_deduction_current <= gen_total_deductible_current` | WARNING | — | |
| VAT005 | 销项税额应为非负数 | `gen_output_tax_current >= 0` | INFO | — | 红字发票可能导致负数 |

#### 4.3.5 企业所得税申报表表内规则 (`intra_table/cit_return.yaml`)

| 规则ID | 规则名称 | 表达式 | 严重级别 | 容差 | 备注 |
|--------|----------|--------|----------|------|------|
| CIT001 | 利润总额=营业利润+营业外收入-营业外支出 | `total_profit == operating_profit + non_operating_revenue - non_operating_expense` | ERROR | 0.01 | |
| CIT002 | 营业利润=营业收入-营业成本-税金及附加-费用 | `operating_profit == revenue - cost - taxes_and_surcharges - selling_expenses - administrative_expenses - financial_expenses` | WARNING | 1.0 | 简化公式，实际可能有其他调整项 |
| CIT003 | 应纳税所得额=调整后所得-所得减免-抵扣所得-弥补亏损 | `taxable_income == adjusted_income - income_exemption - deductible_income - loss_carryforward` | ERROR | 0.01 | |
| CIT004 | 应纳所得税额=应纳税所得额×税率 | `nominal_tax == taxable_income * tax_rate` | WARNING | 0.1 | 税率通常为25%，小微企业可能有优惠 |
| CIT005 | 应补退税额=应纳税额-已预缴税额 | `annual_tax_payable == actual_tax_payable - prepaid_tax` | ERROR | 0.01 | |
| CIT006 | 应纳税所得额不为负数 | `taxable_income >= 0` | INFO | — | 允许为0或负数（亏损） |

#### 4.3.6 表间交叉校验规则 (`inter_table/cross_validation.yaml`)

| 规则ID | 规则名称 | 涉及表 | 表达式 | 严重级别 | 容差 | 备注 |
|--------|----------|--------|--------|----------|------|------|
| CROSS001 | 利润表营业收入≈所得税申报表营业收入 | income_statements, tax_returns_income | `abs(income_statements.operating_revenue - tax_returns_income.revenue) / max(income_statements.operating_revenue, 1) < 0.01` | WARNING | 0.01 | |
| CROSS002 | 利润表利润总额≈所得税申报表利润总额 | income_statements, tax_returns_income | `abs(income_statements.total_profit - tax_returns_income.total_profit) / max(abs(income_statements.total_profit), 1) < 0.01` | WARNING | 0.01 | |
| CROSS003 | 现金流量表期末现金≈资产负债表货币资金 | cash_flow_statements, balance_sheets | `abs(cash_flow_statements.cash_ending - balance_sheets.cash_and_equivalents) / max(cash_flow_statements.cash_ending, 1) < 0.05` | WARNING | 0.05 | 现金等价物口径可能略有差异 |
| CROSS004 | 期末未分配利润变动≈净利润-利润分配 | balance_sheets, income_statements | `balance_sheets.retained_earnings - balance_sheets_prev.retained_earnings <= income_statements.net_profit * 1.1` | INFO | — | 需考虑利润分配影响 |
| CROSS005 | 增值税销售额×(1+税率)大约等于利润表营业收入 | tax_returns_vat, income_statements | `tax_returns_vat.gen_sales_taxable_ytd * 1.13 >= income_statements.operating_revenue * 0.8` | INFO | — | 粗略校验，存在免税/简易计税/出口退税等情况 |

### 4.4 导入后即时校验 (`ImportValidator`)

**文件：** `etl/validators/import_validator.py`

在数据导入完成后立即执行，针对 v2 版本表结构（`balance_sheets_v2`, `income_statements_v2`, `cash_flow_statements_v3`）。

#### 4.4.1 资产负债表导入校验

| 规则ID | 规则名称 | 公式 | 说明 |
|--------|----------|------|------|
| BS001 | 资产总计=流动资产+非流动资产(期末) | `total_assets_ending == current_assets_total_ending + non_current_assets_total_ending` | |
| BS001b | 资产总计=流动资产+非流动资产(年初) | `total_assets_beginning == current_assets_total_beginning + non_current_assets_total_beginning` | |
| BS002 | 资产总计=负债+权益(期末) | `total_assets_ending == total_liabilities_ending + total_equity_ending` | |
| BS002b | 资产总计=负债+权益(年初) | `total_assets_beginning == total_liabilities_beginning + total_equity_beginning` | |
| BS003 | 负债合计=流动负债+非流动负债(期末) | `total_liabilities_ending == current_liabilities_total_ending + non_current_liabilities_total_ending` | |
| BS003b | 负债合计=流动负债+非流动负债(年初) | `total_liabilities_beginning == current_liabilities_total_beginning + non_current_liabilities_total_beginning` | |
| BS004 | 负债和权益总计=负债+权益(期末) | `total_liabilities_and_equity_ending == total_liabilities_ending + total_equity_ending` | |
| BS004b | 负债和权益总计=负债+权益(年初) | `total_liabilities_and_equity_beginning == total_liabilities_beginning + total_equity_beginning` | |

#### 4.4.2 利润表导入校验

| 规则ID | 规则名称 | 公式 |
|--------|----------|------|
| IS001 | 利润总额=营业利润+营业外收支(本期) | `total_profit_current == operating_profit_current + non_operating_income_current - non_operating_expenses_current` |
| IS001b | 利润总额=营业利润+营业外收支(累计) | `total_profit_ytd == operating_profit_ytd + non_operating_income_ytd - non_operating_expenses_ytd` |
| IS002 | 净利润=利润总额-所得税费用(本期) | `net_profit_current == total_profit_current - income_tax_expense_current` |
| IS002b | 净利润=利润总额-所得税费用(累计) | `net_profit_ytd == total_profit_ytd - income_tax_expense_ytd` |

#### 4.4.3 现金流量表导入校验

| 规则ID | 规则名称 | 公式 |
|--------|----------|------|
| CF001 | 现金净增加=经营+投资+筹资+汇率(本期) | `net_increase_in_cash_current == net_cash_from_operating_current + net_cash_from_investing_current + net_cash_from_financing_current + exchange_rate_effect_current` |
| CF001b | 现金净增加=经营+投资+筹资+汇率(累计) | `net_increase_in_cash_ytd == net_cash_from_operating_ytd + net_cash_from_investing_ytd + net_cash_from_financing_ytd + exchange_rate_effect_ytd` |
| CF002 | 期末现金=期初现金+现金净增加(本期) | `cash_at_end_current == cash_at_beginning_current + net_increase_in_cash_current` |
| CF002b | 期末现金=期初现金+现金净增加(累计) | `cash_at_end_ytd == cash_at_beginning_ytd + net_increase_in_cash_ytd` |

#### 4.4.4 表间交叉校验（导入后）

| 规则ID | 规则名称 | 涉及表 | 公式 |
|--------|----------|--------|------|
| CROSS001 | 资产负债表货币资金=现金流量表期末现金 | balance_sheets_v2, cash_flow_statements_v2 | `cash_ending ≈ cash_at_end_current` |
| CROSS002 | 资产负债表存货=科目余额表存货 | balance_sheets_v2, account_balances | `inventory_ending ≈ 科目余额表中"存货"科目的ending_balance` |

**容差规则：** 差异 > 0.01 为 error，0.001~0.01 为 warning

### 4.5 规则引擎架构 (`ValidationRuleEngine`)

**文件：** `etl/validators/rule_engine.py`

**核心数据结构：**

```python
@dataclass
class ValidationRule:
    id: str                    # 规则标识符
    name: str                  # 规则名称
    expression: str            # 校验表达式
    severity: Severity         # error / warning / info
    tolerance: float           # 数值容差 (默认 0.01)
    note: str                  # 备注
    tables: List[str]          # 涉及的表 (跨表规则)

class Severity(Enum):
    ERROR = "error"      # 阻断性错误
    WARNING = "warning"  # 警告，不阻断
    INFO = "info"        # 信息提示
```

**表达式求值：**
- 支持运算符：`==`, `>=`, `<=`
- 支持算术：`+`, `-`, `*`, `/`, `()`
- 字段引用：直接字段名（表内）或 `table.field`（跨表）
- 安全求值：仅允许数字和基本运算符字符集

**规则加载：**
- 从 `etl/config/validation_rules/intra_table/*.yaml` 加载表内规则
- 从 `etl/config/validation_rules/inter_table/*.yaml` 加载表间规则
- 支持 `reload()` 热重载

### 4.6 检查规则汇总统计

| 类别 | 规则数量 | 严重级别分布 |
|------|----------|-------------|
| 资产负债表 (YAML) | 5 | 4 ERROR + 1 WARNING |
| 利润表 (YAML) | 5 | 2 ERROR + 2 WARNING + 1 INFO |
| 现金流量表 (YAML) | 5 | 5 ERROR |
| 增值税申报表 (YAML) | 5 | 2 ERROR + 2 WARNING + 1 INFO |
| 企业所得税申报表 (YAML) | 6 | 3 ERROR + 2 WARNING + 1 INFO |
| 表间交叉校验 (YAML) | 5 | 3 WARNING + 2 INFO |
| **YAML 规则小计** | **31** | **16 ERROR + 10 WARNING + 5 INFO** |
| 运行时检查 (data_quality.py) | 7 种表 × 多条规则 | 见 4.2 节各表详情 |
| 导入后校验 (import_validator.py) | 18 条 | 见 4.4 节详情 |

---

## 五、数据库表结构

### 5.1 核心数据表

| 表名 | 用途 | 期间粒度 |
|------|------|----------|
| `companies` | 企业基本信息 | — |
| `balance_sheets` | 资产负债表 | 月度 |
| `income_statements` | 利润表 | 月度 |
| `cash_flow_statements` | 现金流量表 | 月度 |
| `account_balances` | 科目余额表 | 月度 |
| `tax_returns_vat` | 增值税申报表 | 月度 |
| `tax_returns_income` | 企业所得税申报表 | 季度/年度 |
| `tax_returns_stamp` | 印花税申报表 | 季度 |
| `tax_return_stamp_items` | 印花税明细项 | — |
| `invoices` | 发票数据 | — |
| `financial_metrics` | 财务指标汇总 | 月度 |

### 5.2 ETL v2 版本表

ETL 管道使用升级版表结构，支持期末/年初双列和本期/累计双列：

| 表名 | 说明 |
|------|------|
| `balance_sheets_v2` | 资产负债表（含 `_ending` / `_beginning` 后缀字段） |
| `income_statements_v2` | 利润表（含 `_current` / `_ytd` 后缀字段） |
| `cash_flow_statements_v3` | 现金流量表（含 `_current` / `_ytd` 后缀字段） |

---

## 六、数据流转图

```
用户操作                    前端组件                      后端API                        数据库
─────────────────────────────────────────────────────────────────────────────────────────────
[选择企业/Tab] ──→ DataManagement ──→ GET /stats ──→ data_management.py ──→ financial.db
                                                        ├── 查询 companies
                                                        ├── 统计 7 张表记录数
                                                        ├── 统计 financial_metrics 期间数
                                                        └── 返回 summary + companies + checks

[点击"开始检测"] ──→ handleRunCheck() ──→ POST /quality-check ──→ DataQualityChecker
                                                                    ├── get_available_periods()
                                                                    ├── check_subject_balance()
                                                                    ├── check_balance_sheet()
                                                                    ├── check_income_statement()
                                                                    ├── check_cash_flow()
                                                                    ├── check_vat_return()
                                                                    ├── check_cit_return()
                                                                    └── check_stamp_duty()

[切换到数据浏览] ──→ DataBrowser ──→ GET /companies ──→ data_browser.py ──→ companies
                                  ──→ GET /tables ──→ SUPPORTED_TABLES 配置
                                  ──→ GET /periods ──→ 动态查询期间
                                  ──→ GET /data ──→ 查询数据 + 字段映射
                                                      └── get_column_mapping() 中英文映射

[切换原表格式] ──→ RawView 组件 ──→ 使用 tableData.data[0] 渲染官方表格样式
```

---

## 七、验证方式

1. 启动后端：`python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload`
2. 启动前端：`cd frontend && npm run dev`
3. 登录系统，导航到"数据管理"菜单
4. 验证单户企业 Tab：查看仪表盘数据、点击"开始检测"查看质量检查结果
5. 验证多户企业 Tab：查看企业列表、搜索过滤功能
6. 验证数据浏览 Tab：切换企业/表/期间、切换通表/原表格式
