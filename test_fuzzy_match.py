"""测试模糊匹配函数"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mvp_pipeline import _fuzzy_match_metric


test_cases = [
    ('实际缴纳的企业所得税额', '企业所得税纳税额', True),
    ('增值税应纳税额', '增值税纳税额', True),
    ('所得税税负率', '所得税税负率', True),
    ('利润总额', '利润总额', True),
    ('应纳税所得额', '应纳税所得额', True),
    ('未注册指标X', '利润总额', False),
]

print("=" * 80)
print("测试模糊匹配函数")
print("=" * 80)

for req, ret, expected in test_cases:
    result = _fuzzy_match_metric(req, ret)
    status = "✓" if result == expected else "✗"
    print(f"{status} '{req}' vs '{ret}': {result} (期望: {expected})")
