"""统一配置加载工具：从 JSON 文件加载配置，失败时 graceful fallback"""
import json
import os
from pathlib import Path
from typing import Any, Optional


CONFIG_DIR = Path(__file__).resolve().parent


def load_json(path, fallback=None):
    """加载单个 JSON 文件，失败返回 fallback 并打印警告。

    Args:
        path: JSON 文件路径（str 或 Path）
        fallback: 加载失败时的默认值

    Returns:
        dict/list 或 fallback
    """
    try:
        p = Path(path)
        if not p.exists():
            return fallback if fallback is not None else {}
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[config_loader] Warning: failed to load {path}: {e}")
        return fallback if fallback is not None else {}


def load_json_dir(dir_path, fallback=None):
    """加载目录下所有 JSON 文件，合并为一个 dict。

    每个文件名（去扩展名）作为顶层 key。

    Args:
        dir_path: 目录路径
        fallback: 加载失败时的默认值

    Returns:
        dict
    """
    try:
        d = Path(dir_path)
        if not d.exists() or not d.is_dir():
            return fallback if fallback is not None else {}
        merged = {}
        for f in sorted(d.glob('*.json')):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                key = f.stem
                merged[key] = data
            except Exception as e:
                print(f"[config_loader] Warning: failed to load {f}: {e}")
        return merged if merged else (fallback if fallback is not None else {})
    except Exception as e:
        print(f"[config_loader] Warning: failed to load dir {dir_path}: {e}")
        return fallback if fallback is not None else {}
