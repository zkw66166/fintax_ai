"""简化测试：验证概念管线完整性检查逻辑"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mvp_pipeline import _extract_requested_metrics, _fuzzy_match_metric


def test_completeness_check():
    """测试完整性检查逻辑"""
    print("=" * 80)
    print("测试: 完整性检查逻辑")
    print("=" * 80)

    # 模拟概念管线返回的结果
    concept_result = {
        'success': True,
        'results': [
            {
                'period': '2025Q4',
                '应纳税所得额': 1000000,
                '利润总额': 1200000,
            }
        ]
    }

    # 提取请求的指标
    query = "TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率"
    entities = {'taxpayer_name': 'TSE科技', 'period_year': 2025, 'period_quarter': 4}
    requested_metrics = _extract_requested_metrics(query, entities)

    print(f"\n请求的指标: {requested_metrics}")

    # 提取返回的指标
    returned_metrics = set()
    for r in concept_result.get('results', []):
        for key in r.keys():
            if key not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter'):
                returned_metrics.add(key)

    print(f"返回的指标: {list(returned_metrics)}")

    # 检查缺失的指标
    missing = []
    for req in requested_metrics:
        if not any(_fuzzy_match_metric(req, ret) for ret in returned_metrics):
            missing.append(req)

    print(f"缺失的指标: {missing}")

    if missing:
        print(f"\n✓ 完整性检查正确: 检测到缺失指标，应回退到LLM管线")
        return True
    else:
        print(f"\n✗ 完整性检查失败: 未检测到缺失指标")
        return False


def test_completeness_check_complete():
    """测试完整性检查逻辑（完整情况）"""
    print("\n" + "=" * 80)
    print("测试: 完整性检查逻辑（完整情况）")
    print("=" * 80)

    # 模拟概念管线返回的完整结果
    concept_result = {
        'success': True,
        'results': [
            {
                'period': '2025Q4',
                '应纳税所得额': 1000000,
                '企业所得税纳税额': 250000,
                '利润总额': 1200000,
                '所得税税负率': 20.83,
            }
        ]
    }

    # 提取请求的指标
    query = "TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率"
    entities = {'taxpayer_name': 'TSE科技', 'period_year': 2025, 'period_quarter': 4}
    requested_metrics = _extract_requested_metrics(query, entities)

    print(f"\n请求的指标: {requested_metrics}")

    # 提取返回的指标
    returned_metrics = set()
    for r in concept_result.get('results', []):
        for key in r.keys():
            if key not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter'):
                returned_metrics.add(key)

    print(f"返回的指标: {list(returned_metrics)}")

    # 检查缺失的指标（使用模糊匹配）
    missing = []
    for req in requested_metrics:
        if not any(_fuzzy_match_metric(req, ret) for ret in returned_metrics):
            missing.append(req)

    print(f"缺失的指标: {missing}")

    if not missing:
        print(f"\n✓ 完整性检查正确: 所有指标都返回了，可以直接返回结果")
        return True
    else:
        print(f"\n✗ 完整性检查失败: 错误地认为有缺失指标")
        return False


if __name__ == '__main__':
    results = []
    results.append(('不完整情况', test_completeness_check()))
    results.append(('完整情况', test_completeness_check_complete()))

    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)
    print(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 部分失败'}")
