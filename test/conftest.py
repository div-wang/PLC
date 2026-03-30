#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pytest 配置文件和公共固件
"""
import os
import sys
import shutil
import tempfile
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_storage
import db


@pytest.fixture(scope="function")
def temp_db(tmp_path, monkeypatch):
    """临时数据库固件，每个测试用例使用独立的临时数据库"""
    # 修改数据库路径到临时目录
    temp_db_file = str(tmp_path / "test_plc_monitor.db")
    monkeypatch.setattr(app_storage, 'user_file_path', lambda filename: temp_db_file)
    if hasattr(db, 'db_path'):
        monkeypatch.setattr(db, 'db_path', lambda: temp_db_file)
    
    # 初始化新的测试数据库
    db.init_db()
    
    yield


@pytest.fixture(scope="function")
def test_project_id():
    """测试用项目ID"""
    return "test_project_001"


@pytest.fixture(autouse=True)
def mock_web_engine(monkeypatch):
    """在无头环境下Mock QWebEngineView避免崩溃"""
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        from unittest.mock import MagicMock
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            monkeypatch.setattr('home.QWebEngineView', MagicMock)
        except Exception:
            pass
