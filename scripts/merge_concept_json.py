"""
合并概念JSON文件脚本

将细分后的JSON文件合并为统一的7个文件：
- balance_sheet_eas.json + balance_sheet_sas.json → balance_sheet.json
- profit_eas.json + profit_sas.json → profit.json
- cash_flow_eas.json + cash_flow_sas.json → cash_flow.json
- vat_general.json + vat_small.json → vat.json
- 保留: eit.json, invoice.json, financial_metrics.json
"""
import json
from pathlib import Path
from collections import defaultdict

def merge_json_files():
    """合并JSON文件"""
    config_dir = Path('config/concepts')

    # 定义合并规则
    merge_rules = [
        {
            'files': ['balance_sheet_eas.json', 'balance_sheet_sas.json'],
            'output': 'balance_sheet.json',
            'suffix_to_remove': ['_EAS', '_SAS']
        },
        {
            'files': ['profit_eas.json', 'profit_sas.json'],
            'output': 'profit.json',
            'suffix_to_remove': ['_EAS', '_SAS']
        },
        {
            'files': ['cash_flow_eas.json', 'cash_flow_sas.json'],
            'output': 'cash_flow.json',
            'suffix_to_remove': ['_EAS', '_SAS']
        },
        {
            'files': ['vat_general.json', 'vat_small.json'],
            'output': 'vat.json',
            'suffix_to_remove': ['_一般', '_小规模']
        }
    ]

    for rule in merge_rules:
        print(f"\n合并 {rule['files']} → {rule['output']}")
        merged_concepts = {}

        for json_file in rule['files']:
            file_path = config_dir / json_file
            if not file_path.exists():
                print(f"  警告: {json_file} 不存在，跳过")
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                concepts = json.load(f)

            print(f"  读取 {json_file}: {len(concepts)} 个概念")

            # 处理每个概念
            for name, defn in concepts.items():
                # 移除后缀
                clean_name = name
                for suffix in rule['suffix_to_remove']:
                    if name.endswith(suffix):
                        clean_name = name[:-len(suffix)]
                        break

                # 如果概念已存在，合并aliases
                if clean_name in merged_concepts:
                    existing_aliases = set(merged_concepts[clean_name].get('aliases', []))
                    new_aliases = set(defn.get('aliases', []))
                    merged_aliases = sorted(existing_aliases | new_aliases)
                    merged_concepts[clean_name]['aliases'] = merged_aliases
                    print(f"    合并别名: {clean_name} ({len(merged_aliases)} 个别名)")
                else:
                    # 新概念，复制定义
                    merged_defn = defn.copy()

                    # 移除不需要的字段
                    merged_defn.pop('accounting_standard', None)
                    merged_defn.pop('taxpayer_type', None)

                    merged_concepts[clean_name] = merged_defn

        # 写入合并后的文件
        output_path = config_dir / rule['output']
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_concepts, f, ensure_ascii=False, indent=2)

        print(f"  ✓ 写入 {rule['output']}: {len(merged_concepts)} 个概念")

    print("\n合并完成！")
    print("\n统计:")
    for rule in merge_rules:
        output_path = config_dir / rule['output']
        if output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                concepts = json.load(f)
            print(f"  {rule['output']}: {len(concepts)} 个概念")

if __name__ == '__main__':
    merge_json_files()
