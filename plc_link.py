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
        projects_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.json")
        default_settings = {
            "device_type": "S7",
            "byte_order": "ABCD",
            "heartbeat": 30,
            "timeout": 10000,
            "refresh_interval_ms": 60000,
            "address": "192.168.1.10",
            "port": 102,
            "username": "",
            "password": ""
        }
        
        if os.path.exists(projects_path):
            try:
                with open(projects_path, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
                    for p in projects:
                        if p.get("is_active"):
                            return {**default_settings, **p.get("plc_settings", {})}
                    if projects:
                        return {**default_settings, **projects[0].get("plc_settings", {})}
            except Exception as e:
                print(f"Error loading PLC settings: {e}")
        
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
                                <option value="sqllite">sqllite</option>
                                <option value="MySQL">MySQL</option>
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
                            <div class="setting-label">地址</div>
                            <div class="setting-desc">PLC连接地址(不可为空)</div>
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
                byte_order: "__BYTE_ORDER__",
                heartbeat: __HEARTBEAT__,
                timeout: __TIMEOUT__,
                refresh_ms: __REFRESH_MS__,
                address: "__ADDRESS__",
                port: __PORT__,
                username: "__USERNAME__",
                password: "__PASSWORD__"
            };
            
            function initValues() {
                var dt = document.getElementById('device_type');
                if(dt) dt.value = settings.device_type;
                
                var bo = document.getElementById('byte_order');
                if(bo) bo.value = settings.byte_order;
                
                document.getElementById('heartbeat').value = settings.heartbeat;
                document.getElementById('timeout').value = settings.timeout;
                document.getElementById('refresh_ms').value = settings.refresh_ms;
                document.getElementById('address').value = settings.address;
                document.getElementById('port').value = settings.port;
                document.getElementById('username').value = settings.username;
                document.getElementById('password').value = settings.password;
            }

            document.addEventListener('DOMContentLoaded', function(){
                initValues();
                
                new QWebChannel(qt.webChannelTransport, function(channel){
                    window.bridge = channel.objects.bridge;
                    
                    document.getElementById('saveBtn').addEventListener('click', function(){
                        var data = {
                            device_type: document.getElementById('device_type').value,
                            byte_order: document.getElementById('byte_order').value,
                            heartbeat: parseInt(document.getElementById('heartbeat').value),
                            timeout: parseInt(document.getElementById('timeout').value),
                            refresh_ms: parseInt(document.getElementById('refresh_ms').value),
                            address: document.getElementById('address').value,
                            port: parseInt(document.getElementById('port').value),
                            username: document.getElementById('username').value,
                            password: document.getElementById('password').value
                        };
                        
                        bridge.saveSettings(
                            data.device_type, data.byte_order, data.heartbeat, 
                            data.timeout, data.refresh_ms, data.address, 
                            data.port, data.username, data.password
                        );
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
        html_content = html_content.replace("__BYTE_ORDER__", settings.get("byte_order", "ABCD"))
        html_content = html_content.replace("__HEARTBEAT__", str(settings.get("heartbeat", 30)))
        html_content = html_content.replace("__TIMEOUT__", str(settings.get("timeout", 10000)))
        html_content = html_content.replace("__REFRESH_MS__", str(settings.get("refresh_interval_ms", 60000)))
        html_content = html_content.replace("__ADDRESS__", settings.get("address", "192.168.1.10"))
        html_content = html_content.replace("__PORT__", str(settings.get("port", 102)))
        html_content = html_content.replace("__USERNAME__", settings.get("username", ""))
        html_content = html_content.replace("__PASSWORD__", settings.get("password", ""))
        
        # 保存HTML到临时文件
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "plc_link_page.html")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(html_path))

class PLCLinkBridge(QObject):
    @pyqtSlot(str, str, int, int, int, str, int, str, str)
    def saveSettings(self, device_type, byte_order, heartbeat, timeout, refresh_ms, address, port, username, password):
        projects_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.json")
        try:
            projects = []
            if os.path.exists(projects_path):
                with open(projects_path, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
            
            # Update active project settings
            updated = False
            for p in projects:
                if p.get("is_active"):
                    p["plc_settings"] = {
                        "device_type": device_type,
                        "byte_order": byte_order,
                        "heartbeat": int(heartbeat),
                        "timeout": int(timeout),
                        "refresh_interval_ms": int(refresh_ms),
                        "address": address,
                        "port": int(port),
                        "username": username,
                        "password": password
                    }
                    updated = True
                    break
            
            # If no active project found but projects exist, update the first one
            if not updated and projects:
                projects[0]["plc_settings"] = {
                    "device_type": device_type,
                    "byte_order": byte_order,
                    "heartbeat": int(heartbeat),
                    "timeout": int(timeout),
                    "refresh_interval_ms": int(refresh_ms),
                    "address": address,
                    "port": int(port),
                    "username": username,
                    "password": password
                }
                updated = True
                
            if updated:
                with open(projects_path, 'w', encoding='utf-8') as f:
                    json.dump(projects, f, indent=4, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Error saving PLC settings: {e}")
