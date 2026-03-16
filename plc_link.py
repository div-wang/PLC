#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PLC连接模块
负责PLC连接设置相关功能
"""

import os
import json
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSettings, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

import app_storage

class PLCLinkPage:
    """PLC连接页面类"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.bridge = PLCLinkBridge()
        self.channel = QWebChannel(self.page.page())
        self.channel.registerObject('bridge', self.bridge)
        self.page.page().setWebChannel(self.channel)
        self.generate_page()
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def load_plc_settings(self):
        """从JSON文件加载当前项目的PLC设置"""
        default_settings = {
            "device_type": "S7",
            "protocol": "modbus_tcp",
            "byte_order": "ABCD",
            "heartbeat": 30,
            "timeout": 10000,
            "refresh_interval_ms": 60000,
            "address": "192.168.1.10",
            "port": 102,
            "rack": 0,
            "slot": 1,
            "unit_id": 1,
            "serial_port": "",
            "baudrate": 9600,
            "parity": "N",
            "stopbits": 1,
            "bytesize": 8,
            "username": "",
            "password": ""
        }

        projects = app_storage.load_json("project.json", [])
        if isinstance(projects, list):
            for p in projects:
                if isinstance(p, dict) and p.get("is_active"):
                    return {**default_settings, **p.get("plc_settings", {})}
            if projects and isinstance(projects[0], dict):
                return {**default_settings, **projects[0].get("plc_settings", {})}

        return default_settings
    
    def generate_page(self):
        """生成PLC连接页面内容"""
        # 构建HTML页面
        settings = self.load_plc_settings()
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>PLC连接设置</title>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }
                .settings-container {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 20px;
                }
                .setting-group {
                    margin-bottom: 30px;
                }
                .setting-group-title {
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #eee;
                }
                .setting-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 0;
                    border-bottom: 1px solid #f5f5f5;
                }
                .setting-item:last-child {
                    border-bottom: none;
                }
                .setting-label {
                    font-weight: 500;
                    color: #333;
                }
                .setting-desc {
                    color: #999;
                    font-size: 13px;
                    margin-top: 3px;
                }
                .setting-control {
                    width: 200px;
                    margin-right: 10px;
                    text-align: right;
                }
                .setting-control input,
                .setting-control select {
                    width: 100%;
                    box-sizing: border-box;
                    padding: 8px 10px;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    font-size: 14px;
                    height: 34px;
                }
                .save-btn {
                    background-color: #1890ff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    margin-top: 20px;
                    float: right;
                }
                .save-btn:hover {
                    background-color: #40a9ff;
                }
            </style>
        </head>
        <body>
            <div class="settings-container">
                <div class="setting-group">
                    <div class="setting-group-title">PLC连接设置</div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">设备类型</div>
                            <div class="setting-desc">PLC设备类型</div>
                        </div>
                        <div class="setting-control">
                            <select id="device_type">
                                <option value="S7">S7</option>
                                <option value="JY500B1C">JY500B1C</option>
                                <option value="sqllite">sqllite</option>
                                <option value="MySQL">MySQL</option>
                            </select>
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">协议</div>
                            <div class="setting-desc">JY500B1C：Modbus-RTU/Modbus-TCP</div>
                        </div>
                        <div class="setting-control">
                            <select id="protocol">
                                <option value="modbus_tcp">Modbus-TCP</option>
                                <option value="modbus_rtu">Modbus-RTU</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">字节顺序</div>
                            <div class="setting-desc">数据字节顺序</div>
                        </div>
                        <div class="setting-control">
                            <select id="byte_order">
                                <option value="ABCD">ABCD</option>
                                <option value="CDAB">CDAB</option>
                                <option value="BADC">BADC</option>
                                <option value="DCBA">DCBA</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">心跳周期</div>
                            <div class="setting-desc">心跳周期(1-1000)</div>
                        </div>
                        <div class="setting-control">
                            <input id="heartbeat" type="number" min="1" max="1000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">读写超时(毫秒)</div>
                            <div class="setting-desc">读写超时时间(1000-30000)</div>
                        </div>
                        <div class="setting-control">
                            <input id="timeout" type="number" min="1000" max="30000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">刷新间隔(毫秒)</div>
                            <div class="setting-desc">数据刷新间隔(100-10000)</div>
                        </div>
                        <div class="setting-control">
                            <input id="refresh_ms" type="number" min="100" max="100000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">IP地址</div>
                            <div class="setting-desc">PLC连接IP地址(不可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input id="address" type="text">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">端口号</div>
                            <div class="setting-desc">PLC连接端口(不可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input id="port" type="number">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">站号</div>
                            <div class="setting-desc">Modbus 站号(1-247)</div>
                        </div>
                        <div class="setting-control">
                            <input id="unit_id" type="number" min="1" max="247">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">串口</div>
                            <div class="setting-desc">Modbus-RTU 串口，如 /dev/ttyUSB0</div>
                        </div>
                        <div class="setting-control">
                            <input id="serial_port" type="text">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">波特率</div>
                            <div class="setting-desc">RS485 波特率，默认9600</div>
                        </div>
                        <div class="setting-control">
                            <input id="baudrate" type="number">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">数据位</div>
                            <div class="setting-desc">默认8</div>
                        </div>
                        <div class="setting-control">
                            <input id="bytesize" type="number" min="5" max="8">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">校验位</div>
                            <div class="setting-desc">N/E/O</div>
                        </div>
                        <div class="setting-control">
                            <select id="parity">
                                <option value="N">N</option>
                                <option value="E">E</option>
                                <option value="O">O</option>
                            </select>
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">停止位</div>
                            <div class="setting-desc">默认1</div>
                        </div>
                        <div class="setting-control">
                            <input id="stopbits" type="number" min="1" max="2">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">机架号</div>
                            <div class="setting-desc">PLC机架号(Rack)</div>
                        </div>
                        <div class="setting-control">
                            <input id="rack" type="number" min="0" max="255">
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">插槽号</div>
                            <div class="setting-desc">PLC插槽号(Slot)</div>
                        </div>
                        <div class="setting-control">
                            <input id="slot" type="number" min="0" max="255">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">用户名</div>
                            <div class="setting-desc">连接用户名(可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input id="username" type="text">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">密码</div>
                            <div class="setting-desc">连接密码(可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input id="password" type="password">
                        </div>
                    </div>
                </div>
                
                <button class="save-btn" id="saveBtn">保存连接设置</button>
                <div style="clear: both;"></div>
            </div>
            
            <script>
            // 初始化值
            var settings = {
                device_type: "__DEVICE_TYPE__",
                protocol: "__PROTOCOL__",
                byte_order: "__BYTE_ORDER__",
                heartbeat: __HEARTBEAT__,
                timeout: __TIMEOUT__,
                refresh_ms: __REFRESH_MS__,
                address: "__ADDRESS__",
                port: __PORT__,
                rack: __RACK__,
                slot: __SLOT__,
                unit_id: __UNIT_ID__,
                serial_port: "__SERIAL_PORT__",
                baudrate: __BAUDRATE__,
                parity: "__PARITY__",
                stopbits: __STOPBITS__,
                bytesize: __BYTESIZE__,
                username: "__USERNAME__",
                password: "__PASSWORD__"
            };
            
            // 各类型默认参数
            var defaultParams = {
                'S7': {
                    byte_order: 'ABCD',
                    heartbeat: 30,
                    timeout: 10000,
                    refresh_ms: 60000,
                    address: '192.168.1.10',
                    port: 102,
                    rack: 0,
                    slot: 1,
                    username: '',
                    password: ''
                },
                'sqllite': {
                    byte_order: 'ABCD',
                    heartbeat: 30,
                    timeout: 10000,
                    refresh_ms: 60000,
                    address: '',
                    port: 0,
                    rack: 0,
                    slot: 0,
                    username: '',
                    password: ''
                },
                'JY500B1C': {
                    protocol: 'modbus_tcp',
                    byte_order: 'ABCD',
                    heartbeat: 30,
                    timeout: 10000,
                    refresh_ms: 1000,
                    address: '192.168.1.101',
                    port: 502,
                    rack: 0,
                    slot: 0,
                    unit_id: 1,
                    serial_port: '',
                    baudrate: 9600,
                    parity: 'N',
                    stopbits: 1,
                    bytesize: 8,
                    username: '',
                    password: ''
                },
                'MySQL': {
                    byte_order: 'ABCD',
                    heartbeat: 30,
                    timeout: 10000,
                    refresh_ms: 60000,
                    address: '127.0.0.1',
                    port: 3306,
                    rack: 0,
                    slot: 0,
                    username: 'root',
                    password: ''
                }
            };
            
            function initValues() {
                var dt = document.getElementById('device_type');
                if(dt) dt.value = settings.device_type;
                
                var pr = document.getElementById('protocol');
                if(pr) pr.value = settings.protocol;

                var bo = document.getElementById('byte_order');
                if(bo) bo.value = settings.byte_order;
                
                document.getElementById('heartbeat').value = settings.heartbeat;
                document.getElementById('timeout').value = settings.timeout;
                document.getElementById('refresh_ms').value = settings.refresh_ms;
                document.getElementById('address').value = settings.address;
                document.getElementById('port').value = settings.port;
                document.getElementById('rack').value = settings.rack;
                document.getElementById('slot').value = settings.slot;
                document.getElementById('unit_id').value = settings.unit_id;
                document.getElementById('serial_port').value = settings.serial_port;
                document.getElementById('baudrate').value = settings.baudrate;
                document.getElementById('parity').value = settings.parity;
                document.getElementById('stopbits').value = settings.stopbits;
                document.getElementById('bytesize').value = settings.bytesize;
                document.getElementById('username').value = settings.username;
                document.getElementById('password').value = settings.password;
            }
            
            function resetToDefaults(type) {
                var defs = defaultParams[type] || defaultParams['S7'];
                
                var pr = document.getElementById('protocol');
                if(pr && defs.protocol) pr.value = defs.protocol;

                var bo = document.getElementById('byte_order');
                if(bo) bo.value = defs.byte_order;
                
                document.getElementById('heartbeat').value = defs.heartbeat;
                document.getElementById('timeout').value = defs.timeout;
                document.getElementById('refresh_ms').value = defs.refresh_ms;
                document.getElementById('address').value = defs.address;
                document.getElementById('port').value = defs.port;
                document.getElementById('rack').value = defs.rack;
                document.getElementById('slot').value = defs.slot;
                if (defs.unit_id !== undefined) document.getElementById('unit_id').value = defs.unit_id;
                if (defs.serial_port !== undefined) document.getElementById('serial_port').value = defs.serial_port;
                if (defs.baudrate !== undefined) document.getElementById('baudrate').value = defs.baudrate;
                if (defs.parity !== undefined) document.getElementById('parity').value = defs.parity;
                if (defs.stopbits !== undefined) document.getElementById('stopbits').value = defs.stopbits;
                if (defs.bytesize !== undefined) document.getElementById('bytesize').value = defs.bytesize;
                document.getElementById('username').value = defs.username;
                document.getElementById('password').value = defs.password;
            }

            document.addEventListener('DOMContentLoaded', function(){
                initValues();
                
                var dt = document.getElementById('device_type');
                if(dt) {
                    dt.addEventListener('change', function() {
                        resetToDefaults(this.value);
                    });
                }
                
                new QWebChannel(qt.webChannelTransport, function(channel){
                    window.bridge = channel.objects.bridge;
                    
                    document.getElementById('saveBtn').addEventListener('click', function(){
                        var data = {
                            device_type: document.getElementById('device_type').value,
                            protocol: document.getElementById('protocol').value,
                            byte_order: document.getElementById('byte_order').value,
                            heartbeat: parseInt(document.getElementById('heartbeat').value),
                            timeout: parseInt(document.getElementById('timeout').value),
                            refresh_ms: parseInt(document.getElementById('refresh_ms').value),
                            address: document.getElementById('address').value,
                            port: parseInt(document.getElementById('port').value),
                            rack: parseInt(document.getElementById('rack').value),
                            slot: parseInt(document.getElementById('slot').value),
                            unit_id: parseInt(document.getElementById('unit_id').value),
                            serial_port: document.getElementById('serial_port').value,
                            baudrate: parseInt(document.getElementById('baudrate').value),
                            parity: document.getElementById('parity').value,
                            stopbits: parseInt(document.getElementById('stopbits').value),
                            bytesize: parseInt(document.getElementById('bytesize').value),
                            username: document.getElementById('username').value,
                            password: document.getElementById('password').value
                        };

                        bridge.saveSettingsJson(JSON.stringify(data));
                        alert('连接设置已保存');
                    });
                });
            });
            </script>
        </body>
        </html>
        """
        
        # 替换初始值
        html_content = html_content.replace("__DEVICE_TYPE__", settings.get("device_type", "S7"))
        html_content = html_content.replace("__PROTOCOL__", settings.get("protocol", "modbus_tcp"))
        html_content = html_content.replace("__BYTE_ORDER__", settings.get("byte_order", "ABCD"))
        html_content = html_content.replace("__HEARTBEAT__", str(settings.get("heartbeat", 30)))
        html_content = html_content.replace("__TIMEOUT__", str(settings.get("timeout", 10000)))
        html_content = html_content.replace("__REFRESH_MS__", str(settings.get("refresh_interval_ms", 60000)))
        html_content = html_content.replace("__ADDRESS__", settings.get("address", "192.168.1.10"))
        html_content = html_content.replace("__PORT__", str(settings.get("port", 102)))
        html_content = html_content.replace("__RACK__", str(settings.get("rack", 0)))
        html_content = html_content.replace("__SLOT__", str(settings.get("slot", 1)))
        html_content = html_content.replace("__UNIT_ID__", str(settings.get("unit_id", 1)))
        html_content = html_content.replace("__SERIAL_PORT__", settings.get("serial_port", ""))
        html_content = html_content.replace("__BAUDRATE__", str(settings.get("baudrate", 9600)))
        html_content = html_content.replace("__PARITY__", settings.get("parity", "N"))
        html_content = html_content.replace("__STOPBITS__", str(settings.get("stopbits", 1)))
        html_content = html_content.replace("__BYTESIZE__", str(settings.get("bytesize", 8)))
        html_content = html_content.replace("__USERNAME__", settings.get("username", ""))
        html_content = html_content.replace("__PASSWORD__", settings.get("password", ""))
        
        # 保存HTML到临时文件
        html_path = os.path.join(app_storage.ui_cache_dir(), "plc_link_page.html")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(html_path))

class PLCLinkBridge(QObject):
    @pyqtSlot(str)
    def saveSettingsJson(self, json_str):
        try:
            data = json.loads(json_str)

            def to_int(v, d=0):
                try:
                    return int(v)
                except Exception:
                    return int(d)

            def to_str(v, d=""):
                return d if v is None else str(v)

            projects = app_storage.load_json("project.json", [])
            if not isinstance(projects, list):
                projects = []
            
            # Update active project settings
            updated = False
            for p in projects:
                if p.get("is_active"):
                    p["plc_settings"] = {
                        "device_type": to_str(data.get("device_type"), "S7"),
                        "protocol": to_str(data.get("protocol"), "modbus_tcp"),
                        "byte_order": to_str(data.get("byte_order"), "ABCD"),
                        "heartbeat": to_int(data.get("heartbeat", 30), 30),
                        "timeout": to_int(data.get("timeout", 10000), 10000),
                        "refresh_interval_ms": to_int(data.get("refresh_ms", 60000), 60000),
                        "address": to_str(data.get("address"), ""),
                        "port": to_int(data.get("port", 0), 0),
                        "rack": to_int(data.get("rack", 0), 0),
                        "slot": to_int(data.get("slot", 0), 0),
                        "unit_id": to_int(data.get("unit_id", 1), 1),
                        "serial_port": to_str(data.get("serial_port", ""), ""),
                        "baudrate": to_int(data.get("baudrate", 9600), 9600),
                        "parity": to_str(data.get("parity", "N"), "N"),
                        "stopbits": to_int(data.get("stopbits", 1), 1),
                        "bytesize": to_int(data.get("bytesize", 8), 8),
                        "username": to_str(data.get("username", ""), ""),
                        "password": to_str(data.get("password", ""), "")
                    }
                    updated = True
                    break
            
            # If no active project found but projects exist, update the first one
            if not updated and projects:
                projects[0]["plc_settings"] = {
                    "device_type": to_str(data.get("device_type"), "S7"),
                    "protocol": to_str(data.get("protocol"), "modbus_tcp"),
                    "byte_order": to_str(data.get("byte_order"), "ABCD"),
                    "heartbeat": to_int(data.get("heartbeat", 30), 30),
                    "timeout": to_int(data.get("timeout", 10000), 10000),
                    "refresh_interval_ms": to_int(data.get("refresh_ms", 60000), 60000),
                    "address": to_str(data.get("address"), ""),
                    "port": to_int(data.get("port", 0), 0),
                    "rack": to_int(data.get("rack", 0), 0),
                    "slot": to_int(data.get("slot", 0), 0),
                    "unit_id": to_int(data.get("unit_id", 1), 1),
                    "serial_port": to_str(data.get("serial_port", ""), ""),
                    "baudrate": to_int(data.get("baudrate", 9600), 9600),
                    "parity": to_str(data.get("parity", "N"), "N"),
                    "stopbits": to_int(data.get("stopbits", 1), 1),
                    "bytesize": to_int(data.get("bytesize", 8), 8),
                    "username": to_str(data.get("username", ""), ""),
                    "password": to_str(data.get("password", ""), "")
                }
                updated = True
                
            if updated:
                app_storage.save_json("project.json", projects)
                    
        except Exception as e:
            print(f"Error saving PLC settings: {e}")
