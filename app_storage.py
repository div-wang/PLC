#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import shutil
import sys
from typing import Any, Dict, Optional

from PyQt5.QtCore import QStandardPaths


def _safe_mkdir(p: str) -> str:
    os.makedirs(p, exist_ok=True)
    return p


def app_data_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".plc_monitor")
    return _safe_mkdir(base)


def cache_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    if not base:
        base = app_data_dir()
    return _safe_mkdir(base)


def ui_cache_dir() -> str:
    return _safe_mkdir(os.path.join(cache_dir(), "ui"))


def user_file_path(filename: str) -> str:
    return os.path.join(app_data_dir(), filename)


def resource_file_path(filename: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = getattr(sys, "_MEIPASS")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


def ensure_user_file_from_resource(filename: str) -> str:
    dst = user_file_path(filename)
    if os.path.exists(dst):
        return dst
    src = resource_file_path(filename)
    if os.path.exists(src):
        try:
            shutil.copy2(src, dst)
        except Exception:
            pass
    return dst


def load_json(filename: str, default: Any) -> Any:
    path = ensure_user_file_from_resource(filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict) and isinstance(data, dict):
            return {**default, **data}
        return data
    except Exception:
        return default


def save_json(filename: str, data: Any) -> Optional[str]:
    path = user_file_path(filename)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
        return path
    except Exception:
        return None

