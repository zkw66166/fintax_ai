"""将concept_registry.py中的245个概念��出为JSON配置文件（混合方案）。

混合方案规则：
- 财务报表域（balance_sheet/profit/cash_flow）：按会计准则细分为 EAS/SAS 两套
- VAT域：按纳税人类型细分为 一般/小规模 两套
- 其他域（EIT/invoice/financial_metrics）：不细分，直接导出

输出目录：config/concepts/
"""
import json
import copy
import sys
from pathlib import Path

# 确保项目根目录在path中
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.concept_registry import CONCEPT_REGISTRY
from modules.schema_catalog import VIEW_COLUMNS


def get_sas_view_name(eas_view: str) -> str:
    """将EAS视图名转换为SAS视图名"""
    return eas_view.replace('_eas', '_sas')


def get_sas_column(column: str, sas_view: str) -> str | None:
    """检查SAS视图是否有对应列，返回列名或None"""
    sas_cols = VIEW_COLUMNS.get(sas_view, [])
    if column in sas_cols:
        return column
    return None


def export_financial_statement_domain(domain: str, concepts: list, output_dir: Path):
    """导出财务报表域概念（按会计准则细分）"""
    eas_concepts = {}
    sas_concepts = {}

    for name, defn in concepts:
        eas_view = defn.get('view', '')
        sas_view = get_sas_view_name(eas_view)

        # EAS版本：保持原样
        eas_defn = copy.deepcopy(defn)
        eas_defn['accounting_standard'] = '企业会计准则'
        eas_concepts[name] = eas_defn

        # SAS版本：检查列是否存在
        column = defn.get('column', '')
        concept_type = defn.get('type', '')

        if concept_type == 'computed':
            # 计算型概念：检查所有source列
            sources = defn.get('sources', {})
            all_cols_exist = True
            for src_key, src_val in sources.items():
                src_col = src_val.get('column', '')
                if src_col and not get_sas_column(src_col, sas_view):
                    all_cols_exist = False
                    break

            if all_cols_exist:
                sas_defn = copy.deepcopy(defn)
                sas_defn['view'] = sas_view
                sas_defn['accounting_standard'] = '小企业会计准则'
                sas_concepts[name] = sas_defn
        else:
            # 直接取值型概念：检查列是否存在
            if column and get_sas_column(column, sas_view):
                sas_defn = copy.deepcopy(defn)
                sas_defn['view'] = sas_view
                sas_defn['accounting_standard'] = '小企业会计准则'
                sas_concepts[name] = sas_defn

    # 写入文件
    eas_file = output_dir / f'{domain}_eas.json'
    sas_file = output_dir / f'{domain}_sas.json'

    with open(eas_file, 'w', encoding='utf-8') as f:
        json.dump(eas_concepts, f, ensure_ascii=False, indent=2)
    print(f"  EAS: {len(eas_concepts)} concepts -> {eas_file.name}")

    with open(sas_file, 'w', encoding='utf-8') as f:
        json.dump(sas_concepts, f, ensure_ascii=False, indent=2)
    print(f"  SAS: {len(sas_concepts)} concepts -> {sas_file.name}")

    return len(eas_concepts), len(sas_concepts)


def export_vat_domain(concepts: list, output_dir: Path):
    """导出VAT域概念（按纳税人类型细分）"""
    general_concepts = {}
    small_concepts = {}

    for name, defn in concepts:
        gen_view = 'vw_vat_return_general'
        small_view = 'vw_vat_return_small'
        column = defn.get('column', '')

        # 一般纳税人版本
        gen_cols = VIEW_COLUMNS.get(gen_view, [])
        if column in gen_cols:
            gen_defn = copy.deepcopy(defn)
            gen_defn['view'] = gen_view
            gen_defn['taxpayer_type'] = '一般纳税人'
            general_concepts[name] = gen_defn

        # 小规模纳税人版本
        small_cols = VIEW_COLUMNS.get(small_view, [])
        if column in small_cols:
            small_defn = copy.deepcopy(defn)
            small_defn['view'] = small_view
            small_defn['taxpayer_type'] = '小规模纳税人'
            small_concepts[name] = small_defn

    # 写入文件
    gen_file = output_dir / 'vat_general.json'
    small_file = output_dir / 'vat_small.json'

    with open(gen_file, 'w', encoding='utf-8') as f:
        json.dump(general_concepts, f, ensure_ascii=False, indent=2)
    print(f"  General: {len(general_concepts)} concepts -> {gen_file.name}")

    with open(small_file, 'w', encoding='utf-8') as f:
        json.dump(small_concepts, f, ensure_ascii=False, indent=2)
    print(f"  Small: {len(small_concepts)} concepts -> {small_file.name}")

    return len(general_concepts), len(small_concepts)


def export_simple_domain(domain: str, concepts: list, output_dir: Path):
    """导出不细分的域概念"""
    concept_dict = {}
    for name, defn in concepts:
        concept_dict[name] = copy.deepcopy(defn)

    output_file = output_dir / f'{domain}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(concept_dict, f, ensure_ascii=False, indent=2)
    print(f"  {len(concept_dict)} concepts -> {output_file.name}")

    return len(concept_dict)


def main():
    output_dir = Path('config/concepts')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按域分组
    domains = {}
    for name, defn in CONCEPT_REGISTRY.items():
        domain = defn.get('domain', 'unknown')
        domains.setdefault(domain, []).append((name, defn))

    total = 0

    # 财务报表域：按会计准则细分
    for fs_domain in ['balance_sheet', 'profit', 'cash_flow']:
        if fs_domain not in domains:
            continue
        print(f"\n[{fs_domain}] 按会计准则细分:")
        eas_count, sas_count = export_financial_statement_domain(
            fs_domain, domains[fs_domain], output_dir
        )
        total += eas_count + sas_count

    # VAT域：按纳税人类型细分
    if 'vat' in domains:
        print(f"\n[vat] 按纳税人类型细分:")
        gen_count, small_count = export_vat_domain(domains['vat'], output_dir)
        total += gen_count + small_count

    # 其他域：不细分
    for simple_domain in ['eit', 'invoice', 'financial_metrics']:
        if simple_domain not in domains:
            continue
        print(f"\n[{simple_domain}] 不细分:")
        count = export_simple_domain(simple_domain, domains[simple_domain], output_dir)
        total += count

    print(f"\n{'='*50}")
    print(f"总计导出: {total} 个概念定义")
    print(f"输出目录: {output_dir.absolute()}")


if __name__ == '__main__':
    main()
