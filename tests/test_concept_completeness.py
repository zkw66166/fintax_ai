"""测试概念管线完整性验证功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mvp_pipeline import _extract_requested_metrics
from modules.concept_registry import resolve_concepts, CONCEPT_REGISTRY


def test_metric_extraction():
    """测试指标提取功能"""
    print("=" * 60)
    print("测试1: 指标提取功能")
    print("=" * 60)

    test_cases = [
        {
            'query': 'TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率',
            'entities': {'taxpayer_name': 'TSE科技', 'period_year': 2025, 'period_quarter': 4},
            'expected': ['应纳税所得额', '实际缴纳的企业所得税额', '利润总额', '所得税税负率']
        },
        {
            'query': 'TSE科技2025年增值税纳税额、企业所得税纳税额、利润总额、所得税税负率、增值税税负率',
            'entities': {'taxpayer_name': 'TSE科技', 'period_year': 2025},
            'expected': ['增值税纳税额', '企业所得税纳税额', '利润总额', '所得税税负率', '增值税税负率']
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  查询: {tc['query']}")
        metrics = _extract_requested_metrics(tc['query'], tc['entities'])
        print(f"  提取指标: {metrics}")
        print(f"  期望指标: {tc['expected']}")
        print(f"  结果: {'✓ 通过' if set(metrics) == set(tc['expected']) else '✗ 失败'}")


def test_concept_resolution():
    """测试概念解析功能"""
    print("\n" + "=" * 60)
    print("测试2: 概念解析功能")
    print("=" * 60)

    test_cases = [
        {
            'query': '应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率',
            'entities': {'period_year': 2025, 'period_quarter': 4},
            'expected_count': 4,
            'expected_names': ['应纳税所得额', '企业所得税纳税额', '利润总额', '所得税税负率']
        },
        {
            'query': '增值税纳税额、企业所得税纳税额、利润总额、所得税税负率、增值税税负率',
            'entities': {'period_year': 2025},
            'expected_count': 5,
            'expected_names': ['增值税纳税额', '企业所得税纳税额', '利润总额', '所得税税负率', '增值税税负率']
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  查询: {tc['query']}")
        concepts = resolve_concepts(tc['query'], tc['entities'])
        concept_names = [c['name'] for c in concepts]
        print(f"  解析概念: {concept_names}")
        print(f"  期望概念: {tc['expected_names']}")
        print(f"  概念数量: {len(concepts)} (期望: {tc['expected_count']})")
        print(f"  结果: {'✓ 通过' if len(concepts) == tc['expected_count'] else '✗ 失败'}")


def test_new_concepts():
    """测试新增概念是否正确注册"""
    print("\n" + "=" * 60)
    print("测试3: 新增概念注册")
    print("=" * 60)

    new_concepts = [
        '所得税税负率',
        '增值税税负率',
        '增值税纳税额',
        '企业所得税纳税额',
    ]

    for concept_name in new_concepts:
        if concept_name in CONCEPT_REGISTRY:
            cdef = CONCEPT_REGISTRY[concept_name]
            print(f"\n✓ {concept_name}:")
            print(f"  域: {cdef.get('domain')}")
            print(f"  视图: {cdef.get('view')}")
            print(f"  列: {cdef.get('column')}")
            print(f"  别名: {cdef.get('aliases', [])}")
        else:
            print(f"\n✗ {concept_name}: 未找到")


def test_alias_matching():
    """测试别名匹配功能"""
    print("\n" + "=" * 60)
    print("测试4: 别名匹配功能")
    print("=" * 60)

    test_aliases = [
        ('实际缴纳的企业所得税额', '企业所得税纳税额'),
        ('增值税应纳税额', '增值税纳税额'),
        ('EIT税负率', '所得税税负率'),
        ('VAT税负率', '增值税税负率'),
    ]

    for alias, expected_concept in test_aliases:
        query = f"2025年{alias}"
        entities = {'period_year': 2025}
        concepts = resolve_concepts(query, entities)
        if concepts:
            matched_name = concepts[0]['name']
            result = '✓ 通过' if matched_name == expected_concept else f'✗ 失败 (匹配到: {matched_name})'
        else:
            result = '✗ 失败 (未匹配)'
        print(f"  {alias} → {expected_concept}: {result}")


if __name__ == '__main__':
    test_metric_extraction()
    test_concept_resolution()
    test_new_concepts()
    test_alias_matching()
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
