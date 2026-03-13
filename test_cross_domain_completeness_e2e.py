"""端到端测试：验证跨域查询完整性修复"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mvp_pipeline import run_pipeline
from config.settings import DB_PATH


def test_query_1():
    """测试查询1: 季度跨域查询"""
    print("=" * 80)
    print("测试查询1: TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率")
    print("=" * 80)

    query = "TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率"

    result = run_pipeline(query, db_path=str(DB_PATH))

    print(f"\n执行结果:")
    print(f"  成功: {result.get('success')}")
    print(f"  概念管线: {result.get('concept_pipeline', False)}")
    print(f"  结果行数: {len(result.get('results', []))}")

    if result.get('results'):
        print(f"\n返回的指标:")
        first_row = result['results'][0]
        metrics = [k for k in first_row.keys() if k not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter')]
        print(f"  {metrics}")

        expected_metrics = ['应纳税所得额', '企业所得税纳税额', '利润总额', '所得税税负率']
        missing = [m for m in expected_metrics if not any(m in ret or ret in m for ret in metrics)]

        if missing:
            print(f"\n✗ 测试失败: 缺失指标 {missing}")
            return False
        else:
            print(f"\n✓ 测试通过: 所有4个指标都返回了")
            return True
    else:
        print(f"\n✗ 测试失败: 无结果")
        return False


def test_query_2():
    """测试查询2: 年度跨域查询"""
    print("\n" + "=" * 80)
    print("测试查询2: TSE科技2025年增值税纳税额、企业所得税纳税额、利润总额、所得税税负率、增值税税负率")
    print("=" * 80)

    query = "TSE科技2025年增值税纳税额、企业所得税纳税额、利润总额、所得税税负率、增值税税负率"

    result = run_pipeline(query, db_path=str(DB_PATH))

    print(f"\n执行结果:")
    print(f"  成功: {result.get('success')}")
    print(f"  概念管线: {result.get('concept_pipeline', False)}")
    print(f"  结果行数: {len(result.get('results', []))}")

    if result.get('results'):
        print(f"\n返回的指标:")
        first_row = result['results'][0]
        metrics = [k for k in first_row.keys() if k not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter')]
        print(f"  {metrics}")

        expected_metrics = ['增值税纳税额', '企业所得税纳税额', '利润总额', '所得税税负率', '增值税税负率']
        missing = [m for m in expected_metrics if not any(m in ret or ret in m for ret in metrics)]

        if missing:
            print(f"\n✗ 测试失败: 缺失指标 {missing}")
            return False
        else:
            print(f"\n✓ 测试通过: 所有5个指标都返回了")
            return True
    else:
        print(f"\n✗ 测试失败: 无结果")
        return False


def test_fallback_to_llm():
    """测试回退到LLM管线"""
    print("\n" + "=" * 80)
    print("测试查询3: 包含未注册指标的查询（应回退到LLM管线）")
    print("=" * 80)

    query = "TSE科技2025年应纳税所得额、未注册指标X、利润总额"

    result = run_pipeline(query, db_path=str(DB_PATH))

    print(f"\n执行结果:")
    print(f"  成功: {result.get('success')}")
    print(f"  概念管线: {result.get('concept_pipeline', False)}")

    # 应该回退到LLM管线，concept_pipeline应该为False或不存在
    if not result.get('concept_pipeline'):
        print(f"\n✓ 测试通过: 正确回退到LLM管线")
        return True
    else:
        print(f"\n✗ 测试失败: 应该回退到LLM管线但没有")
        return False


if __name__ == '__main__':
    results = []

    try:
        results.append(('查询1 (季度跨域)', test_query_1()))
    except Exception as e:
        print(f"\n✗ 查询1异常: {e}")
        results.append(('查询1 (季度跨域)', False))

    try:
        results.append(('查询2 (年度跨域)', test_query_2()))
    except Exception as e:
        print(f"\n✗ 查询2异常: {e}")
        results.append(('查询2 (年度跨域)', False))

    try:
        results.append(('查询3 (回退测试)', test_fallback_to_llm()))
    except Exception as e:
        print(f"\n✗ 查询3异常: {e}")
        results.append(('查询3 (回退测试)', False))

    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)
    print(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 部分失败'}")
