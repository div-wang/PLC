#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


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


def decode_int16(reg: int) -> int:
    v = reg & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def decode_uint16(reg: int) -> int:
    return reg & 0xFFFF


def decode_int32(regs: Sequence[int], byte_order: str = "ABCD") -> int:
    if len(regs) != 2:
        raise ValueError("int32 expects 2 registers")
    b = _u16_to_bytes_be(regs[0]) + _u16_to_bytes_be(regs[1])
    b = _reorder_4(b, byte_order)
    return struct.unpack(">i", b)[0]


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


def encode_int32(v: int, byte_order: str = "ABCD") -> Tuple[int, int]:
    b = struct.pack(">i", int(v))
    b = _reorder_4(b, byte_order)
    return ((b[0] << 8) | b[1], (b[2] << 8) | b[3])


def encode_float32(v: float, byte_order: str = "ABCD") -> Tuple[int, int]:
    b = struct.pack(">f", float(v))
    b = _reorder_4(b, byte_order)
    return ((b[0] << 8) | b[1], (b[2] << 8) | b[3])


@dataclass(frozen=True)
class JY500ConnectionSettings:
    mode: str
    unit_id: int
    timeout_s: float
    byte_order: str

    host: Optional[str] = None
    port: Optional[int] = None

    serial_port: Optional[str] = None
    baudrate: Optional[int] = None
    parity: Optional[str] = None
    stopbits: Optional[int] = None
    bytesize: Optional[int] = None

    @staticmethod
    def from_plc_settings(plc_settings: Dict[str, Any]) -> "JY500ConnectionSettings":
        device_type = (plc_settings.get("device_type") or "").strip()
        protocol = (plc_settings.get("protocol") or "").strip().lower()
        byte_order = plc_settings.get("byte_order") or "ABCD"
        timeout_ms = int(plc_settings.get("timeout", 10000))
        timeout_s = max(0.2, timeout_ms / 1000.0)

        unit_id = plc_settings.get("unit_id")
        if unit_id is None:
            unit_id = plc_settings.get("station") or plc_settings.get("address_id") or plc_settings.get("address")
        try:
            unit_id = int(unit_id) if unit_id is not None else 1
        except Exception:
            unit_id = 1
        if unit_id < 1 or unit_id > 247:
            unit_id = 1

        if device_type.upper() == "JY500B1C" and not protocol:
            protocol = "modbus_tcp"
        if protocol not in {"modbus_tcp", "modbus_rtu"}:
            protocol = "modbus_tcp"

        if protocol == "modbus_tcp":
            host = str(plc_settings.get("address") or plc_settings.get("host") or "192.168.1.101")
            port = int(plc_settings.get("port") or 502)
            return JY500ConnectionSettings(
                mode="tcp",
                unit_id=unit_id,
                timeout_s=timeout_s,
                byte_order=byte_order,
                host=host,
                port=port,
            )

        serial_port = str(plc_settings.get("serial_port") or plc_settings.get("com") or plc_settings.get("device") or "")
        baudrate = int(plc_settings.get("baudrate") or plc_settings.get("rs485_baudrate") or 9600)
        parity = str(plc_settings.get("parity") or "N").upper()
        stopbits = int(plc_settings.get("stopbits") or 1)
        bytesize = int(plc_settings.get("bytesize") or 8)
        return JY500ConnectionSettings(
            mode="rtu",
            unit_id=unit_id,
            timeout_s=timeout_s,
            byte_order=byte_order,
            serial_port=serial_port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
        )


class JY500ModbusClient:
    def __init__(self, settings: JY500ConnectionSettings):
        self.settings = settings
        self._client = None
        self._lock = threading.RLock()

    def connect(self) -> Tuple[bool, str]:
        with self._lock:
            try:
                if self.settings.mode == "tcp":
                    from pymodbus.client import ModbusTcpClient

                    self._client = ModbusTcpClient(
                        host=self.settings.host,
                        port=int(self.settings.port or 502),
                        timeout=self.settings.timeout_s,
                    )
                else:
                    from pymodbus.client import ModbusSerialClient

                    self._client = ModbusSerialClient(
                        port=self.settings.serial_port,
                        baudrate=int(self.settings.baudrate or 9600),
                        parity=str(self.settings.parity or "N"),
                        stopbits=int(self.settings.stopbits or 1),
                        bytesize=int(self.settings.bytesize or 8),
                        timeout=self.settings.timeout_s,
                    )
                ok = bool(self._client.connect())
                return ok, "" if ok else "connect failed"
            except Exception as e:
                self._client = None
                return False, str(e)

    def close(self) -> None:
        with self._lock:
            try:
                if self._client is not None:
                    self._client.close()
            finally:
                self._client = None

    def is_connected(self) -> bool:
        with self._lock:
            return self._client is not None

    def read_holding_registers(self, address: int, count: int) -> Tuple[Optional[List[int]], str]:
        with self._lock:
            if self._client is None:
                return None, "not connected"
            try:
                rr = self._client.read_holding_registers(address=int(address), count=int(count), slave=int(self.settings.unit_id))
                if rr is None:
                    return None, "empty response"
                if hasattr(rr, "isError") and rr.isError():
                    return None, str(rr)
                regs = getattr(rr, "registers", None)
                if regs is None:
                    return None, "no registers"
                return list(regs), ""
            except Exception as e:
                return None, str(e)

    def write_registers(self, address: int, values: Sequence[int]) -> Tuple[bool, str]:
        with self._lock:
            if self._client is None:
                return False, "not connected"
            try:
                rq = self._client.write_registers(address=int(address), values=[int(v) & 0xFFFF for v in values], slave=int(self.settings.unit_id))
                if rq is None:
                    return False, "empty response"
                if hasattr(rq, "isError") and rq.isError():
                    return False, str(rq)
                return True, ""
            except Exception as e:
                return False, str(e)

    def write_register(self, address: int, value: int) -> Tuple[bool, str]:
        return self.write_registers(address, [int(value) & 0xFFFF])


class JY500Poller:
    def __init__(self, client: JY500ModbusClient, refresh_interval_ms: int = 1000):
        self.client = client
        self.refresh_interval_ms = max(200, int(refresh_interval_ms))
        self._stop = threading.Event()
        self._t = None
        self._latest_lock = threading.RLock()
        self._latest: Dict[str, Any] = {"connected": False, "ts": 0, "error": "not started"}

    def start(self) -> None:
        if self._t is not None:
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, name="JY500Poller", daemon=True)
        self._t.start()

    def stop(self) -> None:
        self._stop.set()
        t = self._t
        self._t = None
        if t is not None:
            t.join(timeout=2.0)

    def latest(self) -> Dict[str, Any]:
        with self._latest_lock:
            return dict(self._latest)

    def _set_latest(self, v: Dict[str, Any]) -> None:
        with self._latest_lock:
            self._latest = dict(v)

    def _run(self) -> None:
        while not self._stop.is_set():
            ts = time.time()
            if not self.client.is_connected():
                self._set_latest({"connected": False, "ts": ts, "error": "not connected"})
                time.sleep(self.refresh_interval_ms / 1000.0)
                continue

            regs, err = self.client.read_holding_registers(31, 25)
            if regs is None:
                self._set_latest({"connected": True, "ts": ts, "error": err})
                time.sleep(self.refresh_interval_ms / 1000.0)
                continue

            bo = self.client.settings.byte_order
            try:
                alarm_raw = decode_uint32(regs[0:2], "ABCD")
                sys_jd = decode_uint16(regs[2])
                sys_status = (sys_jd >> 8) & 0xFF
                jd_status = sys_jd & 0xFF

                def i32_at(addr_offset: int) -> int:
                    i = addr_offset - 31
                    return decode_int32(regs[i : i + 2], bo)

                def f_at(addr_offset: int) -> float:
                    i = addr_offset - 31
                    return decode_float32(regs[i : i + 2], bo)

                shift1_int = i32_at(34)
                shift1_frac = f_at(36)
                shift2_int = i32_at(38)
                shift2_frac = f_at(40)
                shift3_int = i32_at(42)
                shift3_frac = f_at(44)

                batch_done = f_at(46)
                batch_left = f_at(48)
                flow_i = f_at(50)
                load_q = f_at(52)
                speed_v = f_at(54)

                self._set_latest(
                    {
                        "connected": True,
                        "ts": ts,
                        "error": "",
                        "alarm_raw": alarm_raw,
                        "sys_status": sys_status,
                        "jd_status": jd_status,
                        "shift1": float(shift1_int) + float(shift1_frac),
                        "shift2": float(shift2_int) + float(shift2_frac),
                        "shift3": float(shift3_int) + float(shift3_frac),
                        "shift1_int": shift1_int,
                        "shift1_frac": shift1_frac,
                        "shift2_int": shift2_int,
                        "shift2_frac": shift2_frac,
                        "shift3_int": shift3_int,
                        "shift3_frac": shift3_frac,
                        "batch_done": batch_done,
                        "batch_left": batch_left,
                        "flow_i": flow_i,
                        "load_q": load_q,
                        "speed_v": speed_v,
                    }
                )
            except Exception as e:
                self._set_latest({"connected": True, "ts": ts, "error": str(e)})

            time.sleep(self.refresh_interval_ms / 1000.0)

