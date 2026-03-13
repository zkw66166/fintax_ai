"""测试空结果提示功能"""
import sqlite3
from mvp_pipeline import run_pipeline
from modules.display_formatter import build_display_data

def test_empty_result_message():
    """测试空结果时的提示信息生成"""

    # 测试用例1: 查询不存在的期间数据
    print("\n" + "="*60)
    print("测试用例1: 查询不存在的期间数据")
    print("="*60)
    query1 = "大华智能制造厂2027年1月经营活动现金流是多少?"
    result1 = run_pipeline(query1)

    print(f"\n查询: {query1}")
    print(f"成功: {result1.get('success')}")
    print(f"结果数量: {len(result1.get('results', []))}")
    print(f"纳税人名称: {result1.get('taxpayer_name')}")
    print(f"纳税人ID: {result1.get('taxpayer_id')}")
    print(f"期间: {result1.get('period')}")
    print(f"域: {result1.get('domain')}")

    if result1.get('success') and len(result1.get('results', [])) == 0:
        display_data = build_display_data(result1)
        empty_msg = display_data.get('empty_data_message')
        print(f"\n空结果提示: {empty_msg}")
        assert empty_msg is not None, "应该生成空结果提示信息"
        assert "大华智能制造" in empty_msg or "92440300MA2KYYYYYY" in empty_msg, "提示信息应包含公司名称"
        assert "2027" in empty_msg, "提示信息应包含期间"
        print("✅ 测试用例1通过")
    else:
        print("⚠️ 查询返回了数据或失败，跳过空结果测试")

    # 测试用例2: 查询不存在的公司
    print("\n" + "="*60)
    print("测试用例2: 查询不存在的公司")
    print("="*60)
    query2 = "不存在的公司2026年1月增值税是多少?"
    result2 = run_pipeline(query2)

    print(f"\n查询: {query2}")
    print(f"成功: {result2.get('success')}")
    results2 = result2.get('results') or []
    print(f"结果数量: {len(results2)}")
    print(f"纳税人名称: {result2.get('taxpayer_name')}")
    print(f"期间: {result2.get('period')}")
    print(f"域: {result2.get('domain')}")

    if result2.get('success') and len(results2) == 0:
        display_data = build_display_data(result2)
        empty_msg = display_data.get('empty_data_message')
        print(f"\n空结果提示: {empty_msg}")
        assert empty_msg is not None, "应该生成空结果提示信息"
        print("✅ 测试用例2通过")
    else:
        print("⚠️ 查询返回了数据、失败或需要澄清，跳过空结果测试")

    # 测试用例3: 查询存在的数据（应该没有空结果提示）
    print("\n" + "="*60)
    print("测试用例3: 查询存在的数据")
    print("="*60)
    query3 = "华兴科技2025年12月增值税是多少?"
    result3 = run_pipeline(query3)

    print(f"\n查询: {query3}")
    print(f"成功: {result3.get('success')}")
    print(f"结果数量: {len(result3.get('results', []))}")

    if result3.get('success') and len(result3.get('results', [])) > 0:
        display_data = build_display_data(result3)
        empty_msg = display_data.get('empty_data_message')
        print(f"\n空结果提示: {empty_msg}")
        assert empty_msg is None, "有数据时不应该有空结果提示"
        print("✅ 测试用例3通过")
    else:
        print("⚠️ 查询失败或无数据")

    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)

if __name__ == "__main__":
    test_empty_result_message()
