"""测试场景：验证完整NL2SQL管线"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import DB_PATH
from database.init_db import init_database
from database.seed_data import seed_reference_data
from database.sample_data import insert_sample_data
from mvp_pipeline import run_pipeline


TEST_CASES = [
    {
        "id": "T1",
        "query": "查询华兴科技2025年1月的销项税额",
        "desc": "单字段查询（一般纳税人）",
        "expect_success": True,
        "expect_domain": "vat",
    },
    {
        "id": "T2",
        "query": "华兴科技2025年1月到3月的应纳税额趋势",
        "desc": "趋势查询（3个月）",
        "expect_success": True,
        "expect_domain": "vat",
    },
    {
        "id": "T3",
        "query": "查询鑫源贸易商行的3%征收率销售额",
        "desc": "缺期间 → 触发澄清",
        "expect_success": False,
        "expect_clarification": True,
    },
    {
        "id": "T4",
        "query": "鑫源贸易商行2025年2月的3%征收率销售额",
        "desc": "小规模纳税人查询",
        "expect_success": True,
        "expect_domain": "vat",
    },
    {
        "id": "T5",
        "query": "华兴科技2025年3月的进项税额和销项税额",
        "desc": "多字段查询 + 修订版本",
        "expect_success": True,
        "expect_domain": "vat",
    },
]


def setup_db():
    """确保测试数据库就绪"""
    db_path = str(DB_PATH)
    # 重建数据库
    p = Path(db_path)
    if p.exists():
        p.unlink()
    init_database(db_path)
    seed_reference_data(db_path)
    insert_sample_data(db_path)
    print("测试数据库已就绪\n")


def run_all_tests():
    """运行全部测试"""
    setup_db()

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"\n{'#'*60}")
        print(f"测试 {tc['id']}: {tc['desc']}")
        print(f"查询: {tc['query']}")
        print(f"{'#'*60}")

        result = run_pipeline(tc['query'])

        # 验证
        ok = True
        if tc.get('expect_clarification'):
            if not result.get('clarification'):
                print(f"  ✗ 预期触发澄清，但未触发")
                ok = False
            else:
                print(f"  ✓ 正确触发澄清: {result['clarification']}")
        elif tc.get('expect_success'):
            if not result['success']:
                print(f"  ✗ 预期成功，但失败: {result.get('error')}")
                ok = False
            else:
                print(f"  ✓ 查询成功，返回 {len(result['results'])} 行")
                if tc.get('expect_domain') and result.get('intent'):
                    actual_domain = result['intent'].get('domain')
                    if actual_domain != tc['expect_domain']:
                        print(f"  ✗ 域不匹配: 预期={tc['expect_domain']}, 实际={actual_domain}")
                        ok = False
                    else:
                        print(f"  ✓ 域正确: {actual_domain}")

        if ok:
            passed += 1
            print(f"  >>> 测试 {tc['id']} 通过")
        else:
            failed += 1
            print(f"  >>> 测试 {tc['id']} 失败")

    print(f"\n{'='*60}")
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {len(TEST_CASES)} 个")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
