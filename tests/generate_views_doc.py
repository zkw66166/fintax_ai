import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('d:/fintax_ai/database/fintax_ai.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'vw_%' ORDER BY name")
views = [r[0] for r in cursor.fetchall()]

md_content = f"""# 数据库视图结构文档

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据库**: fintax_ai.db
**视图数量**: {len(views)}

---

## 目录

"""

for i, v in enumerate(views, 1):
    md_content += f"{i}. [{v}](#{v})\n"

md_content += "\n---\n\n"

for view_name in views:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='view' AND name=?", (view_name,))
    result = cursor.fetchone()
    sql_def = result[0] if result else ""

    cursor.execute(f"PRAGMA table_info({view_name})")
    columns = cursor.fetchall()

    md_content += f"## {view_name}\n\n"
    md_content += f"**说明**: "
    
    if "vat_return_general" in view_name:
        md_content += "一般纳税人增值税申报表视图\n"
    elif "vat_return_small" in view_name:
        md_content += "小规模纳税人增值税申报表视图\n"
    elif "eit_annual" in view_name:
        md_content += "企业所得税年度申报表视图\n"
    elif "eit_quarter" in view_name:
        md_content += "企业所得税季度申报表视图\n"
    elif "financial_statement" in view_name:
        md_content += "财务报表视图\n"
    elif "account_balance" in view_name:
        md_content += "科目余额表视图\n"
    elif "inv_spec_purchase" in view_name:
        md_content += "进项发票明细视图\n"
    elif "inv_spec_sales" in view_name:
        md_content += "销项发票明细视图\n"
    elif "enterprise_profile" in view_name:
        md_content += "企业基本信息视图\n"
    elif "balance_sheet_eas" in view_name:
        md_content += "企业会计准则资产负债表视图\n"
    elif "balance_sheet_sas" in view_name:
        md_content += "小企业会计准则资产负债表视图\n"
    elif "profit_eas" in view_name:
        md_content += "企业会计准则利润表视图\n"
    elif "profit_sas" in view_name:
        md_content += "小企业会计准则利润表视图\n"
    elif "cash_flow_eas" in view_name:
        md_content += "企业会计准则现金流量表视图\n"
    elif "cash_flow_sas" in view_name:
        md_content += "小企业会计准则现金流量表视图\n"
    elif "financial_metrics" in view_name:
        md_content += "财务指标视图\n"
    else:
        md_content += "\n"
    
    md_content += f"\n**字段数量**: {len(columns)}\n\n"
    
    md_content += "### 字段列表\n\n"
    md_content += "| 序号 | 字段名 | 数据类型 | 非空 | 主键 | 默认值 |\n"
    md_content += "|------|--------|----------|------|------|--------|\n"
    
    for i, col in enumerate(columns, 1):
        name = col[1]
        col_type = col[2] if col[2] else "TEXT"
        not_null = "是" if col[3] else "否"
        pk = "是" if col[5] else "否"
        default = str(col[4]) if col[4] else "-"
        md_content += f"| {i} | {name} | {col_type} | {not_null} | {pk} | {default} |\n"
    
    md_content += "\n### SQL 定义\n\n"
    md_content += "```sql\n"
    md_content += sql_def + "\n"
    md_content += "```\n\n"
    md_content += "---\n\n"

conn.close()

with open('d:/fintax_ai/docs/database_views.md', 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Done! Created database_views.md with {len(views)} views")
