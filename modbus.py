#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import math
import os
import json
import struct
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QAbstractItemView,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import app_storage
import db


def _deep_merge(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k] = _deep_merge(out.get(k), v)
        else:
            out[k] = v
    return out


def _load_setting_template() -> Dict[str, Any]:
    try:
        path = app_storage.resource_file_path("setting.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_setting_root() -> Dict[str, Any]:
    template = _load_setting_template()
    user = app_storage.load_json("setting.json", {})
    if not isinstance(user, dict):
        user = {}
    merged = _deep_merge(template, user)

    try:
        old_path = app_storage.user_file_path("settings.json")
        if os.path.exists(old_path) and "modbus" not in merged:
            with open(old_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            if isinstance(old, dict):
                merged["modbus"] = dict(old)
    except Exception:
        pass

    if merged != user:
        try:
            app_storage.save_json("setting.json", merged)
        except Exception:
            pass
    return merged


def _today_log_path() -> str:
    d = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(app_storage.logs_dir(), f"{d}.log")


def _cleanup_logs(retention_days: int = 30) -> None:
    try:
        base = app_storage.logs_dir()
        now = datetime.now()
        for name in os.listdir(base):
            if not name.endswith(".log"):
                continue
            stem = name[:-4]
            try:
                dt = datetime.strptime(stem, "%Y-%m-%d")
            except Exception:
                continue
            if (now - dt).days > int(retention_days):
                try:
                    os.remove(os.path.join(base, name))
                except Exception:
                    pass
    except Exception:
        pass


def _append_log_line(text: str) -> None:
    try:
        path = _today_log_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


def _u16_to_bytes_be(v: int) -> bytes:
    return bytes([(v >> 8) & 0xFF, v & 0xFF])


def _reorder_4(b: bytes, byte_order: str) -> bytes:
    if len(b) != 4:
        raise ValueError("expected 4 bytes")
    order = (byte_order or "ABCD").upper()
    idx = {"A": 0, "B": 1, "C": 2, "D": 3}
    try:
        return bytes([b[idx[ch]] for ch in order])
    except Exception as e:
        raise ValueError(f"invalid byte_order: {byte_order}") from e


def decode_uint32(regs: Sequence[int], byte_order: str = "ABCD") -> int:
    if len(regs) != 2:
        raise ValueError("uint32 expects 2 registers")
    b = _u16_to_bytes_be(regs[0]) + _u16_to_bytes_be(regs[1])
    b = _reorder_4(b, byte_order)
    return struct.unpack(">I", b)[0]


def decode_float32(regs: Sequence[int], byte_order: str = "ABCD") -> float:
    if len(regs) != 2:
        raise ValueError("float32 expects 2 registers")
    b = _u16_to_bytes_be(regs[0]) + _u16_to_bytes_be(regs[1])
    b = _reorder_4(b, byte_order)
    return struct.unpack(">f", b)[0]


@dataclass(frozen=True)
class _RTUSettings:
    unit_id: int
    timeout_s: float
    serial_port: str
    baudrate: int
    parity: str
    stopbits: int
    bytesize: int


class _RTUModbusClient:
    def __init__(self, settings: _RTUSettings):
        self.settings = settings
        self._instrument = None
        self._lock = threading.RLock()

    def _byteorder_const(self, minimalmodbus, byte_order: str) -> int:
        bo = (byte_order or "ABCD").upper()
        if bo == "ABCD":
            return int(getattr(minimalmodbus, "BYTEORDER_BIG", 0))
        if bo == "CDAB":
            return int(getattr(minimalmodbus, "BYTEORDER_BIG_SWAP", 2))
        if bo == "BADC":
            return int(getattr(minimalmodbus, "BYTEORDER_LITTLE_SWAP", 3))
        if bo == "DCBA":
            return int(getattr(minimalmodbus, "BYTEORDER_LITTLE", 1))
        return int(getattr(minimalmodbus, "BYTEORDER_BIG", 0))

    def connect(self) -> Tuple[bool, str]:
        with self._lock:
            try:
                import minimalmodbus

                self._instrument = minimalmodbus.Instrument(
                    str(self.settings.serial_port),
                    int(self.settings.unit_id),
                )
                self._instrument.serial.baudrate = int(self.settings.baudrate)
                self._instrument.serial.bytesize = int(self.settings.bytesize)
                parity = str(self.settings.parity or "N").upper()
                if parity == "E":
                    self._instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
                elif parity == "O":
                    self._instrument.serial.parity = minimalmodbus.serial.PARITY_ODD
                else:
                    self._instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
                self._instrument.serial.stopbits = int(self.settings.stopbits)
                self._instrument.serial.timeout = float(self.settings.timeout_s)
                self._instrument.mode = minimalmodbus.MODE_RTU
                self._instrument.clear_buffers_before_each_transaction = True
                self._instrument.offset = 0

                try:
                    if hasattr(self._instrument.serial, "is_open") and not self._instrument.serial.is_open:
                        self._instrument.serial.open()
                except Exception:
                    pass

                return True, ""
            except Exception as e:
                self._instrument = None
                return False, str(e)

    def read_float32(self, address: int, byte_order: str) -> Tuple[Optional[float], str]:
        with self._lock:
            if self._instrument is None:
                return None, "not connected"
            try:
                import minimalmodbus

                v = self._instrument.read_float(
                    int(address),
                    functioncode=3,
                    number_of_registers=2,
                    byteorder=self._byteorder_const(minimalmodbus, byte_order),
                )
                return float(v), ""
            except Exception as e:
                return None, str(e)

    def read_uint32(self, address: int, byte_order: str) -> Tuple[Optional[int], str]:
        with self._lock:
            if self._instrument is None:
                return None, "not connected"
            try:
                import minimalmodbus

                v = self._instrument.read_long(
                    int(address),
                    functioncode=3,
                    number_of_registers=2,
                    signed=False,
                    byteorder=self._byteorder_const(minimalmodbus, byte_order),
                )
                return int(v), ""
            except Exception:
                pass
            try:
                regs = self._instrument.read_registers(int(address), 2, functioncode=3)
                if regs is None or len(regs) != 2:
                    return None, "empty response"
                return int(decode_uint32([int(regs[0]) & 0xFFFF, int(regs[1]) & 0xFFFF], byte_order=byte_order)), ""
            except Exception as e:
                return None, str(e)

    def close(self) -> None:
        with self._lock:
            try:
                if self._instrument is not None:
                    try:
                        if hasattr(self._instrument, "serial") and hasattr(self._instrument.serial, "is_open") and self._instrument.serial.is_open:
                            self._instrument.serial.close()
                    except Exception:
                        pass
            finally:
                self._instrument = None

    def is_connected(self) -> bool:
        with self._lock:
            return self._instrument is not None

    def read_holding_registers(self, address: int, count: int) -> Tuple[Optional[List[int]], str]:
        with self._lock:
            if self._instrument is None:
                return None, "not connected"
            try:
                regs = self._instrument.read_registers(int(address), int(count), functioncode=3)
                if regs is None:
                    return None, "empty response"
                return [int(x) & 0xFFFF for x in regs], ""
            except Exception as e:
                return None, str(e)


DEFAULT_SETTINGS: Dict[str, Any] = {
    "instrument_port": "COM1",
    "instrument_address": 1,
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "timeout_s": 1.0,
    "byte_order": "ABCD",
    "load_sign": 1,
    "load_offset": 0.0,
    "load_clamp_zero": False,
    "scale": 1.0,
    "sample_save_interval_s": 5,
}


def load_modbus_settings() -> Dict[str, Any]:
    root = _load_setting_root()
    raw = root.get("modbus")
    if not isinstance(raw, dict):
        raw = {}
    merged = {**DEFAULT_SETTINGS, **raw}
    merged["instrument_port"] = str(merged.get("instrument_port") or "").strip() or DEFAULT_SETTINGS["instrument_port"]
    try:
        merged["instrument_address"] = int(merged.get("instrument_address", DEFAULT_SETTINGS["instrument_address"]))
    except Exception:
        merged["instrument_address"] = DEFAULT_SETTINGS["instrument_address"]
    try:
        merged["baudrate"] = int(merged.get("baudrate", DEFAULT_SETTINGS["baudrate"]))
    except Exception:
        merged["baudrate"] = DEFAULT_SETTINGS["baudrate"]
    try:
        merged["bytesize"] = int(merged.get("bytesize", DEFAULT_SETTINGS["bytesize"]))
    except Exception:
        merged["bytesize"] = DEFAULT_SETTINGS["bytesize"]
    merged["parity"] = str(merged.get("parity") or DEFAULT_SETTINGS["parity"]).upper()[:1]
    if merged["parity"] not in {"N", "E", "O"}:
        merged["parity"] = DEFAULT_SETTINGS["parity"]
    try:
        merged["stopbits"] = int(merged.get("stopbits", DEFAULT_SETTINGS["stopbits"]))
    except Exception:
        merged["stopbits"] = DEFAULT_SETTINGS["stopbits"]
    try:
        merged["timeout_s"] = float(merged.get("timeout_s", DEFAULT_SETTINGS["timeout_s"]))
    except Exception:
        merged["timeout_s"] = DEFAULT_SETTINGS["timeout_s"]
    merged["timeout_s"] = max(0.2, float(merged["timeout_s"]))
    merged["byte_order"] = str(merged.get("byte_order") or DEFAULT_SETTINGS["byte_order"]).upper()
    if merged["byte_order"] not in {"ABCD", "BADC", "CDAB", "DCBA"}:
        merged["byte_order"] = DEFAULT_SETTINGS["byte_order"]

    try:
        merged["load_sign"] = int(merged.get("load_sign", DEFAULT_SETTINGS["load_sign"]))
    except Exception:
        merged["load_sign"] = DEFAULT_SETTINGS["load_sign"]
    merged["load_sign"] = -1 if int(merged["load_sign"]) < 0 else 1
    try:
        merged["load_offset"] = float(merged.get("load_offset", DEFAULT_SETTINGS["load_offset"]))
    except Exception:
        merged["load_offset"] = DEFAULT_SETTINGS["load_offset"]
    merged["load_clamp_zero"] = bool(merged.get("load_clamp_zero", DEFAULT_SETTINGS["load_clamp_zero"]))

    try:
        merged["scale"] = float(merged.get("scale", DEFAULT_SETTINGS["scale"]))
    except Exception:
        merged["scale"] = DEFAULT_SETTINGS["scale"]
    merged["scale"] = max(0.0, float(merged["scale"]))

    try:
        merged["sample_save_interval_s"] = int(merged.get("sample_save_interval_s", DEFAULT_SETTINGS["sample_save_interval_s"]))
    except Exception:
        merged["sample_save_interval_s"] = int(DEFAULT_SETTINGS["sample_save_interval_s"])
    merged["sample_save_interval_s"] = max(0, int(merged["sample_save_interval_s"]))
    return merged


def save_modbus_settings(data: Dict[str, Any]) -> Optional[str]:
    root = _load_setting_root()
    if not isinstance(root, dict):
        root = {}
    root["modbus"] = dict(data)
    return app_storage.save_json("setting.json", root)


RING_DB_DEFAULT: Dict[str, Any] = {"records": []}


def _active_project_id() -> str:
    raw = app_storage.load_json("project.json", [])
    if not isinstance(raw, list):
        return "default"
    active: Optional[Dict[str, Any]] = None
    for p in raw:
        if isinstance(p, dict) and bool(p.get("is_active", False)):
            active = p
            break
    if active is None and raw and isinstance(raw[0], dict):
        active = raw[0]
    if isinstance(active, dict):
        pid = str(active.get("name_en") or active.get("name_cn") or "").strip()
        if pid:
            return pid
    return "default"


def _load_ring_db() -> Dict[str, Any]:
    raw = app_storage.load_json("ring_records.json", RING_DB_DEFAULT)
    if not isinstance(raw, dict):
        raw = dict(RING_DB_DEFAULT)
    records = raw.get("records")
    if not isinstance(records, list):
        records = []
    return {"records": list(records)}


def _save_ring_db(db: Dict[str, Any]) -> Optional[str]:
    payload = {"records": list(db.get("records") or [])}
    return app_storage.save_json("ring_records.json", payload)


MODBUS_SAMPLES_DB_DEFAULT: Dict[str, Any] = {"records": []}


def _load_modbus_samples_db() -> Dict[str, Any]:
    raw = app_storage.load_json("modbus_samples.json", MODBUS_SAMPLES_DB_DEFAULT)
    if not isinstance(raw, dict):
        raw = dict(MODBUS_SAMPLES_DB_DEFAULT)
    records = raw.get("records")
    if not isinstance(records, list):
        records = []
    return {"records": list(records)}


def _save_modbus_samples_db(db: Dict[str, Any]) -> Optional[str]:
    payload = {"records": list(db.get("records") or [])}
    return app_storage.save_json("modbus_samples.json", payload)


class ModbusSettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], settings: Dict[str, Any], is_admin: bool):
        super().__init__(parent)
        self._settings = dict(settings)
        self._is_admin = bool(is_admin)

        self.setWindowTitle("Modbus设置")
        self.setModal(True)
        self.resize(420, 420)

        root = QVBoxLayout(self)

        form = QFormLayout()
        root.addLayout(form)

        self.port_input = QLineEdit(str(self._settings.get("instrument_port", "")))
        form.addRow("COM口", self.port_input)

        self.address_input = QSpinBox()
        self.address_input.setRange(1, 247)
        self.address_input.setValue(int(self._settings.get("instrument_address", 1)))
        form.addRow("通讯地址", self.address_input)

        self.baudrate_input = QSpinBox()
        self.baudrate_input.setRange(300, 115200)
        self.baudrate_input.setValue(int(self._settings.get("baudrate", 9600)))
        form.addRow("波特率", self.baudrate_input)

        self.parity_input = QComboBox()
        self.parity_input.addItems(["N", "E", "O"])
        self.parity_input.setCurrentText(str(self._settings.get("parity", "N")).upper())
        form.addRow("校验位", self.parity_input)

        self.stopbits_input = QComboBox()
        self.stopbits_input.addItems(["1", "2"])
        self.stopbits_input.setCurrentText(str(self._settings.get("stopbits", 1)))
        form.addRow("停止位", self.stopbits_input)

        self.bytesize_input = QComboBox()
        self.bytesize_input.addItems(["7", "8"])
        self.bytesize_input.setCurrentText(str(self._settings.get("bytesize", 8)))
        form.addRow("数据位", self.bytesize_input)

        self.timeout_input = QDoubleSpinBox()
        self.timeout_input.setRange(0.2, 30.0)
        self.timeout_input.setDecimals(1)
        self.timeout_input.setValue(float(self._settings.get("timeout_s", 1.0)))
        form.addRow("超时(s)", self.timeout_input)

        self.byte_order_input = QComboBox()
        self.byte_order_input.addItems(["ABCD", "BADC", "CDAB", "DCBA"])
        self.byte_order_input.setCurrentText(str(self._settings.get("byte_order", "ABCD")).upper())
        form.addRow("字节序", self.byte_order_input)

        self.load_sign_input = QComboBox()
        self.load_sign_input.addItems(["正常", "取反"])
        self.load_sign_input.setCurrentIndex(1 if int(self._settings.get("load_sign", 1)) < 0 else 0)
        form.addRow("载荷符号", self.load_sign_input)

        self.load_offset_input = QDoubleSpinBox()
        self.load_offset_input.setRange(-1000000.0, 1000000.0)
        self.load_offset_input.setDecimals(3)
        self.load_offset_input.setValue(float(self._settings.get("load_offset", 0.0)))
        form.addRow("载荷偏移(kg/m)", self.load_offset_input)

        self.load_clamp_zero_input = QCheckBox("载荷小于0时置为0")
        self.load_clamp_zero_input.setChecked(bool(self._settings.get("load_clamp_zero", False)))
        form.addRow("", self.load_clamp_zero_input)

        self.sample_save_interval_input = QSpinBox()
        self.sample_save_interval_input.setRange(0, 86400)
        self.sample_save_interval_input.setValue(int(self._settings.get("sample_save_interval_s", 5)))
        form.addRow("采样保存间隔(s)", self.sample_save_interval_input)

        if self._is_admin:
            self.scale_input = QDoubleSpinBox()
            self.scale_input.setRange(0.0, 1000000.0)
            self.scale_input.setDecimals(6)
            self.scale_input.setValue(float(self._settings.get("scale", 1.0)))
            form.addRow("总重量比例", self.scale_input)

        actions = QHBoxLayout()
        actions.addStretch(1)
        root.addLayout(actions)

        self.cancel_btn = QPushButton("取消")
        self.save_btn = QPushButton("保存")
        self.save_btn.setDefault(True)
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.save_btn)

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save)

    def _on_save(self) -> None:
        port = self.port_input.text().strip() or DEFAULT_SETTINGS["instrument_port"]
        data: Dict[str, Any] = dict(self._settings)
        data.update({
            "instrument_port": port,
            "instrument_address": int(self.address_input.value()),
            "baudrate": int(self.baudrate_input.value()),
            "parity": str(self.parity_input.currentText()).upper(),
            "stopbits": int(self.stopbits_input.currentText()),
            "bytesize": int(self.bytesize_input.currentText()),
            "timeout_s": float(self.timeout_input.value()),
            "byte_order": str(self.byte_order_input.currentText()).upper(),
            "load_sign": -1 if int(self.load_sign_input.currentIndex()) == 1 else 1,
            "load_offset": float(self.load_offset_input.value()),
            "load_clamp_zero": bool(self.load_clamp_zero_input.isChecked()),
            "sample_save_interval_s": int(self.sample_save_interval_input.value()),
        })
        if self._is_admin:
            try:
                data["scale"] = max(0.0, float(self.scale_input.value()))
            except Exception:
                data["scale"] = float(self._settings.get("scale", 1.0))
        save_modbus_settings(data)
        self._settings = dict(data)
        self.accept()

    def settings(self) -> Dict[str, Any]:
        return dict(self._settings)


class ModbusPage:
    def __init__(self, user_role: str = "user"):
        self.page = QWidget()
        self.page.setStyleSheet("background-color: #f5f7fa;")

        try:
            db.init_db()
            db.migrate_ring_records_json_if_needed()
        except Exception:
            pass

        _cleanup_logs(30)

        self._settings = load_modbus_settings()
        self._user_role = str(user_role or "user").strip() or "user"
        self._client: Optional[_RTUModbusClient] = None
        self._last_io_error = ""
        self._last_load_diag_at = 0.0
        self._baseline_total_weight: Optional[float] = None
        self._last_total_weight: Optional[float] = None
        self._travel_total: float = 0.0
        self._baseline_travel_total: Optional[float] = None
        self._last_poll_at: float = 0.0
        self._last_sample_at: float = 0.0
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_once)
        self._status_cb = None
        self._auto_attempts = 0
        self._auto_connecting = False

        root = QVBoxLayout(self.page)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        toolbar = QFrame()
        toolbar.setStyleSheet("QFrame { background: white; border: none; border-radius: 10px; }")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 10, 14, 10)
        toolbar_layout.setSpacing(10)

        self.status_label = QLabel("未连接")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedWidth(110)
        self.status_label.setStyleSheet("background: #fff2e8; color: #d4380d; border: none; border-radius: 8px; padding: 6px 10px;")

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet(
            "QPushButton { background: #f0f0f0; color: #333; border: none; border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background: #e6f4ff; color: #1677ff; }"
        )
        self.settings_btn.clicked.connect(self._open_settings)

        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.settings_btn)
        root.addWidget(toolbar)

        self._ring_page = 1
        self._ring_page_size = 12
        ring_frame = QFrame()
        ring_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        ring_layout = QVBoxLayout(ring_frame)
        ring_layout.setContentsMargins(14, 12, 14, 12)
        ring_layout.setSpacing(10)

        ring_top = QHBoxLayout()
        ring_top.setContentsMargins(0, 0, 0, 0)
        ring_top.setSpacing(10)
        ring_title = QLabel("环号记录")
        ring_title.setStyleSheet("color: #111827; font-size: 16px; font-weight: 600;")
        ring_top.addWidget(ring_title)
        ring_top.addStretch(1)

        self.ring_page_label = QLabel("")
        self.ring_page_label.setStyleSheet("color: #6b7280; font-size: 13px;")

        self.ring_prev_btn = QPushButton("上一页")
        self.ring_prev_btn.setCursor(Qt.PointingHandCursor)
        self.ring_prev_btn.setStyleSheet(
            "QPushButton { background: #f3f4f6; color: #111827; border: none; border-radius: 8px; padding: 6px 10px; }"
            "QPushButton:hover { background: #e5e7eb; }"
        )
        self.ring_next_btn = QPushButton("下一页")
        self.ring_next_btn.setCursor(Qt.PointingHandCursor)
        self.ring_next_btn.setStyleSheet(
            "QPushButton { background: #f3f4f6; color: #111827; border: none; border-radius: 8px; padding: 6px 10px; }"
            "QPushButton:hover { background: #e5e7eb; }"
        )

        ring_top.addWidget(self.ring_page_label)
        ring_top.addWidget(self.ring_prev_btn)
        ring_top.addWidget(self.ring_next_btn)
        ring_layout.addLayout(ring_top)

        self.ring_table = QTableWidget()
        self.ring_table.setColumnCount(3)
        self.ring_table.setHorizontalHeaderLabels(["环号", "重量", "时间"])
        self.ring_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ring_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ring_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ring_table.verticalHeader().setVisible(False)
        self.ring_table.horizontalHeader().setStretchLastSection(True)
        self.ring_table.setStyleSheet(
            "QTableWidget { border: 1px solid #e5e7eb; border-radius: 10px; gridline-color: #e5e7eb; }"
            "QHeaderView::section { background: #f9fafb; color: #374151; padding: 6px 8px; border: none; border-bottom: 1px solid #e5e7eb; }"
        )
        ring_layout.addWidget(self.ring_table)

        root.addWidget(ring_frame)
        root.setStretchFactor(ring_frame, 2)

        self._latest_flow: Optional[float] = None
        self._latest_load: Optional[float] = None
        self._latest_speed: Optional[float] = None
        self._latest_total_weight: Optional[float] = None
        self._latest_total_unit: str = self._total_weight_display_unit()
        self._set_values(None, None, None, None, self._latest_total_unit)

        log_frame = QFrame()
        log_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(14, 12, 14, 12)
        log_layout.setSpacing(10)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("QTextEdit { background: #0b1220; color: #d1d5db; border: none; border-radius: 10px; font-family: Consolas; }")
        log_layout.addWidget(self.log_area)

        root.addWidget(log_frame)
        root.setStretchFactor(log_frame, 1)

        self.ring_prev_btn.clicked.connect(self._ring_prev_page)
        self.ring_next_btn.clicked.connect(self._ring_next_page)
        self._refresh_ring_table()

    def get_page(self) -> QWidget:
        return self.page

    def set_user_role(self, user_role: str) -> None:
        self._user_role = str(user_role or "user").strip() or "user"

    def set_status_callback(self, cb) -> None:
        self._status_cb = cb

    def _emit_status(self, status: str) -> None:
        self._set_status_badge(str(status))
        try:
            if callable(self._status_cb):
                self._status_cb(str(status))
        except Exception:
            pass

    def _set_status_badge(self, status: str) -> None:
        s = str(status or "").strip().lower()
        if s == "connected":
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("background: #f6ffed; color: #389e0d; border: none; border-radius: 8px; padding: 6px 10px;")
            return
        if s == "connecting":
            self.status_label.setText("连接中")
            self.status_label.setStyleSheet("background: #f5f5f5; color: #595959; border: none; border-radius: 8px; padding: 6px 10px;")
            return
        self.status_label.setText("未连接")
        self.status_label.setStyleSheet("background: #fff2e8; color: #d4380d; border: none; border-radius: 8px; padding: 6px 10px;")

    def next_ring(self) -> None:
        self._on_next_ring()

    def start_auto_connect(self, max_attempts: int = 3, interval_ms: int = 500) -> None:
        if self._auto_connecting:
            return
        self._auto_connecting = True
        self._auto_attempts = 0
        self._auto_interval_ms = max(100, int(interval_ms))
        self._emit_status("connecting")
        QTimer.singleShot(0, lambda: self._auto_connect_step(max_attempts))

    def _auto_connect_step(self, max_attempts: int) -> None:
        if not self._auto_connecting:
            return
        if self._client is not None and self._client.is_connected():
            self._emit_status("connected")
            self._auto_connecting = False
            return
        ok = self._connect()
        if ok and self._client is not None and self._client.is_connected():
            self._emit_status("connected")
            self._auto_connecting = False
            return
        self._auto_attempts += 1
        if self._auto_attempts >= int(max_attempts):
            self._emit_status("failed")
            self._auto_connecting = False
            return
        self._emit_status("connecting")
        QTimer.singleShot(int(getattr(self, "_auto_interval_ms", 500)), lambda: self._auto_connect_step(max_attempts))

    def _total_weight_display_unit(self) -> str:
        return "t"

    def _make_card(self, title: str, unit: str) -> Dict[str, Any]:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMinimumHeight(150)
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #6b7280; font-size: 16px; font-weight: 600;")

        unit_label = QLabel(unit)
        unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        unit_label.setStyleSheet("color: #9ca3af; font-size: 14px;")

        top.addWidget(title_label)
        top.addStretch(1)
        top.addWidget(unit_label)

        value_label = QLabel("--")
        value_font = QFont()
        value_font.setPointSize(28)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: #333;")

        layout.addLayout(top)
        layout.addWidget(value_label)
        layout.addStretch(1)

        return {"frame": frame, "title": title_label, "value": value_label, "unit": unit_label}

    def _log(self, msg: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{now}] {msg}"
        _append_log_line(line)
        try:
            self.log_area.append(line)
            doc = self.log_area.document()
            while doc.blockCount() > 1000:
                cursor = self.log_area.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()
        except Exception:
            pass

    def _ring_records_for_current_project(self) -> List[Dict[str, Any]]:
        pid = _active_project_id()
        ring_db = _load_ring_db()
        records = ring_db.get("records") or []
        filtered: List[Dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            if str(r.get("project_id") or "") != pid:
                continue
            filtered.append(dict(r))
        filtered.sort(key=lambda x: int(x.get("ring_no") or 0))
        return filtered

    def _refresh_ring_table(self) -> None:
        rows = self._ring_records_for_current_project()
        total = len(rows)
        size = max(1, int(getattr(self, "_ring_page_size", 12)))
        total_pages = max(1, (total + size - 1) // size)
        self._ring_page = max(1, min(int(getattr(self, "_ring_page", 1)), total_pages))

        start = (self._ring_page - 1) * size
        page_rows = rows[start : start + size]

        try:
            self.ring_table.setRowCount(len(page_rows))
            for i, rec in enumerate(page_rows):
                ring_no = int(rec.get("ring_no") or 0)
                weight = rec.get("weight")
                ts = str(rec.get("time") or "")

                item0 = QTableWidgetItem(str(ring_no) if ring_no > 0 else "")
                item0.setTextAlignment(Qt.AlignCenter)
                self.ring_table.setItem(i, 0, item0)

                wtxt = ""
                try:
                    if isinstance(weight, (int, float)):
                        wtxt = f"{float(weight):.3f}"
                except Exception:
                    wtxt = ""
                item1 = QTableWidgetItem(wtxt)
                item1.setTextAlignment(Qt.AlignCenter)
                self.ring_table.setItem(i, 1, item1)

                item2 = QTableWidgetItem(ts)
                item2.setTextAlignment(Qt.AlignCenter)
                self.ring_table.setItem(i, 2, item2)

            self.ring_table.setColumnWidth(0, 90)
            self.ring_table.setColumnWidth(1, 140)
        except Exception:
            pass

        try:
            self.ring_page_label.setText(f"第 {self._ring_page}/{total_pages} 页（{total} 条）")
            self.ring_prev_btn.setEnabled(self._ring_page > 1)
            self.ring_next_btn.setEnabled(self._ring_page < total_pages)
        except Exception:
            pass

    def _ring_prev_page(self) -> None:
        self._ring_page = max(1, int(getattr(self, "_ring_page", 1)) - 1)
        self._refresh_ring_table()

    def _ring_next_page(self) -> None:
        self._ring_page = int(getattr(self, "_ring_page", 1)) + 1
        self._refresh_ring_table()

    def _on_next_ring(self) -> None:
        if self._last_total_weight is None:
            return
        pid = _active_project_id()
        records = self._ring_records_for_current_project()
        if records:
            last = records[-1]
            last_ring = int(last.get("ring_no") or 0)
            prev_total = float(last.get("total_weight") or 0.0)
            prev_travel_total = float(last.get("total_travel") or 0.0)
            ring_no = last_ring + 1
        else:
            ring_no = 1
            prev_total = float(self._baseline_total_weight) if self._baseline_total_weight is not None else float(self._last_total_weight)
            prev_travel_total = float(self._baseline_travel_total) if self._baseline_travel_total is not None else float(self._travel_total)

        current_total = float(self._last_total_weight)
        weight = current_total - float(prev_total)
        travel = float(self._travel_total) - float(prev_travel_total)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rec = {
            "project_id": pid,
            "ring_no": int(ring_no),
            "weight": float(weight),
            "travel": float(travel),
            "time": ts,
            "total_weight": float(current_total),
            "total_travel": float(self._travel_total),
        }

        ring_db = _load_ring_db()
        ring_rows = ring_db.get("records")
        if not isinstance(ring_rows, list):
            ring_rows = []
        ring_rows.append(rec)
        ring_db["records"] = ring_rows
        _save_ring_db(ring_db)
        try:
            db.upsert_ring_detail(
                project_id=str(pid),
                ring_no=int(ring_no),
                weight=float(weight),
                travel=float(travel),
                time_str=str(ts),
                total_weight=float(current_total),
                total_travel=float(self._travel_total),
            )
        except Exception:
            pass
        self._log(f"下一环: 环号={int(ring_no)}, 重量={float(weight):g}, 行程={float(travel):g}, 总重量={float(current_total):.3f}")
        try:
            total = len(self._ring_records_for_current_project())
            size = max(1, int(getattr(self, "_ring_page_size", 12)))
            self._ring_page = max(1, (total + size - 1) // size)
            self._refresh_ring_table()
        except Exception:
            pass

    def _set_connected_ui(self, connected: bool) -> None:
        self._set_status_badge("connected" if connected else "failed")

    def _build_client(self) -> _RTUModbusClient:
        s = dict(self._settings)
        settings = _RTUSettings(
            unit_id=int(s["instrument_address"]),
            timeout_s=float(s["timeout_s"]),
            serial_port=str(s["instrument_port"]),
            baudrate=int(s["baudrate"]),
            parity=str(s["parity"]),
            stopbits=int(s["stopbits"]),
            bytesize=int(s["bytesize"]),
        )
        return _RTUModbusClient(settings)

    def _connect(self) -> bool:
        self._log(f"连接中: {self._settings.get('instrument_port')} (地址:{self._settings.get('instrument_address')})")
        self._disconnect()
        self._client = self._build_client()
        ok, err = self._client.connect()
        if ok:
            self._last_load_diag_at = 0.0
            self._baseline_total_weight = None
            self._last_total_weight = None
            self._travel_total = 0.0
            self._baseline_travel_total = None
            self._last_poll_at = 0.0
            self._last_sample_at = 0.0
            self._set_connected_ui(True)
            self._poll_timer.start()
            self._poll_once()
            if self._client is None or not self._client.is_connected():
                return False
            self._emit_status("connected")
            self._log("已连接")
            return True
        self._disconnect()
        self._log(f"连接失败: {err}")
        return False

    def _disconnect(self) -> None:
        self._poll_timer.stop()
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._last_io_error = ""
        self._baseline_total_weight = None
        self._last_total_weight = None
        self._travel_total = 0.0
        self._baseline_travel_total = None
        self._last_poll_at = 0.0
        self._last_sample_at = 0.0
        self._set_connected_ui(False)

    def _toggle_connect(self) -> None:
        if self._client is not None and self._client.is_connected():
            self._disconnect()
            self._set_values(None, None, None, None, self._total_weight_display_unit())
            return
        ok = self._connect()
        if not ok:
            self._set_values(None, None, None, None, self._total_weight_display_unit())

    def _open_settings(self) -> None:
        dlg = ModbusSettingsDialog(self.page, self._settings, is_admin=(self._user_role == "admin"))
        if dlg.exec_() != QDialog.Accepted:
            return
        self._settings = dlg.settings()
        self._latest_total_unit = "t"
        if self._client is not None and self._client.is_connected():
            self._connect()

    def _read_regs(self, address: int, count: int) -> Optional[Tuple[int, ...]]:
        if self._client is None:
            return None
        regs, err = self._client.read_holding_registers(address=address, count=count)
        if regs is None:
            self._last_io_error = err or "unknown error"
            return None
        if len(regs) != count:
            self._last_io_error = f"unexpected registers length: {len(regs)}"
            return None
        try:
            self._last_io_error = ""
            return tuple(int(x) & 0xFFFF for x in regs)
        except Exception:
            self._last_io_error = "invalid registers"
            return None

    def _read_float32(self, address: int) -> Optional[float]:
        try:
            if self._client is None:
                return None
            v, err = self._client.read_float32(int(address), str(self._settings.get("byte_order") or "ABCD"))
            if v is None:
                self._last_io_error = err or "unknown error"
                return None
            self._last_io_error = ""
            v = float(v)
        except Exception:
            return None
        if math.isnan(v) or math.isinf(v):
            return None
        return v

    def _read_uint32(self, address: int) -> Optional[int]:
        try:
            if self._client is None:
                return None
            v, err = self._client.read_uint32(int(address), str(self._settings.get("byte_order") or "ABCD"))
            if v is None:
                self._last_io_error = err or "unknown error"
                return None
            self._last_io_error = ""
            return int(v)
        except Exception:
            return None

    def _set_values(
        self,
        flow: Optional[float],
        load: Optional[float],
        speed: Optional[float],
        total_weight: Optional[float],
        total_weight_unit: str,
    ) -> None:
        self._latest_flow = float(flow) if isinstance(flow, (int, float)) else None
        self._latest_load = float(load) if isinstance(load, (int, float)) else None
        self._latest_speed = float(speed) if isinstance(speed, (int, float)) else None
        self._latest_total_weight = float(total_weight) if isinstance(total_weight, (int, float)) else None
        self._latest_total_unit = str(total_weight_unit or self._total_weight_display_unit())

    def _poll_once(self) -> None:
        if self._client is None or not self._client.is_connected():
            self._disconnect()
            self._set_values(None, None, None, None, self._total_weight_display_unit())
            return

        total_int = self._read_uint32(20)

        if total_int is None:
            detail = self._last_io_error.strip()
            self._log("读取数据失败" if not detail else f"读取数据失败: {detail}")
            self._disconnect()
            self._set_values(None, None, None, None, self._total_weight_display_unit())
            if not self._auto_connecting:
                self.start_auto_connect(max_attempts=5, interval_ms=2000)
            return

        flow = self._read_float32(50)
        load_raw = self._read_float32(52)
        speed = self._read_float32(54)

        now_mono = time.monotonic()
        if self._last_poll_at > 0:
            dt = float(now_mono - self._last_poll_at)
            if 0.0 < dt < 5.0:
                try:
                    v_speed = float(speed)
                except Exception:
                    v_speed = 0.0
                if v_speed > 0:
                    self._travel_total += v_speed * dt
        self._last_poll_at = now_mono

        load: Optional[float] = None
        if isinstance(load_raw, (int, float)):
            load = float(load_raw)
            try:
                load = (load + float(self._settings.get("load_offset", 0.0))) * (1.0 if int(self._settings.get("load_sign", 1)) >= 0 else -1.0)
            except Exception:
                pass
            if bool(self._settings.get("load_clamp_zero", False)) and load < 0:
                load = 0.0

            if load_raw < 0:
                now = time.monotonic()
                if self._last_load_diag_at <= 0 or (now - self._last_load_diag_at) >= 30.0:
                    self._last_load_diag_at = now
                    regs = self._read_regs(52, 2)
                    if regs is not None and len(regs) == 2:
                        r0, r1 = int(regs[0]) & 0xFFFF, int(regs[1]) & 0xFFFF
                        candidates: List[str] = []
                        for bo in ("ABCD", "BADC", "CDAB", "DCBA"):
                            try:
                                v = float(decode_float32((r0, r1), byte_order=bo))
                                if math.isnan(v) or math.isinf(v):
                                    continue
                                candidates.append(f"{bo}={v:.6g}")
                            except Exception:
                                continue
                        bo_now = str(self._settings.get("byte_order") or "ABCD").upper()
                        msg = f"载荷为负，原始寄存器[52..53]=[0x{r0:04X},0x{r1:04X}]，当前字节序={bo_now}"
                        if candidates:
                            msg += "，候选解析: " + ", ".join(candidates)
                        self._log(msg)

        total_weight = float(total_int) / 1000.0
        total_unit = "t"
        try:
            scale = float(self._settings.get("scale", 1.0))
        except Exception:
            scale = 1.0
        scale = max(0.0, float(scale))
        total_weight = float(total_weight) * scale
        self._last_total_weight = float(total_weight)
        if self._baseline_total_weight is None:
            self._baseline_total_weight = float(total_weight)
        if self._baseline_travel_total is None:
            self._baseline_travel_total = float(self._travel_total)
        self._last_io_error = ""
        self._set_values(flow, load, speed, total_weight, total_unit)
        self._emit_status("connected")

        try:
            app_storage.save_json(
                "modbus_state.json",
                {
                    "project_id": _active_project_id(),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "flow": float(flow) if isinstance(flow, (int, float)) else None,
                    "load": float(load) if isinstance(load, (int, float)) else None,
                    "speed": float(speed) if isinstance(speed, (int, float)) else None,
                    "total_weight": float(total_weight),
                    "total_weight_unit": str(total_unit),
                    "travel_total": float(self._travel_total),
                },
            )
        except Exception:
            pass

        try:
            interval_s = int(self._settings.get("sample_save_interval_s", 0))
        except Exception:
            interval_s = 0
        interval_s = max(0, int(interval_s))
        if interval_s > 0:
            if self._last_sample_at <= 0 or (now_mono - self._last_sample_at) >= float(interval_s):
                self._last_sample_at = now_mono
                rec = {
                    "project_id": _active_project_id(),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "flow": float(flow) if isinstance(flow, (int, float)) else None,
                    "load": float(load) if isinstance(load, (int, float)) else None,
                    "speed": float(speed) if isinstance(speed, (int, float)) else None,
                    "total_weight": float(total_weight),
                    "total_weight_unit": str(total_unit),
                    "travel_total": float(self._travel_total),
                }
                db = _load_modbus_samples_db()
                rows = db.get("records")
                if not isinstance(rows, list):
                    rows = []
                rows.append(rec)
                if len(rows) > 20000:
                    rows = rows[-20000:]
                db["records"] = rows
                _save_modbus_samples_db(db)
