#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from connectors.jy500_modbus import (
    JY500ConnectionSettings,
    JY500ModbusClient,
    decode_float32,
    decode_int16,
    decode_int32,
    decode_uint16,
    encode_float32,
    encode_int32,
)


@dataclass(frozen=True)
class JY500ReadResult:
    ok: bool
    error: str
    values: Dict[str, Any]


class JY500B1C:
    def __init__(self, plc_settings: Dict[str, Any]):
        self.conn_settings = JY500ConnectionSettings.from_plc_settings(plc_settings)
        self.client = JY500ModbusClient(self.conn_settings)

    def connect(self) -> Tuple[bool, str]:
        return self.client.connect()

    def close(self) -> None:
        self.client.close()

    def is_connected(self) -> bool:
        return self.client.is_connected()

    def read_registers(self, start: int, count: int) -> Tuple[Optional[List[int]], str]:
        return self.client.read_holding_registers(start, count)

    def write_registers(self, start: int, values: List[int]) -> Tuple[bool, str]:
        return self.client.write_registers(start, values)

    def write_int16(self, addr: int, v: int) -> Tuple[bool, str]:
        return self.client.write_register(addr, int(v) & 0xFFFF)

    def write_float32(self, addr: int, v: float) -> Tuple[bool, str]:
        hi, lo = encode_float32(float(v), self.conn_settings.byte_order)
        return self.client.write_registers(addr, [hi, lo])

    def write_int32(self, addr: int, v: int) -> Tuple[bool, str]:
        hi, lo = encode_int32(int(v), self.conn_settings.byte_order)
        return self.client.write_registers(addr, [hi, lo])

    def read_realtime(self) -> JY500ReadResult:
        regs, err = self.read_registers(46, 10)
        if regs is None:
            return JY500ReadResult(ok=False, error=err, values={})
        bo = self.conn_settings.byte_order
        batch_done = decode_float32(regs[0:2], bo)
        batch_left = decode_float32(regs[2:4], bo)
        flow_i = decode_float32(regs[4:6], bo)
        load_q = decode_float32(regs[6:8], bo)
        speed_v = decode_float32(regs[8:10], bo)
        return JY500ReadResult(
            ok=True,
            error="",
            values={
                "batch_done": batch_done,
                "batch_left": batch_left,
                "flow_i": flow_i,
                "load_q": load_q,
                "speed_v": speed_v,
            },
        )

    def read_shift_totals(self) -> JY500ReadResult:
        regs, err = self.read_registers(34, 12)
        if regs is None:
            return JY500ReadResult(ok=False, error=err, values={})
        bo = self.conn_settings.byte_order
        s1_int = decode_int32(regs[0:2], bo)
        s1_frac = decode_float32(regs[2:4], bo)
        s2_int = decode_int32(regs[4:6], bo)
        s2_frac = decode_float32(regs[6:8], bo)
        s3_int = decode_int32(regs[8:10], bo)
        s3_frac = decode_float32(regs[10:12], bo)
        return JY500ReadResult(
            ok=True,
            error="",
            values={
                "shift1_int": s1_int,
                "shift1_frac": s1_frac,
                "shift1": float(s1_int) + float(s1_frac),
                "shift2_int": s2_int,
                "shift2_frac": s2_frac,
                "shift2": float(s2_int) + float(s2_frac),
                "shift3_int": s3_int,
                "shift3_frac": s3_frac,
                "shift3": float(s3_int) + float(s3_frac),
            },
        )

    def read_alarm_status(self) -> JY500ReadResult:
        regs, err = self.read_registers(31, 3)
        if regs is None:
            return JY500ReadResult(ok=False, error=err, values={})
        alarm_raw = ((regs[0] & 0xFFFF) << 16) | (regs[1] & 0xFFFF)
        sys_jd = decode_uint16(regs[2])
        return JY500ReadResult(
            ok=True,
            error="",
            values={
                "alarm_raw": alarm_raw,
                "sys_status": (sys_jd >> 8) & 0xFF,
                "jd_status": sys_jd & 0xFF,
            },
        )

    def set_flow_setpoint(self, v: float) -> Tuple[bool, str]:
        return self.write_float32(12, v)

    def set_batch_setpoint(self, v: float) -> Tuple[bool, str]:
        return self.write_float32(14, v)

    def set_pid_p(self, v: float) -> Tuple[bool, str]:
        return self.write_float32(16, v)

    def set_pid_i(self, v: float) -> Tuple[bool, str]:
        return self.write_float32(18, v)

    def clear_all_totals(self) -> Tuple[bool, str]:
        return self.write_int32(20, 0)

    def set_feeder(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(24, 1 if on else 0)

    def set_pre_feeder(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(25, 1 if on else 0)

    def set_volume_mode(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(26, 1 if on else 0)

    def set_sync_volume_mode(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(27, 1 if on else 0)

    def set_batch_mode(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(28, 1 if on else 0)

    def set_full_flag(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(29, 1 if on else 0)

    def clear_event_flag(self) -> Tuple[bool, str]:
        return self.write_int16(30, 0)

    def read_comm_calibration_values(self) -> JY500ReadResult:
        regs, err = self.read_registers(80, 10)
        if regs is None:
            return JY500ReadResult(ok=False, error=err, values={})
        bo = self.conn_settings.byte_order
        load_cell_mv_v = decode_float32(regs[0:2], bo)
        tacho_hz = decode_float32(regs[2:4], bo)
        d04_tare = decode_float32(regs[4:6], bo)
        d06_pulses = decode_float32(regs[6:8], bo)
        d02_factor = decode_float32(regs[8:10], bo)
        return JY500ReadResult(
            ok=True,
            error="",
            values={
                "load_cell_mv_v": load_cell_mv_v,
                "tacho_hz": tacho_hz,
                "d04_tare": d04_tare,
                "d06_pulses": d06_pulses,
                "d02_factor": d02_factor,
            },
        )

    def set_calibration_mode(self, on: bool) -> Tuple[bool, str]:
        return self.write_int16(90, 1 if on else 0)

    def set_calibration_command(self, cmd: int) -> Tuple[bool, str]:
        return self.write_int16(91, int(cmd))

    def read_calibration_status(self) -> JY500ReadResult:
        regs, err = self.read_registers(90, 3)
        if regs is None:
            return JY500ReadResult(ok=False, error=err, values={})
        return JY500ReadResult(
            ok=True,
            error="",
            values={
                "cal_mode": decode_int16(regs[0]),
                "cal_status": decode_int16(regs[1]),
                "cal_countdown_s": decode_int16(regs[2]),
            },
        )

    def write_actual_weight(self, kg: float) -> Tuple[bool, str]:
        return self.write_float32(93, kg)

    def write_measured_weight(self, kg: float) -> Tuple[bool, str]:
        return self.write_float32(95, kg)

