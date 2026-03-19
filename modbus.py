#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import math
import struct
import threading
import time
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import app_storage


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
    "z0_unit": "t",
    "z0_decimal": 2,
    "load_sign": 1,
    "load_offset": 0.0,
    "load_clamp_zero": False,
}


def load_modbus_settings() -> Dict[str, Any]:
    raw = app_storage.load_json("settings.json", DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        raw = dict(DEFAULT_SETTINGS)
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
    merged["z0_unit"] = str(merged.get("z0_unit") or DEFAULT_SETTINGS["z0_unit"]).strip()
    if merged["z0_unit"] not in {"kg", "t", "10t", "100t"}:
        merged["z0_unit"] = DEFAULT_SETTINGS["z0_unit"]
    try:
        merged["z0_decimal"] = int(merged.get("z0_decimal", DEFAULT_SETTINGS["z0_decimal"]))
    except Exception:
        merged["z0_decimal"] = DEFAULT_SETTINGS["z0_decimal"]
    merged["z0_decimal"] = max(0, min(3, int(merged["z0_decimal"])))
    if merged["z0_unit"] in {"10t", "100t"}:
        merged["z0_decimal"] = 0

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
    return merged


def save_modbus_settings(data: Dict[str, Any]) -> Optional[str]:
    return app_storage.save_json("settings.json", data)


class ModbusSettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], settings: Dict[str, Any]):
        super().__init__(parent)
        self._settings = dict(settings)

        self.setWindowTitle("Modbus设置")
        self.setModal(True)
        self.resize(420, 360)

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

        self.z0_unit_input = QComboBox()
        self.z0_unit_input.addItems(["kg", "t", "10t", "100t"])
        self.z0_unit_input.setCurrentText(str(self._settings.get("z0_unit", "t")))
        form.addRow("总重量单位", self.z0_unit_input)

        self.z0_decimal_input = QSpinBox()
        self.z0_decimal_input.setRange(0, 3)
        self.z0_decimal_input.setValue(int(self._settings.get("z0_decimal", 2)))
        form.addRow("总重量小数位", self.z0_decimal_input)

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

        self.z0_unit_input.currentTextChanged.connect(self._sync_z0_decimal)
        self._sync_z0_decimal(self.z0_unit_input.currentText())

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

    def _sync_z0_decimal(self, unit: str) -> None:
        if unit in {"10t", "100t"}:
            self.z0_decimal_input.setValue(0)
            self.z0_decimal_input.setEnabled(False)
        else:
            self.z0_decimal_input.setEnabled(True)

    def _on_save(self) -> None:
        port = self.port_input.text().strip() or DEFAULT_SETTINGS["instrument_port"]
        data: Dict[str, Any] = {
            "instrument_port": port,
            "instrument_address": int(self.address_input.value()),
            "baudrate": int(self.baudrate_input.value()),
            "parity": str(self.parity_input.currentText()).upper(),
            "stopbits": int(self.stopbits_input.currentText()),
            "bytesize": int(self.bytesize_input.currentText()),
            "timeout_s": float(self.timeout_input.value()),
            "byte_order": str(self.byte_order_input.currentText()).upper(),
            "z0_unit": str(self.z0_unit_input.currentText()),
            "z0_decimal": int(self.z0_decimal_input.value()),
            "load_sign": -1 if int(self.load_sign_input.currentIndex()) == 1 else 1,
            "load_offset": float(self.load_offset_input.value()),
            "load_clamp_zero": bool(self.load_clamp_zero_input.isChecked()),
        }
        if data["z0_unit"] in {"10t", "100t"}:
            data["z0_decimal"] = 0
        save_modbus_settings(data)
        self._settings = dict(data)
        self.accept()

    def settings(self) -> Dict[str, Any]:
        return dict(self._settings)


class ModbusPage:
    def __init__(self):
        self.page = QWidget()
        self.page.setStyleSheet("background-color: #f5f7fa;")

        self._settings = load_modbus_settings()
        self._client: Optional[_RTUModbusClient] = None
        self._last_io_error = ""
        self._last_load_diag_at = 0.0
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_once)

        root = QVBoxLayout(self.page)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        toolbar = QFrame()
        toolbar.setStyleSheet("QFrame { background: white; border: none; border-radius: 10px; }")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 10, 14, 10)
        toolbar_layout.setSpacing(10)

        self.connect_btn = QPushButton("连接")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.setStyleSheet(
            "QPushButton { background: #1677ff; color: white; border: none; border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background: #4096ff; }"
        )
        self.connect_btn.clicked.connect(self._toggle_connect)

        self.status_label = QLabel("未连接")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedWidth(84)
        self.status_label.setStyleSheet("background: #fff2e8; color: #d4380d; border: none; border-radius: 8px; padding: 6px 10px;")

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet(
            "QPushButton { background: #f0f0f0; color: #333; border: none; border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background: #e6f4ff; color: #1677ff; }"
        )
        self.settings_btn.clicked.connect(self._open_settings)

        toolbar_layout.addWidget(self.connect_btn)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.settings_btn)
        root.addWidget(toolbar)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        root.addLayout(grid)

        self.flow_card = self._make_card("实时流量", "t/h")
        self.load_card = self._make_card("实时载荷", "kg/m")
        self.speed_card = self._make_card("实时速度", "m/s")
        self.total_weight_card = self._make_card("总重量", self._total_weight_display_unit())

        grid.addWidget(self.flow_card["frame"], 0, 0)
        grid.addWidget(self.load_card["frame"], 0, 1)
        grid.addWidget(self.speed_card["frame"], 1, 0)
        grid.addWidget(self.total_weight_card["frame"], 1, 1)
        grid.setRowStretch(2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._set_values(None, None, None, None, self._total_weight_display_unit())

    def get_page(self) -> QWidget:
        return self.page

    def _total_weight_display_unit(self) -> str:
        unit = str(self._settings.get("z0_unit") or "t")
        if unit in {"10t", "100t"}:
            return "t"
        return unit

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
        return

    def _set_connected_ui(self, connected: bool) -> None:
        if connected:
            self.connect_btn.setText("断开")
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("background: #f6ffed; color: #389e0d; border: none; border-radius: 8px; padding: 6px 10px;")
        else:
            self.connect_btn.setText("连接")
            self.status_label.setText("未连接")
            self.status_label.setStyleSheet("background: #fff2e8; color: #d4380d; border: none; border-radius: 8px; padding: 6px 10px;")

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
        self._log(f"正在连接 {self._settings['instrument_port']} (地址:{self._settings['instrument_address']})...")
        self._disconnect()
        self._client = self._build_client()
        ok, err = self._client.connect()
        if ok:
            self._log("通讯库: minimalmodbus")
            self._log("连接成功")
            self._last_load_diag_at = 0.0
            self._set_connected_ui(True)
            self._poll_timer.start()
            self._poll_once()
            return True
        self._log(f"连接失败: {err}")
        self._disconnect()
        return False

    def _disconnect(self) -> None:
        self._poll_timer.stop()
        if self._client is not None:
            self._log("断开连接")
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._last_io_error = ""
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
        dlg = ModbusSettingsDialog(self.page, self._settings)
        if dlg.exec_() != QDialog.Accepted:
            return
        self._settings = dlg.settings()
        self.total_weight_card["unit"].setText(self._total_weight_display_unit())
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

    def _calc_total_weight(self, int_part: int, frac_part: float) -> Tuple[float, str]:
        unit = str(self._settings.get("z0_unit") or "t")
        dec = int(self._settings.get("z0_decimal") or 0)
        if unit in {"10t", "100t"}:
            dec = 0
        raw = float(int_part) + round(float(frac_part), dec)
        if unit == "10t":
            return round(raw * 10, 0), "t"
        if unit == "100t":
            return round(raw * 100, 0), "t"
        return round(raw, dec), unit

    def _set_values(
        self,
        flow: Optional[float],
        load: Optional[float],
        speed: Optional[float],
        total_weight: Optional[float],
        total_weight_unit: str,
    ) -> None:
        self.flow_card["value"].setText("--" if flow is None else f"{flow:.2f}")
        self.load_card["value"].setText("--" if load is None else f"{load:.2f}")
        self.speed_card["value"].setText("--" if speed is None else f"{speed:.2f}")
        self.total_weight_card["value"].setText("--" if total_weight is None else f"{total_weight:g}")
        self.total_weight_card["unit"].setText(total_weight_unit)

    def _poll_once(self) -> None:
        if self._client is None or not self._client.is_connected():
            self._log("连接已断开，停止读取")
            self._disconnect()
            self._set_values(None, None, None, None, self._total_weight_display_unit())
            return

        flow = self._read_float32(50)
        load_raw = self._read_float32(52)
        speed = self._read_float32(54)
        total_int = self._read_uint32(20)
        total_frac = self._read_float32(22)

        if flow is None or load_raw is None or speed is None or total_int is None or total_frac is None:
            detail = self._last_io_error.strip()
            self._log("读取数据失败" if not detail else f"读取数据失败: {detail}")
            self._disconnect()
            self._set_values(None, None, None, None, self._total_weight_display_unit())
            return

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

        total_weight, total_unit = self._calc_total_weight(total_int, total_frac)
        self._set_values(flow, load, speed, total_weight, total_unit)
        self._log(
            f"实时流量={flow:.2f} t/h, 实时载荷={load:.2f} kg/m, 实时速度={speed:.2f} m/s, 总重量={total_weight:g} {total_unit}"
        )
