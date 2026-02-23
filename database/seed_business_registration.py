"""为 company_business_registration 表插入示例数据

对应两个现有纳税人：华兴科技有限公司、鑫源贸易商行
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def seed_business_registration():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM company_business_registration")

    records = [
        {
            "company_name": "华兴科技有限公司",
            "english_name": "Huaxing Technology Co., Ltd.",
            "unified_social_credit_code": "91310000MA1FL8XQ30",
            "company_type": "有限责任公司(自然人投资或控股)",
            "operation_status": "存续",
            "established_date": "2018-03-22",
            "approval_date": "2023-06-15",
            "legal_representative": "陈浩",
            "registered_capital": "5000万人民币",
            "paid_in_capital": "3000万人民币",
            "insured_count": 171,
            "company_scale": "中型企业",
            "business_scope": "软件开发；信息技术咨询服务；计算机系统集成；数据处理和存储支持服务；人工智能应用软件开发",
            "registered_address": "上海市浦东新区张江高科技园区碧波路690号5幢301室",
            "business_term": "2018-03-22 至 无固定期限",
            "source": "国家企业信用信息公示系统",
            "taxpayer_id": "91310000MA1FL8XQ30",
            "industry_commerce_reg_no": "310000000XXXXXX",
            "organization_code": "MA1FL8XQ-3",
            "contact_phone": "021-5080-XXXX",
            "email": "info@huaxingtech.com",
            "taxpayer_qualification": "一般纳税人",
            "former_name": None,
            "province": "上海市",
            "city": "浦东新区",
            "district": "张江镇",
            "website": "www.huaxingtech.com",
            "industry": "软件和信息技术服务业",
            "industry_level1": "信息传输、软件和信息技术服务业",
            "industry_level2": "软件和信息技术服务业",
            "industry_level3": "应用软件开发",
            "registration_authority": "上海市浦东新区市场监督管理局",
            "longitude": 121.5907,
            "latitude": 31.2045,
            "extra": None,
        },
        {
            "company_name": "鑫源贸易商行",
            "english_name": None,
            "unified_social_credit_code": "92440300MA5EQXL17P",
            "company_type": "个体工商户",
            "operation_status": "存续",
            "established_date": "2020-08-10",
            "approval_date": "2024-01-20",
            "legal_representative": "李明",
            "registered_capital": "50万人民币",
            "paid_in_capital": "50万人民币",
            "insured_count": 8,
            "company_scale": "小微企业",
            "business_scope": "日用百货、办公用品、电子产品批发零售；货物进出口",
            "registered_address": "深圳市南山区科技园南区高新南一道008号",
            "business_term": "2020-08-10 至 无固定期限",
            "source": "国家企业信用信息公示系统",
            "taxpayer_id": "92440300MA5EQXL17P",
            "industry_commerce_reg_no": "440300XXXXXXXX",
            "organization_code": "MA5EQXL1-7",
            "contact_phone": "0755-8600-XXXX",
            "email": "xinyuan@trade.com",
            "taxpayer_qualification": "小规模纳税人",
            "former_name": None,
            "province": "广东省",
            "city": "深圳市",
            "district": "南山区",
            "website": None,
            "industry": "批发和零售业",
            "industry_level1": "批发和零售业",
            "industry_level2": "批发业",
            "industry_level3": "综合零售",
            "registration_authority": "深圳市南山区市场监督管理局",
            "longitude": 113.9436,
            "latitude": 22.5329,
            "extra": None,
        },
    ]

    cols = list(records[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    sql = f"INSERT INTO company_business_registration ({col_names}) VALUES ({placeholders})"

    for rec in records:
        cursor.execute(sql, [rec[c] for c in cols])

    conn.commit()
    print(f"Inserted {len(records)} records into company_business_registration")

    # 验证
    cursor.execute("SELECT company_name, taxpayer_id, company_type FROM company_business_registration")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]}")

    conn.close()


if __name__ == "__main__":
    seed_business_registration()
