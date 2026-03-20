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


def _load_setting_template() -> dict:
    try:
        path = app_storage.resource_file_path("setting.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_setting_root() -> dict:
    template = _load_setting_template()
    user = app_storage.load_json("setting.json", {})
    if not isinstance(user, dict):
        user = {}
    merged = _deep_merge(template, user)

    try:
        if "plc_link" not in merged:
            projects = app_storage.load_json("project.json", [])
            if isinstance(projects, list):
                active = None
                for p in projects:
                    if isinstance(p, dict) and p.get("is_active"):
                        active = p
                        break
                if active is None and projects and isinstance(projects[0], dict):
                    active = projects[0]
                if isinstance(active, dict) and isinstance(active.get("plc_settings"), dict):
                    merged["plc_link"] = dict(active.get("plc_settings") or {})
    except Exception:
        pass

    if merged != user:
        try:
            app_storage.save_json("setting.json", merged)
        except Exception:
            pass
    return merged


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
        root = _load_setting_root()
        plc = root.get("plc_link")
        if isinstance(plc, dict):
            return dict(plc)
        return {}
    
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
                                <option value="sqllite">sqllite</option>
                                <option value="MySQL">MySQL</option>
                            </select>
                        </div>
                    </div>

                    <div class="setting-item">
                        <div>
                            <div class="setting-label">协议</div>
                            <div class="setting-desc">通讯协议</div>
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

            root = _load_setting_root()
            if not isinstance(root, dict):
                root = {}
            root["plc_link"] = {
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
                "username": to_str(data.get("username", ""), ""),
                "password": to_str(data.get("password", ""), ""),
            }
            app_storage.save_json("setting.json", root)
                    
        except Exception as e:
            print(f"Error saving PLC settings: {e}")
