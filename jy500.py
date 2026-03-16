#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, QUrl, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView

import app_storage

from connectors.jy500_api import JY500B1C
from connectors.jy500_modbus import JY500Poller


def _load_active_plc_settings() -> Dict[str, Any]:
    default_settings = {
        "device_type": "JY500B1C",
        "protocol": "modbus_tcp",
        "byte_order": "ABCD",
        "timeout": 10000,
        "refresh_interval_ms": 1000,
        "address": "192.168.1.101",
        "port": 502,
        "unit_id": 1,
        "serial_port": "",
        "baudrate": 9600,
        "parity": "N",
        "stopbits": 1,
        "bytesize": 8,
    }

    projects = app_storage.load_json("project.json", [])
    if isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict) and p.get("is_active"):
                return {**default_settings, **p.get("plc_settings", {})}
        if projects and isinstance(projects[0], dict):
            return {**default_settings, **projects[0].get("plc_settings", {})}
    return default_settings


class JY500Page:
    def __init__(self):
        self.page = QWebEngineView()
        self.bridge = JY500Bridge()
        self.channel = QWebChannel(self.page.page())
        self.channel.registerObject("bridge", self.bridge)
        self.page.page().setWebChannel(self.channel)
        self.generate_page()

    def get_page(self):
        return self.page

    def generate_page(self):
        settings = _load_active_plc_settings()
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>JY500B1C 连接器</title>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f9f9f9; }
                .card { background: white; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); padding: 16px; margin-bottom: 12px; }
                .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
                .title { font-size: 18px; font-weight: 700; color: #222; }
                .muted { color: #777; font-size: 12px; }
                .btn { background: #1890ff; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; }
                .btn.secondary { background: #444; }
                .btn.warn { background: #d4380d; }
                .btn:disabled { opacity: 0.55; cursor: not-allowed; }
                .tabs { display: flex; gap: 8px; margin-top: 10px; }
                .tab { padding: 8px 12px; border-radius: 4px; cursor: pointer; background: #f0f2f5; color: #333; }
                .tab.active { background: #1890ff; color: white; }
                .panel { display: none; margin-top: 12px; }
                .panel.active { display: block; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #eee; padding: 8px; font-size: 13px; }
                th { background: #fafafa; text-align: left; }
                input, select { padding: 6px 8px; border: 1px solid #d9d9d9; border-radius: 4px; height: 32px; }
                .kpi { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
                .kpi .item { background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 10px; }
                .kpi .v { font-size: 20px; font-weight: 700; color: #111; }
                .kpi .l { font-size: 12px; color: #666; margin-top: 2px; }
                .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
                .log { font-family: Menlo, monospace; font-size: 12px; background: #0b1020; color: #d7e3ff; padding: 10px; border-radius: 6px; min-height: 88px; white-space: pre-wrap; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="row">
                    <div style="flex: 1;">
                        <div class="title">JY500B1C 连接器</div>
                        <div class="muted">协议：Modbus-RTU / Modbus-TCP（按说明书：03/06/10 功能码，CCITT-16/N）</div>
                    </div>
                    <button class="btn" id="btnConnect">连接</button>
                    <button class="btn secondary" id="btnDisconnect">断开</button>
                </div>
                <div class="row" style="margin-top: 10px;">
                    <div class="muted" id="connInfo"></div>
                    <div class="muted" id="connState"></div>
                </div>
            </div>

            <div class="card">
                <div class="tabs">
                    <div class="tab active" data-tab="tab_runtime">运行数据</div>
                    <div class="tab" data-tab="tab_control">控制</div>
                    <div class="tab" data-tab="tab_cal">通讯校验</div>
                    <div class="tab" data-tab="tab_regs">寄存器</div>
                </div>

                <div class="panel active" id="tab_runtime">
                    <div class="kpi">
                        <div class="item"><div class="v" id="k_flow">--</div><div class="l">实时流量 I</div></div>
                        <div class="item"><div class="v" id="k_load">--</div><div class="l">实时载荷 Q</div></div>
                        <div class="item"><div class="v" id="k_speed">--</div><div class="l">实时速度 V</div></div>
                    </div>
                    <div class="kpi" style="grid-template-columns: repeat(3, minmax(0, 1fr));">
                        <div class="item"><div class="v" id="k_batch_done">--</div><div class="l">此批已下料量</div></div>
                        <div class="item"><div class="v" id="k_batch_left">--</div><div class="l">此批剩余料量</div></div>
                        <div class="item"><div class="v" id="k_alarm_raw">--</div><div class="l">报警/状态原始值</div></div>
                    </div>
                    <div class="grid2" style="margin-top: 10px;">
                        <div>
                            <table>
                                <thead><tr><th>项目</th><th>值</th></tr></thead>
                                <tbody>
                                    <tr><td>一班累重</td><td id="t_shift1">--</td></tr>
                                    <tr><td>二班累重</td><td id="t_shift2">--</td></tr>
                                    <tr><td>三班累重</td><td id="t_shift3">--</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <div>
                            <div class="log" id="logBox"></div>
                        </div>
                    </div>
                </div>

                <div class="panel" id="tab_control">
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">P 流量设定</div>
                        <input id="inpFlow" type="number" step="0.01" style="width: 180px;">
                        <button class="btn" id="btnSetFlow">写入</button>
                    </div>
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">Zb 批量设定</div>
                        <input id="inpBatch" type="number" step="0.01" style="width: 180px;">
                        <button class="btn" id="btnSetBatch">写入</button>
                    </div>
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">PID P / I</div>
                        <input id="inpPidP" type="number" step="0.001" style="width: 120px;">
                        <input id="inpPidI" type="number" step="0.001" style="width: 120px;">
                        <button class="btn" id="btnSetPid">写入</button>
                    </div>
                    <div class="row" style="margin-top: 12px; gap: 8px;">
                        <button class="btn" id="btnFeederOn">给料机启动</button>
                        <button class="btn secondary" id="btnFeederOff">给料机停止</button>
                        <button class="btn" id="btnPreFeederOn">预给料机启动</button>
                        <button class="btn secondary" id="btnPreFeederOff">预给料机停止</button>
                    </div>
                    <div class="row" style="margin-top: 10px; gap: 8px;">
                        <button class="btn" id="btnVolOn">体积模式启动</button>
                        <button class="btn secondary" id="btnVolOff">体积模式停止</button>
                        <button class="btn" id="btnSyncVolOn">同步体积启动</button>
                        <button class="btn secondary" id="btnSyncVolOff">同步体积停止</button>
                        <button class="btn" id="btnBatchModeOn">批次模式启动</button>
                        <button class="btn secondary" id="btnBatchModeOff">批次模式停止</button>
                    </div>
                    <div class="row" style="margin-top: 10px; gap: 8px;">
                        <button class="btn warn" id="btnClearTotals">清零所有累重</button>
                        <button class="btn warn" id="btnClearEvents">清事件标志</button>
                    </div>
                </div>

                <div class="panel" id="tab_cal">
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">校验模式</div>
                        <select id="selCalMode" style="width: 180px;">
                            <option value="1">进入</option>
                            <option value="0">退出</option>
                        </select>
                        <button class="btn" id="btnSetCalMode">写入</button>
                    </div>
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">校验命令</div>
                        <input id="inpCalCmd" type="number" step="1" style="width: 180px;" placeholder="100/200/300/400/430/450/500">
                        <button class="btn" id="btnSetCalCmd">写入</button>
                        <button class="btn secondary" id="btnReadCal">读取状态</button>
                    </div>
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">输入实际重量</div>
                        <input id="inpActualKg" type="number" step="0.01" style="width: 180px;">
                        <button class="btn" id="btnWriteActualKg">写入</button>
                    </div>
                    <div class="row" style="margin-bottom: 8px;">
                        <div style="width: 140px;">输入表测重量</div>
                        <input id="inpMeasuredKg" type="number" step="0.01" style="width: 180px;">
                        <button class="btn" id="btnWriteMeasuredKg">写入</button>
                    </div>
                    <div class="grid2" style="margin-top: 10px;">
                        <div>
                            <table>
                                <thead><tr><th>项目</th><th>值</th></tr></thead>
                                <tbody>
                                    <tr><td>称重传感器信号(mV/V)</td><td id="cal_load_cell">--</td></tr>
                                    <tr><td>测速信号频率(Hz)</td><td id="cal_tacho">--</td></tr>
                                    <tr><td>D04 基础皮重(Kg/m)</td><td id="cal_d04">--</td></tr>
                                    <tr><td>D06 周期脉冲数(I/U)</td><td id="cal_d06">--</td></tr>
                                    <tr><td>D02 标定系数</td><td id="cal_d02">--</td></tr>
                                    <tr><td>倒计时(s)</td><td id="cal_cd">--</td></tr>
                                    <tr><td>状态码</td><td id="cal_status">--</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="log" id="calLog"></div>
                    </div>
                </div>

                <div class="panel" id="tab_regs">
                    <div class="row" style="margin-bottom: 10px;">
                        <div style="width: 140px;">读寄存器</div>
                        <input id="inpRegStart" type="number" step="1" style="width: 120px;" value="0">
                        <input id="inpRegCount" type="number" step="1" style="width: 120px;" value="16">
                        <button class="btn" id="btnReadRegs">读取</button>
                    </div>
                    <table>
                        <thead><tr><th>地址</th><th>值(DEC)</th><th>值(HEX)</th></tr></thead>
                        <tbody id="regsBody"></tbody>
                    </table>
                </div>
            </div>

            <script>
                function fmt(v) {
                    if (v === null || v === undefined) return '--';
                    if (typeof v === 'number' && isFinite(v)) return v.toFixed(3);
                    return String(v);
                }
                function log(msg) {
                    var el = document.getElementById('logBox');
                    el.textContent = (new Date()).toLocaleTimeString() + ' ' + msg + '\\n' + el.textContent;
                }
                function logCal(msg) {
                    var el = document.getElementById('calLog');
                    el.textContent = (new Date()).toLocaleTimeString() + ' ' + msg + '\\n' + el.textContent;
                }
                function setConnInfo(s) {
                    document.getElementById('connInfo').textContent = s;
                }
                function setConnState(s) {
                    document.getElementById('connState').textContent = s;
                }
                function activateTab(tabId) {
                    document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
                    document.querySelectorAll('.panel').forEach(function(p){ p.classList.remove('active'); });
                    document.querySelector('.tab[data-tab=\"' + tabId + '\"]').classList.add('active');
                    document.getElementById(tabId).classList.add('active');
                }
                document.querySelectorAll('.tab').forEach(function(t){
                    t.addEventListener('click', function(){ activateTab(this.getAttribute('data-tab')); });
                });

                var bridge = null;
                function updateButtons(connected) {
                    document.getElementById('btnConnect').disabled = connected;
                    document.getElementById('btnDisconnect').disabled = !connected;
                }

                function renderRegs(start, regs) {
                    var body = document.getElementById('regsBody');
                    body.innerHTML = '';
                    for (var i=0;i<regs.length;i++) {
                        var v = regs[i] >>> 0;
                        var tr = document.createElement('tr');
                        var td0 = document.createElement('td'); td0.textContent = String(start + i);
                        var td1 = document.createElement('td'); td1.textContent = String(v);
                        var td2 = document.createElement('td'); td2.textContent = '0x' + v.toString(16).padStart(4,'0').toUpperCase();
                        tr.appendChild(td0); tr.appendChild(td1); tr.appendChild(td2);
                        body.appendChild(tr);
                    }
                }

                function tick() {
                    if (!bridge) return;
                    var snap = bridge.getSnapshot();
                    if (!snap) return;
                    var s = null;
                    try { s = JSON.parse(snap); } catch(e) { return; }
                    updateButtons(!!s.connected);
                    if (!s.connected) {
                        setConnState('未连接 ' + (s.error ? ('(' + s.error + ')') : ''));
                        return;
                    }
                    setConnState('已连接 ' + (s.error ? ('(' + s.error + ')') : ''));
                    if (!s.error) {
                        document.getElementById('k_flow').textContent = fmt(s.flow_i);
                        document.getElementById('k_load').textContent = fmt(s.load_q);
                        document.getElementById('k_speed').textContent = fmt(s.speed_v);
                        document.getElementById('k_batch_done').textContent = fmt(s.batch_done);
                        document.getElementById('k_batch_left').textContent = fmt(s.batch_left);
                        document.getElementById('k_alarm_raw').textContent = '0x' + (s.alarm_raw >>> 0).toString(16).toUpperCase();
                        document.getElementById('t_shift1').textContent = fmt(s.shift1);
                        document.getElementById('t_shift2').textContent = fmt(s.shift2);
                        document.getElementById('t_shift3').textContent = fmt(s.shift3);
                    }
                }

                function refreshCal() {
                    if (!bridge) return;
                    var v = bridge.readCalValues();
                    if (!v) return;
                    try {
                        var o = JSON.parse(v);
                        if (!o.ok) { logCal('读取失败: ' + o.error); return; }
                        document.getElementById('cal_load_cell').textContent = fmt(o.values.load_cell_mv_v);
                        document.getElementById('cal_tacho').textContent = fmt(o.values.tacho_hz);
                        document.getElementById('cal_d04').textContent = fmt(o.values.d04_tare);
                        document.getElementById('cal_d06').textContent = fmt(o.values.d06_pulses);
                        document.getElementById('cal_d02').textContent = fmt(o.values.d02_factor);
                    } catch(e) {}
                }

                document.addEventListener('DOMContentLoaded', function(){
                    new QWebChannel(qt.webChannelTransport, function(channel){
                        bridge = channel.objects.bridge;
                        setConnInfo(bridge.getConnInfo());
                        updateButtons(false);

                        document.getElementById('btnConnect').addEventListener('click', function(){
                            var r = bridge.connectDevice();
                            try { var o = JSON.parse(r); if (!o.ok) log('连接失败: ' + o.error); else log('连接成功'); } catch(e) {}
                            setConnInfo(bridge.getConnInfo());
                        });
                        document.getElementById('btnDisconnect').addEventListener('click', function(){
                            bridge.disconnectDevice();
                            log('已断开');
                        });

                        document.getElementById('btnSetFlow').addEventListener('click', function(){
                            var v = parseFloat(document.getElementById('inpFlow').value || '0');
                            var r = bridge.setFlowSetpoint(v);
                            try { var o = JSON.parse(r); log(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnSetBatch').addEventListener('click', function(){
                            var v = parseFloat(document.getElementById('inpBatch').value || '0');
                            var r = bridge.setBatchSetpoint(v);
                            try { var o = JSON.parse(r); log(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnSetPid').addEventListener('click', function(){
                            var p = parseFloat(document.getElementById('inpPidP').value || '0');
                            var i = parseFloat(document.getElementById('inpPidI').value || '0');
                            var r = bridge.setPid(p, i);
                            try { var o = JSON.parse(r); log(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });

                        function bindOnOff(btnOn, btnOff, fnOn, fnOff) {
                            document.getElementById(btnOn).addEventListener('click', function(){ var r = fnOn(); try { var o=JSON.parse(r); log(o.ok?'写入成功':('写入失败: '+o.error)); } catch(e) {} });
                            document.getElementById(btnOff).addEventListener('click', function(){ var r = fnOff(); try { var o=JSON.parse(r); log(o.ok?'写入成功':('写入失败: '+o.error)); } catch(e) {} });
                        }

                        bindOnOff('btnFeederOn','btnFeederOff', function(){ return bridge.setFeeder(true); }, function(){ return bridge.setFeeder(false); });
                        bindOnOff('btnPreFeederOn','btnPreFeederOff', function(){ return bridge.setPreFeeder(true); }, function(){ return bridge.setPreFeeder(false); });
                        bindOnOff('btnVolOn','btnVolOff', function(){ return bridge.setVolumeMode(true); }, function(){ return bridge.setVolumeMode(false); });
                        bindOnOff('btnSyncVolOn','btnSyncVolOff', function(){ return bridge.setSyncVolumeMode(true); }, function(){ return bridge.setSyncVolumeMode(false); });
                        bindOnOff('btnBatchModeOn','btnBatchModeOff', function(){ return bridge.setBatchMode(true); }, function(){ return bridge.setBatchMode(false); });

                        document.getElementById('btnClearTotals').addEventListener('click', function(){
                            var r = bridge.clearTotals();
                            try { var o = JSON.parse(r); log(o.ok ? '已请求清零' : ('清零失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnClearEvents').addEventListener('click', function(){
                            var r = bridge.clearEvents();
                            try { var o = JSON.parse(r); log(o.ok ? '已清事件标志' : ('清事件失败: ' + o.error)); } catch(e) {}
                        });

                        document.getElementById('btnSetCalMode').addEventListener('click', function(){
                            var v = parseInt(document.getElementById('selCalMode').value, 10);
                            var r = bridge.setCalMode(v === 1);
                            try { var o = JSON.parse(r); logCal(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnSetCalCmd').addEventListener('click', function(){
                            var v = parseInt(document.getElementById('inpCalCmd').value || '0', 10);
                            var r = bridge.setCalCmd(v);
                            try { var o = JSON.parse(r); logCal(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnWriteActualKg').addEventListener('click', function(){
                            var v = parseFloat(document.getElementById('inpActualKg').value || '0');
                            var r = bridge.writeActualKg(v);
                            try { var o = JSON.parse(r); logCal(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });
                        document.getElementById('btnWriteMeasuredKg').addEventListener('click', function(){
                            var v = parseFloat(document.getElementById('inpMeasuredKg').value || '0');
                            var r = bridge.writeMeasuredKg(v);
                            try { var o = JSON.parse(r); logCal(o.ok ? '写入成功' : ('写入失败: ' + o.error)); } catch(e) {}
                        });

                        document.getElementById('btnReadCal').addEventListener('click', function(){
                            var r = bridge.readCalStatus();
                            try {
                                var o = JSON.parse(r);
                                if (!o.ok) { logCal('读取失败: ' + o.error); return; }
                                document.getElementById('cal_cd').textContent = String(o.values.cal_countdown_s);
                                document.getElementById('cal_status').textContent = String(o.values.cal_status);
                                refreshCal();
                                logCal('状态: ' + JSON.stringify(o.values));
                            } catch(e) {}
                        });

                        document.getElementById('btnReadRegs').addEventListener('click', function(){
                            var s = parseInt(document.getElementById('inpRegStart').value || '0', 10);
                            var c = parseInt(document.getElementById('inpRegCount').value || '0', 10);
                            var r = bridge.readHolding(s, c);
                            try {
                                var o = JSON.parse(r);
                                if (!o.ok) { log('读取失败: ' + o.error); return; }
                                renderRegs(s, o.values);
                            } catch(e) {}
                        });

                        setInterval(tick, 700);
                        setInterval(refreshCal, 2000);
                    });
                });
            </script>
        </body>
        </html>
        """

        html_path = os.path.join(app_storage.ui_cache_dir(), "jy500_page.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        self.page.load(QUrl.fromLocalFile(html_path))


class JY500Bridge(QObject):
    def __init__(self):
        super().__init__()
        self._api: Optional[JY500B1C] = None
        self._poller: Optional[JY500Poller] = None
        self._plc_settings: Dict[str, Any] = {}

    def _ensure_api(self) -> None:
        self._plc_settings = _load_active_plc_settings()
        self._api = JY500B1C(self._plc_settings)

    def _ensure_poller(self) -> None:
        if self._api is None:
            self._ensure_api()
        if self._poller is None:
            refresh_ms = int(self._plc_settings.get("refresh_interval_ms") or 1000)
            self._poller = JY500Poller(self._api.client, refresh_ms)
            self._poller.start()

    def _json(self, ok: bool, error: str = "", values: Any = None) -> str:
        return json.dumps({"ok": bool(ok), "error": error or "", "values": values}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getConnInfo(self) -> str:
        s = _load_active_plc_settings()
        protocol = (s.get("protocol") or "modbus_tcp").lower()
        if protocol == "modbus_rtu":
            return f"Modbus-RTU unit_id={s.get('unit_id', 1)} port={s.get('serial_port','')} baud={s.get('baudrate',9600)} {s.get('bytesize',8)}{s.get('parity','N')}{s.get('stopbits',1)}"
        return f"Modbus-TCP unit_id={s.get('unit_id', 1)} {s.get('address','')}:{s.get('port',502)} byte_order={s.get('byte_order','ABCD')}"

    @pyqtSlot(result=str)
    def connectDevice(self) -> str:
        try:
            if self._api is None:
                self._ensure_api()
            ok, err = self._api.connect()
            if ok:
                self._ensure_poller()
            return self._json(ok, err)
        except Exception as e:
            return self._json(False, str(e))

    @pyqtSlot()
    def disconnectDevice(self) -> None:
        try:
            if self._poller is not None:
                self._poller.stop()
            self._poller = None
            if self._api is not None:
                self._api.close()
        finally:
            self._api = None

    @pyqtSlot(result=str)
    def getSnapshot(self) -> str:
        if self._poller is None:
            return json.dumps({"connected": False, "ts": 0, "error": "not started"}, ensure_ascii=False)
        return json.dumps(self._poller.latest(), ensure_ascii=False)

    @pyqtSlot(int, int, result=str)
    def readHolding(self, start: int, count: int) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        regs, err = self._api.read_registers(int(start), int(count))
        if regs is None:
            return self._json(False, err)
        return self._json(True, "", regs)

    @pyqtSlot(float, result=str)
    def setFlowSetpoint(self, v: float) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_flow_setpoint(float(v))
        return self._json(ok, err)

    @pyqtSlot(float, result=str)
    def setBatchSetpoint(self, v: float) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_batch_setpoint(float(v))
        return self._json(ok, err)

    @pyqtSlot(float, float, result=str)
    def setPid(self, p: float, i: float) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok1, err1 = self._api.set_pid_p(float(p))
        if not ok1:
            return self._json(False, err1)
        ok2, err2 = self._api.set_pid_i(float(i))
        return self._json(ok2, err2)

    @pyqtSlot(bool, result=str)
    def setFeeder(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_feeder(bool(on))
        return self._json(ok, err)

    @pyqtSlot(bool, result=str)
    def setPreFeeder(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_pre_feeder(bool(on))
        return self._json(ok, err)

    @pyqtSlot(bool, result=str)
    def setVolumeMode(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_volume_mode(bool(on))
        return self._json(ok, err)

    @pyqtSlot(bool, result=str)
    def setSyncVolumeMode(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_sync_volume_mode(bool(on))
        return self._json(ok, err)

    @pyqtSlot(bool, result=str)
    def setBatchMode(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_batch_mode(bool(on))
        return self._json(ok, err)

    @pyqtSlot(result=str)
    def clearTotals(self) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.clear_all_totals()
        return self._json(ok, err)

    @pyqtSlot(result=str)
    def clearEvents(self) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.clear_event_flag()
        return self._json(ok, err)

    @pyqtSlot(result=str)
    def readCalValues(self) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        r = self._api.read_comm_calibration_values()
        return self._json(r.ok, r.error, r.values)

    @pyqtSlot(bool, result=str)
    def setCalMode(self, on: bool) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_calibration_mode(bool(on))
        return self._json(ok, err)

    @pyqtSlot(int, result=str)
    def setCalCmd(self, cmd: int) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.set_calibration_command(int(cmd))
        return self._json(ok, err)

    @pyqtSlot(result=str)
    def readCalStatus(self) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        r = self._api.read_calibration_status()
        return self._json(r.ok, r.error, r.values)

    @pyqtSlot(float, result=str)
    def writeActualKg(self, kg: float) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.write_actual_weight(float(kg))
        return self._json(ok, err)

    @pyqtSlot(float, result=str)
    def writeMeasuredKg(self, kg: float) -> str:
        if self._api is None:
            return self._json(False, "not connected")
        ok, err = self._api.write_measured_weight(float(kg))
        return self._json(ok, err)
