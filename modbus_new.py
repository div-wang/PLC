#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import math, os, json, struct, threading, time
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPushButton, QAbstractItemView,
    QMessageBox, QSpinBox, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)
import app_storage, db

def _load_setting_root() -> Dict[str, Any]:
    try:
        path = app_storage.resource_file_path("setting.json")
        tpl = json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}
    except Exception:
        tpl = {}
    user = app_storage.load_json("setting.json", {})
    if not isinstance(user, dict): user = {}
    def merge(a, b):
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
            else: a[k] = v
        return a
    merged = merge(dict(tpl), user)
    app_storage.save_json("setting.json", merged)
    return merged

def _cleanup_logs(days: int = 30):
    try:
        base, now = app_storage.logs_dir(), datetime.now()
        for name in os.listdir(base):
            if name.endswith(".log"):
                try:
                    if (now - datetime.strptime(name[:-4], "%Y-%m-%d")).days > days:
                        os.remove(os.path.join(base, name))
                except Exception: pass
    except Exception: pass

def _append_log(text: str):
    try:
        path = os.path.join(app_storage.logs_dir(), f"{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(path, "a", encoding="utf-8") as f: f.write(text + "\n")
    except Exception: pass

def decode_bytes(regs: Sequence[int], order: str = "ABCD", fmt: str = ">I") -> Any:
    b = bytes([(regs[0] >> 8) & 0xFF, regs[0] & 0xFF, (regs[1] >> 8) & 0xFF, regs[1] & 0xFF])
    idx = {"A":0, "B":1, "C":2, "D":3}
    return struct.unpack(fmt, bytes([b[idx[ch]] for ch in order]))[0]

@dataclass(frozen=True)
class _RTUSettings:
    unit_id: int; timeout_s: float; serial_port: str; baudrate: int
    parity: str; stopbits: int; bytesize: int

class _RTUModbusClient:
    def __init__(self, s: _RTUSettings):
        self.s, self._inst, self._lock = s, None, threading.RLock()
    def connect(self) -> Tuple[bool, str]:
        with self._lock:
            try:
                import minimalmodbus
                i = minimalmodbus.Instrument(self.s.serial_port, self.s.unit_id)
                i.serial.baudrate, i.serial.bytesize = self.s.baudrate, self.s.bytesize
                i.serial.parity = {"E": "E", "O": "O"}.get(self.s.parity, "N")
                i.serial.stopbits, i.serial.timeout = self.s.stopbits, self.s.timeout_s
                i.mode, i.clear_buffers_before_each_transaction = minimalmodbus.MODE_RTU, True
                if not i.serial.is_open: i.serial.open()
                self._inst = i
                return True, ""
            except Exception as e: return False, str(e)
    def read_float32(self, addr: int, order: str) -> Tuple[Optional[float], str]:
        with self._lock:
            if not self._inst: return None, "not connected"
            try:
                bo = {"ABCD": 0, "DCBA": 1, "CDAB": 2, "BADC": 3}.get(order, 0)
                return float(self._inst.read_float(addr, 3, 2, bo)), ""
            except Exception as e: return None, str(e)
    def read_uint32(self, addr: int, order: str) -> Tuple[Optional[int], str]:
        with self._lock:
            if not self._inst: return None, "not connected"
            try:
                bo = {"ABCD": 0, "DCBA": 1, "CDAB": 2, "BADC": 3}.get(order, 0)
                return int(self._inst.read_long(addr, 3, 2, False, bo)), ""
            except Exception:
                try:
                    r = self._inst.read_registers(addr, 2, 3)
                    return int(decode_bytes(r, order, ">I")), ""
                except Exception as e: return None, str(e)
    def read_regs(self, addr: int, count: int) -> Tuple[Optional[List[int]], str]:
        with self._lock:
            if not self._inst: return None, "not connected"
            try: return self._inst.read_registers(addr, count, 3), ""
            except Exception as e: return None, str(e)
    def close(self):
        with self._lock:
            if self._inst and getattr(self._inst, "serial", None) and self._inst.serial.is_open:
                try: self._inst.serial.close()
                except Exception: pass
            self._inst = None
    def is_connected(self) -> bool:
        with self._lock: return self._inst is not None

DEFAULT_SETTINGS = {
    "instrument_port": "COM1", "instrument_address": 1, "baudrate": 9600,
    "bytesize": 8, "parity": "N", "stopbits": 1, "timeout_s": 1.0,
    "byte_order": "ABCD", "load_sign": 1, "load_offset": 0.0,
    "load_clamp_zero": False, "scale": 1.0, "sample_save_interval_s": 5,
}

def load_modbus_settings() -> Dict[str, Any]:
    raw = _load_setting_root().get("modbus", {})
    m = {**DEFAULT_SETTINGS, **(raw if isinstance(raw, dict) else {})}
    m["load_sign"] = -1 if int(m.get("load_sign", 1)) < 0 else 1
    return m

def save_modbus_settings(data: Dict[str, Any]):
    root = _load_setting_root()
    root["modbus"] = data
    app_storage.save_json("setting.json", root)

def _active_project_id() -> str:
    raw = app_storage.load_json("project.json", [])
    if isinstance(raw, list) and raw:
        for p in raw:
            if isinstance(p, dict) and p.get("is_active"): return str(p.get("name_en") or p.get("name_cn") or "default")
        if isinstance(raw[0], dict): return str(raw[0].get("name_en") or raw[0].get("name_cn") or "default")
    return "default"

class ModbusSettingsDialog(QDialog):
    def __init__(self, parent, settings, is_admin):
        super().__init__(parent)
        self.s, self.is_admin = dict(settings), is_admin
        self.setWindowTitle("Modbus设置"); self.resize(420, 420)
        layout = QVBoxLayout(self); form = QFormLayout(); layout.addLayout(form)
        self.w = {}
        def add(k, label, w): form.addRow(label, w); self.w[k] = w
        
        w_port = QLineEdit(str(self.s.get("instrument_port", "COM1")))
        add("instrument_port", "COM口", w_port)
        w_addr = QSpinBox(); w_addr.setRange(1, 247); w_addr.setValue(int(self.s.get("instrument_address", 1)))
        add("instrument_address", "通讯地址", w_addr)
        w_baud = QSpinBox(); w_baud.setRange(300, 115200); w_baud.setValue(int(self.s.get("baudrate", 9600)))
        add("baudrate", "波特率", w_baud)
        w_par = QComboBox(); w_par.addItems(["N", "E", "O"]); w_par.setCurrentText(self.s.get("parity", "N"))
        add("parity", "校验位", w_par)
        w_stop = QComboBox(); w_stop.addItems(["1", "2"]); w_stop.setCurrentText(str(self.s.get("stopbits", 1)))
        add("stopbits", "停止位", w_stop)
        w_byte = QComboBox(); w_byte.addItems(["7", "8"]); w_byte.setCurrentText(str(self.s.get("bytesize", 8)))
        add("bytesize", "数据位", w_byte)
        w_to = QDoubleSpinBox(); w_to.setRange(0.2, 30.0); w_to.setValue(float(self.s.get("timeout_s", 1.0)))
        add("timeout_s", "超时(s)", w_to)
        w_bo = QComboBox(); w_bo.addItems(["ABCD", "BADC", "CDAB", "DCBA"]); w_bo.setCurrentText(self.s.get("byte_order", "ABCD"))
        add("byte_order", "字节序", w_bo)
        w_sign = QComboBox(); w_sign.addItems(["正常", "取反"]); w_sign.setCurrentIndex(1 if int(self.s.get("load_sign", 1)) < 0 else 0)
        add("load_sign", "载荷符号", w_sign)
        w_off = QDoubleSpinBox(); w_off.setRange(-1000000, 1000000); w_off.setDecimals(3); w_off.setValue(float(self.s.get("load_offset", 0.0)))
        add("load_offset", "载荷偏移", w_off)
        w_clamp = QCheckBox("载荷小于0时置为0"); w_clamp.setChecked(bool(self.s.get("load_clamp_zero", False)))
        add("load_clamp_zero", "", w_clamp)
        w_intv = QSpinBox(); w_intv.setRange(0, 86400); w_intv.setValue(int(self.s.get("sample_save_interval_s", 5)))
        add("sample_save_interval_s", "保存间隔(s)", w_intv)
        
        if self.is_admin:
            w_scale = QDoubleSpinBox(); w_scale.setRange(0, 1000000); w_scale.setDecimals(6); w_scale.setValue(float(self.s.get("scale", 1.0)))
            add("scale", "总重量比例", w_scale)
            
        btn_box = QHBoxLayout(); layout.addLayout(btn_box); btn_box.addStretch(1)
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject); btn_box.addWidget(btn_cancel)
        btn_save = QPushButton("保存"); btn_save.setDefault(True); btn_save.clicked.connect(self.save); btn_box.addWidget(btn_save)

    def save(self):
        self.s.update({
            "instrument_port": self.w["instrument_port"].text() or "COM1",
            "instrument_address": self.w["instrument_address"].value(),
            "baudrate": self.w["baudrate"].value(),
            "parity": self.w["parity"].currentText(),
            "stopbits": int(self.w["stopbits"].currentText()),
            "bytesize": int(self.w["bytesize"].currentText()),
            "timeout_s": self.w["timeout_s"].value(),
            "byte_order": self.w["byte_order"].currentText(),
            "load_sign": -1 if self.w["load_sign"].currentIndex() == 1 else 1,
            "load_offset": self.w["load_offset"].value(),
            "load_clamp_zero": self.w["load_clamp_zero"].isChecked(),
            "sample_save_interval_s": self.w["sample_save_interval_s"].value()
        })
        if self.is_admin: self.s["scale"] = self.w["scale"].value()
        save_modbus_settings(self.s)
        self.accept()

class ModbusPage:
    def __init__(self, user_role="user"):
        self.page = QWidget(); self.page.setStyleSheet("background-color: #f5f7fa;")
        try: db.init_db(); db.migrate_ring_records_json_if_needed()
        except Exception: pass
        _cleanup_logs(30)
        self.s = load_modbus_settings(); self.role = user_role
        self.cli, self.last_err, self.travel_tot = None, "", 0.0
        self.ring_no, self.ring_wt = 0, 0.0
        self.last_tot_wt, self.active_pid = None, _active_project_id()
        self.last_poll, self.last_save = 0.0, 0.0
        self.timer = QTimer(); self.timer.setInterval(1000); self.timer.timeout.connect(self.poll)
        self.cb_status, self.cb_ring, self.cb_clr = None, None, None
        self.auto_conn, self.auto_att = False, 0
        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        vbox = QVBoxLayout(self.page); vbox.setContentsMargins(18, 18, 18, 18); vbox.setSpacing(14)
        
        tb = QFrame(); tb.setStyleSheet("background: white; border-radius: 10px;")
        hbox = QHBoxLayout(tb); hbox.setContentsMargins(14, 10, 14, 10)
        self.lbl_st = QLabel("未连接"); self.lbl_st.setFixedWidth(110); self.lbl_st.setAlignment(Qt.AlignCenter)
        self.set_st_ui(False)
        hbox.addWidget(self.lbl_st); hbox.addStretch(1)
        
        btn_style = "QPushButton { border: none; border-radius: 8px; padding: 8px 14px; }"
        self.btn_fix = QPushButton("修正环号"); self.btn_fix.setStyleSheet(btn_style + "background: #e6f4ff; color: #1677ff;")
        self.btn_fix.setVisible(self.role == "admin"); self.btn_fix.clicked.connect(self.fix_ring)
        self.btn_clr = QPushButton("清空数据"); self.btn_clr.setStyleSheet(btn_style + "background: #fff1f0; color: #cf1322;")
        self.btn_clr.setVisible(self.role == "admin"); self.btn_clr.clicked.connect(self.clr_ring)
        self.btn_set = QPushButton("设置"); self.btn_set.setStyleSheet(btn_style + "background: #f0f0f0; color: #333;")
        self.btn_set.clicked.connect(self.open_set)
        for b in [self.btn_fix, self.btn_clr, self.btn_set]: hbox.addWidget(b)
        vbox.addWidget(tb)

        rf = QFrame(); rf.setStyleSheet("background: white; border-radius: 12px;")
        rv = QVBoxLayout(rf); rv.setContentsMargins(14, 12, 14, 12)
        rt = QHBoxLayout(); rv.addLayout(rt)
        t_lbl = QLabel("环号记录"); t_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        rt.addWidget(t_lbl); rt.addStretch(1)
        self.lbl_pg = QLabel(""); rt.addWidget(self.lbl_pg)
        
        pg_btn_st = "QPushButton { background: #f3f4f6; border-radius: 8px; padding: 6px 10px; }"
        self.btn_prv = QPushButton("上一页"); self.btn_prv.setStyleSheet(pg_btn_st); self.btn_prv.clicked.connect(lambda: self.chg_pg(-1))
        self.btn_nxt = QPushButton("下一页"); self.btn_nxt.setStyleSheet(pg_btn_st); self.btn_nxt.clicked.connect(lambda: self.chg_pg(1))
        rt.addWidget(self.btn_prv); rt.addWidget(self.btn_nxt)
        
        self.tbl = QTableWidget(0, 4); self.tbl.setHorizontalHeaderLabels(["环号", "重量", "总重量", "时间"])
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.horizontalHeader().setStretchLastSection(True); self.tbl.verticalHeader().setVisible(False)
        self.tbl.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 10px;")
        rv.addWidget(self.tbl); vbox.addWidget(rf, 2)

        lf = QFrame(); lf.setStyleSheet("background: white; border-radius: 12px;")
        lv = QVBoxLayout(lf); lf.setContentsMargins(14, 12, 14, 12)
        self.log_txt = QTextEdit(); self.log_txt.setReadOnly(True)
        self.log_txt.setStyleSheet("background: #0b1220; color: #d1d5db; font-family: Consolas; border-radius: 10px;")
        lv.addWidget(self.log_txt); vbox.addWidget(lf, 1)
        self.pg, self.pg_sz = 1, 10
        self.update_state(None, None, None, None)

    def get_page(self): return self.page
    def warn(self, msg): QTimer.singleShot(0, lambda: QMessageBox.warning(self.page, "提示", msg))
    def log(self, msg):
        txt = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        _append_log(txt); self.log_txt.append(txt)
    def confirm(self, msg): return QMessageBox.warning(self.page, "确认", msg, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes

    def set_user_role(self, role):
        self.role = role; self.btn_fix.setVisible(role == "admin"); self.btn_clr.setVisible(role == "admin")
    def set_status_callback(self, cb): self.cb_status = cb
    def set_ring_callback(self, cb):
        self.cb_ring = cb; n = db.max_ring_no(_active_project_id())
        if n is not None: self.ring_no = n
        if self.cb_ring: self.cb_ring(self.ring_no)
    def set_clear_ring_callback(self, cb): self.cb_clr = cb

    def emit_st(self, st):
        self.set_st_ui(st == "connected" if st in ("connected", "failed") else None)
        if self.cb_status: self.cb_status(st)
    def set_st_ui(self, conn):
        if conn is True:
            self.lbl_st.setText("已连接"); self.lbl_st.setStyleSheet("background: #f6ffed; color: #389e0d; padding: 6px; border-radius: 8px;")
        elif conn is False:
            self.lbl_st.setText("未连接"); self.lbl_st.setStyleSheet("background: #fff2e8; color: #d4380d; padding: 6px; border-radius: 8px;")
        else:
            self.lbl_st.setText("连接中"); self.lbl_st.setStyleSheet("background: #f5f5f5; color: #595959; padding: 6px; border-radius: 8px;")

    def chg_pg(self, d): self.pg = max(1, self.pg + d); self.refresh_table()
    def refresh_table(self):
        try:
            recs = db.recent_rings(_active_project_id(), 1000)
            recs.sort(key=lambda x: x.get("ring_no", 0), reverse=True)
            tot = len(recs); t_pgs = max(1, (tot + self.pg_sz - 1) // self.pg_sz)
            self.pg = max(1, min(self.pg, t_pgs))
            rows = recs[(self.pg-1)*self.pg_sz : self.pg*self.pg_sz]
            self.tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.tbl.setItem(i, 0, QTableWidgetItem(str(r.get("ring_no", ""))))
                self.tbl.setItem(i, 1, QTableWidgetItem(f"{r.get('weight', 0):.3f}"))
                self.tbl.setItem(i, 2, QTableWidgetItem(f"{r.get('total_weight', 0):.3f}"))
                self.tbl.setItem(i, 3, QTableWidgetItem(r.get("time", "")))
                for j in range(4): self.tbl.item(i, j).setTextAlignment(Qt.AlignCenter)
            self.lbl_pg.setText(f"第 {self.pg}/{t_pgs} 页 ({tot} 条)")
            self.btn_prv.setEnabled(self.pg > 1); self.btn_nxt.setEnabled(self.pg < t_pgs)
        except Exception: pass

    def prev_ring(self):
        if not self.confirm("一旦切换上一环，当前环将被删除"): return
        pid = _active_project_id(); recs = db.recent_rings(pid, 100)
        if len(recs) < 2: return self.warn("没有上一环")
        recs.sort(key=lambda x: x.get("ring_no", 0))
        cur, prv = recs[-1], recs[-2]
        db.upsert_ring_detail(pid, prv["ring_no"], prv.get("weight",0)+cur.get("weight",0), prv.get("travel",0)+cur.get("travel",0), cur.get("time",""), cur.get("total_weight",0), cur.get("total_travel",0))
        db.delete_ring_detail(pid, cur["ring_no"])
        self.ring_no = db.max_ring_no(pid) or prv["ring_no"]
        if self.cb_ring: self.cb_ring(self.ring_no)
        self.log(f"上一环: 删 {cur['ring_no']} 累加至 {self.ring_no}"); self.refresh_table()

    def next_ring(self):
        if not self.cli or not self.cli.is_connected(): return self.warn("Modbus未连接")
        if self.last_tot_wt is None: return self.warn("尚未读取到总重量")
        if self.ring_wt <= 1.0: return self.warn("当前环重量≤1t，不可切换")
        pid = _active_project_id()
        prev_trv = db.get_ring_detail(pid, self.ring_no - 1).get("total_travel", 0) if self.ring_no > 0 else 0
        db.upsert_ring_detail(pid, self.ring_no, self.ring_wt, self.travel_tot - prev_trv, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.last_tot_wt, self.travel_tot)
        db.upsert_ring_detail(pid, self.ring_no + 1, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.last_tot_wt, self.travel_tot)
        self.ring_no = db.max_ring_no(pid) or self.ring_no + 1
        if self.cb_ring: self.cb_ring(self.ring_no)
        self.log(f"下一环: 新建环号={self.ring_no}"); self.refresh_table()

    def clr_ring(self):
        if self.role != "admin" or not self.confirm("确认清空环号数据？将自动备份数据库"): return
        try:
            db.backup_and_recreate_db(); self.ring_no, self.ring_wt, self.travel_tot, self.last_tot_wt = 0, 0, 0, None
            if self.cb_ring: self.cb_ring(0)
            if self.cb_clr: self.cb_clr()
            self.warn("数据已清空"); self.refresh_table()
        except Exception as e: self.warn(f"清空失败: {e}")

    def fix_ring(self):
        if self.role != "admin": return
        pid = _active_project_id(); mx = db.max_ring_no(pid) or 0
        tg, ok = QInputDialog.getInt(self.page, "修正", f"当前最大:{mx}\n目标(>{mx}):", min=mx+1, max=99999)
        if not ok or not self.confirm(f"修正到{tg}环，补全重量为0?"): return
        state = json.loads(db.meta_get("modbus_state::data") or "{}")
        tot_wt = state.get("device_total_weight", db.get_ring_detail(pid, mx).get("total_weight", 0) if mx>0 else 0)
        with db._connect() as c:
            for n in range(mx+1, tg+1): c.execute("INSERT INTO ring_detail(project_id,ring_no,weight,travel,time,total_weight,total_travel) VALUES(?,?,0,0,?,?,0)", (pid, n, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tot_wt))
            c.commit()
        self.ring_no = tg
        if self.cb_ring: self.cb_ring(tg)
        if self.cb_clr: self.cb_clr()
        self.warn("修正成功"); self.refresh_table()

    def start_auto_connect(self, max_att=3, intv=500):
        if self.auto_conn: return
        self.auto_conn, self.auto_att, self.auto_intv = True, 0, max(100, intv)
        self.emit_st("connecting")
        QTimer.singleShot(0, lambda: self._auto_conn_step(max_att))
    def _auto_conn_step(self, max_att):
        if not self.auto_conn: return
        if self.cli and self.cli.is_connected() or self.connect():
            self.emit_st("connected"); self.auto_conn = False; return
        self.auto_att += 1
        if self.auto_att >= max_att: self.emit_st("failed"); self.auto_conn = False; return
        self.emit_st("connecting"); QTimer.singleShot(self.auto_intv, lambda: self._auto_conn_step(max_att))

    def connect(self):
        self.log(f"连接 {self.s.get('instrument_port')} (地址:{self.s.get('instrument_address')})")
        self.disconnect()
        self.cli = _RTUModbusClient(_RTUSettings(self.s["instrument_address"], self.s["timeout_s"], self.s["instrument_port"], self.s["baudrate"], self.s["parity"], self.s["stopbits"], self.s["bytesize"]))
        ok, err = self.cli.connect()
        if ok:
            self.travel_tot, self.last_poll = 0.0, 0.0
            pid = _active_project_id(); self.ring_no = db.max_ring_no(pid) or 0
            if self.cb_ring: self.cb_ring(self.ring_no)
            self.timer.start(); self.poll(); self.emit_st("connected"); self.log("已连接")
            return True
        self.log(f"连接失败: {err}"); return False

    def disconnect(self):
        self.timer.stop(); self.emit_st("failed")
        if self.cli: self.cli.close()
        self.cli = None; self.update_state(None, None, None, None)

    def open_set(self):
        d = ModbusSettingsDialog(self.page, self.s, self.role == "admin")
        if d.exec_() == QDialog.Accepted:
            self.s = d.s
            if self.cli and self.cli.is_connected(): self.connect()

    def update_state(self, flow, load, spd, tot):
        db.meta_set("modbus_state::data", json.dumps({
            "project_id": _active_project_id(), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "flow": flow, "flow_unit": "t/h", "load": load, "speed": spd, "speed_unit": "m/s",
            "total_weight": tot, "total_weight_unit": "t", "travel_total": self.travel_tot,
            "ring_no": self.ring_no, "device_total_weight": self.last_tot_wt
        }, ensure_ascii=False))

    def poll(self):
        pid = _active_project_id()
        if pid != self.active_pid: self.active_pid, self.pg = pid, 1; self.refresh_table()
        if not self.cli or not self.cli.is_connected(): return self.disconnect()
        
        f = self.cli.read_float32(50, self.s["byte_order"])[0]
        ld = self.cli.read_float32(52, self.s["byte_order"])[0]
        sp = self.cli.read_float32(54, self.s["byte_order"])[0]
        tot = self.cli.read_float32(46, self.s["byte_order"])[0]
        
        if None in (f, ld, sp, tot):
            self.log("读取失败"); self.disconnect()
            if not self.auto_conn: self.start_auto_connect(5, 2000)
            return

        now = time.monotonic()
        if self.last_poll > 0 and 0 < now - self.last_poll < 5: self.travel_tot += max(0, sp) * (now - self.last_poll)
        self.last_poll = now

        ld = (ld + self.s.get("load_offset", 0.0)) * self.s.get("load_sign", 1)
        if self.s.get("load_clamp_zero") and ld < 0: ld = 0.0
        
        f *= self.s.get("scale", 1.0); tot *= self.s.get("scale", 1.0)
        self.last_tot_wt = tot
        
        if db.get_ring_detail(pid, 0) is None: db.upsert_ring_detail(pid, 0, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 0)
        self.ring_no = db.max_ring_no(pid) or 0
        
        prv_sum = float(db.sum_ring_weight_before(pid, self.ring_no) if self.ring_no > 0 else db.meta_get(f"ring0_baseline_total_weight::{pid}") or tot)
        if self.ring_no == 0 and db.meta_get(f"ring0_baseline_total_weight::{pid}") is None: db.meta_set(f"ring0_baseline_total_weight::{pid}", str(tot))
        
        self.ring_wt = max(0, tot - prv_sum)
        if self.cb_ring: self.cb_ring(self.ring_no)
        self.update_state(f, ld, sp, self.ring_wt)
        self.emit_st("connected")
        
        if now - self.last_save >= self.s.get("sample_save_interval_s", 5):
            self.last_save = now
            db.upsert_ring_detail(pid, self.ring_no, self.ring_wt, self.travel_tot - (db.get_ring_detail(pid, self.ring_no - 1).get("total_travel", 0) if self.ring_no > 0 else 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tot, self.travel_tot)
