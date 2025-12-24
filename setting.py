#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置模块
负责系统设置相关功能
"""

import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSettings, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

class SettingPage:
    """设置页面类"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.bridge = SettingsBridge()
        self.channel = QWebChannel(self.page.page())
        self.channel.registerObject('bridge', self.bridge)
        self.page.page().setWebChannel(self.channel)
        self.generate_setting_page()
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def generate_setting_page(self):
        """生成设置页面内容"""
        # 构建HTML页面
        settings = QSettings("PLCApp", "PLC")
        try:
            refresh_ms = int(settings.value("refresh_interval_ms", 60000))
        except Exception:
            refresh_ms = 60000
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>系统设置</title>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                .header p {
                    color: #666;
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
                }
                input[type="text"], input[type="number"], input[type="password"], select {
                    width: 100%;
                    padding: 8px 10px;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    font-size: 14px;
                    height: 34px;
                    box-sizing: border-box;
                }
                .toggle-switch {
                    position: relative;
                    display: inline-block;
                    width: 50px;
                    height: 24px;
                }
                .toggle-switch input {
                    opacity: 0;
                    width: 0;
                    height: 0;
                }
                .slider {
                    position: absolute;
                    cursor: pointer;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: #ccc;
                    transition: .4s;
                    border-radius: 24px;
                }
                .slider:before {
                    position: absolute;
                    content: "";
                    height: 16px;
                    width: 16px;
                    left: 4px;
                    bottom: 4px;
                    background-color: white;
                    transition: .4s;
                    border-radius: 50%;
                }
                input:checked + .slider {
                    background-color: #1890ff;
                }
                input:checked + .slider:before {
                    transform: translateX(26px);
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
            <div class="header">
                <h1>系统设置</h1>
                <p>配置系统参数和首选项</p>
            </div>
            
            <div class="settings-container">
                <div class="setting-group">
                    <div class="setting-group-title">PLC连接设置</div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">设备类型</div>
                            <div class="setting-desc">PLC设备类型</div>
                        </div>
                        <div class="setting-control">
                            <select>
                                <option selected>S7</option>
                                <option>sqllite</option>
                                <option>MySQL</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">字节顺序</div>
                            <div class="setting-desc">数据字节顺序</div>
                        </div>
                        <div class="setting-control">
                            <select>
                                <option selected>ABCD</option>
                                <option>CDAB</option>
                                <option>BADC</option>
                                <option>DCBA</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">心跳周期</div>
                            <div class="setting-desc">心跳周期(1-1000)</div>
                        </div>
                        <div class="setting-control">
                            <input type="number" value="30" min="1" max="1000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">读写超时(毫秒)</div>
                            <div class="setting-desc">读写超时时间(1000-30000)</div>
                        </div>
                        <div class="setting-control">
                            <input type="number" value="10000" min="1000" max="30000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">刷新间隔(毫秒)</div>
                            <div class="setting-desc">数据刷新间隔(100-10000)</div>
                        </div>
                        <div class="setting-control">
                            <input id="refresh_ms" type="number" value="__REFRESH_MS__" min="100" max="100000">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">地址</div>
                            <div class="setting-desc">PLC连接地址(不可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input type="text" value="192.168.1.10">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">端口号</div>
                            <div class="setting-desc">PLC连接端口(不可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input type="number" value="102">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">用户名</div>
                            <div class="setting-desc">连接用户名(可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input type="text" value="">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">密码</div>
                            <div class="setting-desc">连接密码(可为空)</div>
                        </div>
                        <div class="setting-control">
                            <input type="password" value="">
                        </div>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="setting-group-title">应用设置</div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">主题</div>
                            <div class="setting-desc">选择应用主题</div>
                        </div>
                        <div class="setting-control">
                            <select>
                                <option>浅色</option>
                                <option>深色</option>
                                <option>系统默认</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">数据刷新间隔(秒)</div>
                            <div class="setting-desc">数据自动刷新间隔</div>
                        </div>
                        <div class="setting-control">
                            <input type="text" value="5">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">自动保存日志</div>
                            <div class="setting-desc">自动保存系统日志</div>
                        </div>
                        <div class="setting-control">
                            <label class="toggle-switch">
                                <input type="checkbox" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">启用通知</div>
                            <div class="setting-desc">启用系统通知</div>
                        </div>
                        <div class="setting-control">
                            <label class="toggle-switch">
                                <input type="checkbox" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <button class="save-btn" id="saveSettingsBtn">保存设置</button>
                <div style="clear: both;"></div>
            </div>
            <script>
            document.addEventListener('DOMContentLoaded', function(){
                new QWebChannel(qt.webChannelTransport, function(channel){
                    window.bridge = channel.objects.bridge;
                    var saveBtn = document.getElementById('saveSettingsBtn');
                    saveBtn.addEventListener('click', function(){
                        var v = parseInt(document.getElementById('refresh_ms').value);
                        if (isNaN(v) || v < 100) { v = 1000; }
                        bridge.setRefreshIntervalMs(v);
                        alert('设置已保存: 刷新间隔 ' + v + ' ms');
                    });
                });
            });
            </script>
        </body>
        </html>
        """
        html_content = html_content.replace("__REFRESH_MS__", str(refresh_ms))
        
        # 保存HTML到临时文件
        setting_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "setting_page.html")
        with open(setting_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(setting_html_path))

class SettingsBridge(QObject):
    @pyqtSlot(int)
    def setRefreshIntervalMs(self, ms: int):
        s = QSettings("PLCApp", "PLC")
        s.setValue("refresh_interval_ms", int(ms))
