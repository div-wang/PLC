#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import secrets
import time
import os
import sys
import shutil
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
    _PYQT_AVAILABLE = True
except Exception:
    Qt = None
    QFont = None
    QDialog = object
    QFormLayout = object
    QHBoxLayout = object
    QLabel = object
    QLineEdit = object
    QPushButton = object
    QVBoxLayout = object
    QWidget = object
    _PYQT_AVAILABLE = False

import app_storage


def _load_setting_root() -> Dict[str, Any]:
    raw = app_storage.load_json("setting.json", {})
    return dict(raw) if isinstance(raw, dict) else {}


def _find_user(users: List[Dict[str, Any]], username: str) -> Optional[Dict[str, Any]]:
    u = str(username or "").strip()
    for item in users:
        if not isinstance(item, dict):
            continue
        if str(item.get("username") or "").strip() == u:
            return dict(item)
    return None


@dataclass
class AuthUser:
    username: str
    role: str


class AuthManager:
    def __init__(self):
        self._current: Optional[AuthUser] = None
        app_storage.ensure_user_file_from_resource("setting.json")

    @property
    def user(self) -> Optional[AuthUser]:
        return self._current

    def role(self) -> str:
        return str(self._current.role) if self._current else ""

    def username(self) -> str:
        return str(self._current.username) if self._current else ""

    def logout(self) -> None:
        self._current = None
        try:
            p = self._token_file_path()
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    def _token_file_path(self) -> str:
        p = app_storage.user_file_path("token_cache.txt")
        if os.path.exists(p):
            return p
        try:
            if getattr(sys, "frozen", False):
                old_base = os.path.dirname(sys.executable)
            else:
                old_base = os.path.dirname(os.path.abspath(__file__))
            old_p = os.path.join(old_base, "token_cache.txt")
            if os.path.exists(old_p):
                try:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    shutil.copy2(old_p, p)
                    os.remove(old_p)
                except Exception:
                    pass
        except Exception:
            pass
        return p

    def _users(self) -> List[Dict[str, Any]]:
        settings = _load_setting_root()
        users = settings.get("users")
        if isinstance(users, list):
            return [dict(x) for x in users if isinstance(x, dict)]
        return []

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        users = self._users()
        u = _find_user(users, username)
        if u is None:
            return False, "用户名或密码错误"
        if str(u.get("password") or "") != str(password or ""):
            return False, "用户名或密码错误"

        role = str(u.get("role") or "user").strip() or "user"
        self._current = AuthUser(username=str(u.get("username") or ""), role=role)

        token = secrets.token_urlsafe(32)
        expires_at = int(time.time() + 30 * 24 * 3600)
        payload = {
            "token": token,
            "username": self._current.username,
            "role": self._current.role,
            "expires_at": expires_at,
        }
        try:
            with open(self._token_file_path(), "w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass
        return True, ""

    def restore_session(self) -> bool:
        try:
            p = self._token_file_path()
            if not os.path.exists(p):
                return False
            with open(p, "r", encoding="utf-8") as f:
                text = f.read().strip()
            raw = json.loads(text) if text else {}
        except Exception:
            return False
        if not isinstance(raw, dict):
            return False
        token = str(raw.get("token") or "").strip()
        username = str(raw.get("username") or "").strip()
        expires_at = raw.get("expires_at")
        try:
            expires_at_i = int(expires_at)
        except Exception:
            return False
        if not token or not username:
            return False
        if int(time.time()) >= expires_at_i:
            return False

        u = _find_user(self._users(), username)
        if u is None:
            return False
        role = str(u.get("role") or "user").strip() or "user"
        self._current = AuthUser(username=username, role=role)
        return True


class LoginDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], auth: AuthManager):
        if not _PYQT_AVAILABLE:
            raise RuntimeError("PyQt5 is required for LoginDialog")
        super().__init__(parent)
        self._auth = auth

        self.setWindowTitle("登录")
        self.setModal(True)
        self.resize(440, 360)
        self.setMinimumSize(440, 360)
        self.setStyleSheet(
            "QDialog { background: white; }"
            "QLabel { color: #111827; }"
            "QLabel#Tip { color: #4b5563; }"
            "QLineEdit { border: 1px solid #d1d5db; border-radius: 10px; padding: 10px 12px; font-size: 14px; }"
            "QLineEdit:focus { border: 1px solid #1677ff; }"
            "QPushButton { border: none; border-radius: 10px; padding: 10px 16px; font-size: 14px; }"
            "QPushButton#LoginBtn { background: #1677ff; color: white; font-size: 16px; padding: 12px 20px; }"
            "QPushButton#LoginBtn:hover { background: #4096ff; }"
            "QLabel#Error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 12px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("请登录")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        tip = QLabel("登录有效期 1 个月。")
        tip.setObjectName("Tip")
        tip.setWordWrap(True)
        root.addWidget(tip)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form_host = QWidget()
        form_host.setLayout(form)
        form_row = QHBoxLayout()
        form_row.setContentsMargins(0, 0, 0, 0)
        form_row.addStretch(1)
        form_row.addWidget(form_host)
        form_row.addStretch(1)
        root.addLayout(form_row)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setFixedWidth(260)
        form.addRow("用户名", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(260)
        form.addRow("密码", self.password_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("Error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        root.addSpacing(10)
        root.addStretch(1)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        actions.setAlignment(Qt.AlignHCenter)
        root.addLayout(actions)

        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("LoginBtn")
        self.login_btn.setDefault(True)
        self.login_btn.setMinimumHeight(46)
        self.login_btn.setMinimumWidth(240)

        actions.addWidget(self.login_btn, 0, Qt.AlignHCenter)
        
        self.login_btn.clicked.connect(self._on_login)

        self.username_input.returnPressed.connect(self._on_login)
        self.password_input.returnPressed.connect(self._on_login)

        self.username_input.setFocus(Qt.ActiveWindowFocusReason)

    def _on_login(self) -> None:
        self.error_label.setVisible(False)
        self.error_label.setText("")
        username = self.username_input.text().strip()
        password = self.password_input.text()
        ok, err = self._auth.login(username, password)
        if ok:
            self.accept()
            return
        self.error_label.setText(err or "登录失败")
        self.error_label.setVisible(True)
