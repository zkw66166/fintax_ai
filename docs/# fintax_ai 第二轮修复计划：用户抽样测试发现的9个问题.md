# fintax_ai 第二轮修复计划：用户抽样测试发现的9个问题

## Context

P0-P3 改造已完成（相对日期、跨域引擎、计算指标、季度路由、多年/枚举月份、子科目同义词），43个单元测试全部通过，原有5个测试也通过。但用户抽样测试发现9个实际运行问题，需要逐一修复。

---

## 问题清单与修复方案

### Fix 1: "账上"关键词未识别为 account_balance 域

**问题**: 用户输入含"账上"/"账面"时，未路由到科目余额表域。
**根因**: `_ACCOUNT_BALANCE_KEYWORDS_HIGH` 和 `_ACCOUNT_BALANCE_KEYWORDS_MED` 缺少"账上"/"账面"/"账"等常用词。
**文件**: `modules/entity_preprocessor.py:10-17`

**改动**:
- `_ACCOUNT_BALANCE_KEYWORDS_MED` 增加: `'账上'`, `'账面'`
- 在共有项目消歧逻辑 (line ~408) 的 `has_ab_signal` 中增加 `'账上'`, `'账面'`

---

### Fix 2: 跨域子查询 SQL 生成不精准导致 0 行结果

**问题**: 跨域管线 `_run_cross_domain_pipeline` 调用 `generate_sql()` 时，子域 intent 缺少具体的 metrics 信息，LLM 生成的 SQL 可能查错列或加错过滤条件，导致返回 0 行。
**根因**: `sub_intent = dict(intent)` 浅拷贝了完整 intent（含所有域的信息），但 `sub_intent['domain']` 改为子域后，`select.metrics` 仍是原始跨域 intent 的 metrics（可能包含其他域的列名），LLM 困惑。
**文件**: `mvp_pipeline.py:326-384`

**改动**:
1. 在 `_run_cross_domain_pipeline` 中，为每个子域构建干净的 sub_intent：
   - 只保留该子域相关的 scope（如 `profit_scope`）
   - 从原始 intent 的 `select.metrics` 中过滤出属于该子域的指标（通过 schema_catalog 的列白名单匹配）
   - 设置 `sub_intent['filters']` 保留期间过滤
2. 增加审核失败后的重试逻辑（与主管线一致，已有但需确认 feedback 传递正确）
3. 子域 SQL 执行失败时记录详细错误而非静默跳过

---

### Fix 3: 计算指标管线 `_run_metric_pipeline` 的 "total_assets is not defined" 错误

**问题**: `compute_metric()` 的 `eval()` 抛出 `NameError`，因为 `source_data` 中缺少所需变量。
**根因**: 两层问题：
  1. `_run_metric_pipeline` 调用 `generate_sql()` 生成通用 SQL，LLM 不知道需要 SELECT 哪个具体列（如 `assets_end`），生成的 SQL 可能不包含该列
  2. `compute_metric()` 的 `except` 只捕获 `ZeroDivisionError, TypeError`，未捕获 `NameError`
**文件**: `mvp_pipeline.py:387-469`, `modules/metric_calculator.py:189-194`

**改动**:
1. **重构 `_run_metric_pipeline`**: 不再依赖 LLM 生成 SQL，改为直接构建确定性 SQL
   - 从 `METRIC_FORMULAS[metric].sources` 获取每个变量需要的 `domain` + `column`
   - 根据 domain 确定 view（通过 `get_scope_view()`）
   - 直接构建 `SELECT column FROM view WHERE taxpayer_id=:taxpayer_id AND period_year=:year AND period_month=:month`
   - 对于 expression 类型（如 `(equity_begin + equity_end) / 2.0`），SELECT 所有 `columns` 列表中的列
   - 跳过 LLM 调用和 SQL 审核（因为 SQL 是代码生成的，已知安全）
2. **`compute_metric()`**: `except` 增加 `NameError, KeyError`
3. 当 source_data 中某变量为 None 时，提前返回友好错误信息而非 eval 失败

---

### Fix 4: 中文引号干扰域检测（"利润总额" 导致全部6个域被检测到）

**问题**: 用户输入含中文引号 `"..."` 或 `"..."` 包裹的术语时，引号字符可能导致关键词匹配异常，触发多个域的关键词同时命中。
**根因**: 域检测使用 `kw in user_query` 做子串匹配，中文引号 `"\u201c"` / `"\u201d"` 不影响子串匹配本身。实际问题可能是：当用户输入 `"利润总额"` 时，"利润总额"同时命中了 `_PROFIT_EIT_SHARED_ITEMS`（利润总额）和其他域的关键词。需要进一步排查。
**文件**: `modules/entity_preprocessor.py`

**改动**:
1. 在 `detect_entities()` 入口处，对 `user_query` 做引号标准化：将中文引号 `""''「」` 统一去除或替换为空格
2. 确保跨域升级逻辑 (0i 段) 不会因为共有项目（如"利润总额"属于 profit 和 EIT 共有）而错误触发跨域检测 — 当前逻辑已经只检查域独有关键词，但需要验证 EIT_KEYWORDS 中的"所得税"是否被"所得税费用"（利润表项目）误触发
3. 在 `_EIT_KEYWORDS` 中，将"所得税"改为更精确的匹配：排除"所得税费用"（利润表项目）的情况

---

### Fix 5: 跨域查询中 account_balance 子域缺少 "账上" 信号

**问题**: 与 Fix 1 相关。当用户说"账上XXX"时，如果同时提到其他域的关键词，account_balance 可能不在 `cross_domain_list` 中。
**文件**: `modules/entity_preprocessor.py:486-525`

**改动**:
- 在跨域检测 (0i 段) 中，`account_balance` 的独有关键词检查增加 `'账上'`, `'账面'`
- 同时在 `_ACCOUNT_BALANCE_KEYWORDS_HIGH` 中增加这些词（与 Fix 1 合并）

---

### Fix 6: 复杂多域查询返回 0 行

**问题**: 与 Fix 2 相同根因。跨域管线的子域 SQL 生成质量不够。
**改动**: 同 Fix 2 方案。

---

### Fix 7: 计算指标查询触发不必要的澄清

**问题**: 当用户查询"去年底资产负债率"时，`_resolve_relative_dates` 将"去年底"转为"2025年12月"，但 intent parser 可能因为缺少明确的月份信号而触发 `need_clarification`。
**根因**: 计算指标管线在 intent 解析后才检测指标，但 intent parser 可能已经返回 `need_clarification=True`，导致管线在 Step 3 就返回了，根本没走到 Step 3b 的指标检测。
**文件**: `mvp_pipeline.py:160-186`

**改动**:
1. 将计算指标检测 (`detect_computed_metrics`) 提前到 intent 解析之前（或与 intent 解析并行）
2. 如果检测到计算指标，跳过 intent 的 `need_clarification` 检查，直接进入指标管线
3. 具体实现：在 Step 1 实体预处理后立即调用 `detect_computed_metrics(resolved_query)`，如果命中，设置 `entities['has_computed_metric'] = True`，然后在 Step 3 的澄清检查中，如果 `has_computed_metric` 为 True，忽略澄清请求

---

### Fix 8: 补全 46 题端到端测试

**问题**: 当前 `test_real_scenarios.py` 只有单元测试（日期解析、域检测、指标检测、操作检测），缺少端到端管线测试。
**文件**: `test_real_scenarios.py`

**改动**:
1. 新增 `TestEndToEnd` 测试类，对 46 个问题逐一调用 `run_pipeline()`
2. 每题验证：
   - `result['success'] == True`（不报错）
   - `result['clarification'] is None`（不触发澄清）
   - `result['entities']['domain_hint']` 符合预期域
   - `len(result['results']) > 0`（有返回数据）
3. 跨域题额外验证 `result['cross_domain_summary']` 非空
4. 计算指标题验证 `result['metric_results']` 非空且 value 非 None
5. 注意：端到端测试需要数据库有对应数据，使用 sample_data 中的华兴科技数据

---

### Fix 9: 前端查询历史

**问题**: 当前 Gradio 前端无查询历史，每次查询后无法回看之前的结果。
**文件**: `app.py`

**改动**:
1. 增加 `gr.State()` 存储查询历史列表 `[{query, result, timestamp}]`
2. 每次查询后将结果追加到历史列表（最新在前）
3. 在界面左侧或底部增加"查询历史"区域，显示历史查询列表
4. 点击历史条目可回填查询并显示缓存结果（不重新执行管线）
5. 历史条目显示：查询文本 + 成功/失败状态 + 时间戳

---

## ASBE/ASSE → EAS/SAS 术语统一（延后）

**评估**: 全代码库约 461 处引用，涉及 DB schema（CHECK 约束）、seed data、sample data、所有 prompt 文件、所有 Python 模块。改动量大且风险高（需要重建数据库），收益仅为命名一致性。

**决定**: 延后处理。当前 ASBE/ASSE 作为内部标识符可正常工作，不影响功能。如需执行，建议作为独立 PR，配合完整回归测试。

---

## 执行顺序

| 步骤 | 修复项 | 涉及文件 |
|------|-------|---------|
| 1 | Fix 1 + Fix 5: "账上"关键词 | `entity_preprocessor.py` |
| 2 | Fix 4: 引号标准化 + EIT关键词精确化 | `entity_preprocessor.py` |
| 3 | Fix 3: 指标管线重构（确定性SQL） | `mvp_pipeline.py`, `metric_calculator.py` |
| 4 | Fix 7: 指标检测提前，跳过澄清 | `mvp_pipeline.py` |
| 5 | Fix 2 + Fix 6: 跨域子查询精准化 | `mvp_pipeline.py` |
| 6 | Fix 9: 前端查询历史 | `app.py` |
| 7 | Fix 8: 46题端到端测试 | `test_real_scenarios.py` |

---

## 验证

1. 每步完成后运行 `python test_real_scenarios.py` 确保单元测试不退化
2. 步骤 7 完成后运行端到端测试，目标：单域 18 题全部通过，跨域题尽可能多通过
3. 手动抽样验证用户反馈的具体问题（"账上应交增值税"、"资产负债率"、"利润总额"等）
