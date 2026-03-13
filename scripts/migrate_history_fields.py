#!/usr/bin/env python3
"""数据迁移脚本：为历史记录添加新字段并移除调试字段

功能：
1. 为旧历史记录填充 user_id（默认值：1，假设为 sys 用户）
2. 为旧历史记录派生 domain 字段
3. 移除调试字段（main_output, entity_text, intent_text, sql_text）
4. 备份原文件到 query_history.json.backup

使用方法：
    python scripts/migrate_history_fields.py
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def derive_domain(entry: dict) -> str:
    """从历史记录条目派生 domain 字段"""
    route = entry.get("route", "")

    # 非 financial_data 路由，domain 为空
    if route != "financial_data":
        return ""

    # 从 result.entities.domain_hint 提取
    result = entry.get("result", {})
    entities = result.get("entities", {})
    domain_hint = entities.get("domain_hint", "")

    return domain_hint


def migrate_history():
    """执行迁移"""
    # 文件路径
    history_path = Path(__file__).resolve().parent.parent / "query_history.json"
    backup_path = Path(__file__).resolve().parent.parent / f"query_history.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if not history_path.exists():
        print(f"❌ 历史记录文件不存在: {history_path}")
        return

    # 备份原文件
    print(f"📦 备份原文件到: {backup_path}")
    shutil.copy2(history_path, backup_path)

    # 加载历史记录
    print(f"📖 加载历史记录: {history_path}")
    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not isinstance(history, list):
        print("❌ 历史记录格式错误，应为数组")
        return

    print(f"📊 共 {len(history)} 条记录")

    # 迁移统计
    stats = {
        "total": len(history),
        "user_id_added": 0,
        "domain_added": 0,
        "main_output_removed": 0,
        "entity_text_removed": 0,
        "intent_text_removed": 0,
        "sql_text_removed": 0,
    }

    # 逐条迁移
    for i, entry in enumerate(history):
        # 1. 填充 user_id（如果不存在）
        if "user_id" not in entry:
            entry["user_id"] = 1  # 默认为 sys 用户
            stats["user_id_added"] += 1

        # 2. 派生 domain（如果不存在）
        if "domain" not in entry:
            entry["domain"] = derive_domain(entry)
            stats["domain_added"] += 1

        # 3. 移除调试字段
        if "main_output" in entry:
            del entry["main_output"]
            stats["main_output_removed"] += 1

        if "entity_text" in entry:
            del entry["entity_text"]
            stats["entity_text_removed"] += 1

        if "intent_text" in entry:
            del entry["intent_text"]
            stats["intent_text_removed"] += 1

        if "sql_text" in entry:
            del entry["sql_text"]
            stats["sql_text_removed"] += 1

    # 保存迁移后的数据
    print(f"💾 保存迁移后的数据: {history_path}")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 打印统计信息
    print("\n✅ 迁移完成！")
    print(f"   总记录数: {stats['total']}")
    print(f"   添加 user_id: {stats['user_id_added']}")
    print(f"   添加 domain: {stats['domain_added']}")
    print(f"   移除 main_output: {stats['main_output_removed']}")
    print(f"   移除 entity_text: {stats['entity_text_removed']}")
    print(f"   移除 intent_text: {stats['intent_text_removed']}")
    print(f"   移除 sql_text: {stats['sql_text_removed']}")

    # 计算文件大小变化
    original_size = backup_path.stat().st_size
    new_size = history_path.stat().st_size
    size_diff = original_size - new_size
    size_percent = (size_diff / original_size * 100) if original_size > 0 else 0

    print(f"\n📉 文件大小变化:")
    print(f"   原始大小: {original_size / 1024 / 1024:.2f} MB")
    print(f"   新大小: {new_size / 1024 / 1024:.2f} MB")
    print(f"   减少: {size_diff / 1024 / 1024:.2f} MB ({size_percent:.1f}%)")


if __name__ == "__main__":
    migrate_history()
