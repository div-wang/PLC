#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置模块
负责系统设置相关功能
"""

import os
import json
import codecs
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
    
    def load_settings(self):
        """从JSON文件加载设置"""
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setting.json")
        default_settings = {
            "theme": "浅色",
            "refresh_interval": 5,
            "auto_save_logs": True,
            "enable_notifications": True
        }
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return {**default_settings, **json.load(f)}
            except Exception as e:
                print(f"Error loading settings: {e}")
                return default_settings
        return default_settings

    def generate_setting_page(self):
        """生成设置页面内容"""
        settings = self.load_settings()
        
        # 构建HTML页面
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
            
            <div class="settings-container">
                <div class="setting-group">
                    <div class="setting-group-title">应用设置</div>
                    
                    <div class="setting-item">

                        <div>
                            <div class="setting-label">主题</div>
                            <div class="setting-desc">选择应用主题</div>
                        </div>
                        <div class="setting-control">
                            <select id="themeSelect">
                                <option value="浅色">浅色</option>
                                <option value="深色">深色</option>
                                <option value="系统默认">系统默认</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">数据刷新间隔(秒)</div>
                            <div class="setting-desc">数据自动刷新间隔</div>
                        </div>
                        <div class="setting-control">
                            <input type="number" id="refreshInterval" value="__REFRESH_INTERVAL__">
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <div>
                            <div class="setting-label">自动保存日志</div>
                            <div class="setting-desc">自动保存系统日志</div>
                        </div>
                        <div class="setting-control">
                            <label class="toggle-switch">
                                <input type="checkbox" id="autoSaveLogs" __AUTO_SAVE_LOGS__>
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
                                <input type="checkbox" id="enableNotifications" __ENABLE_NOTIFICATIONS__>
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
                // Set theme selection
                var themeSelect = document.getElementById('themeSelect');
                themeSelect.value = "__THEME__";

                new QWebChannel(qt.webChannelTransport, function(channel){
                    window.bridge = channel.objects.bridge;
                    var saveBtn = document.getElementById('saveSettingsBtn');
                    saveBtn.addEventListener('click', function(){
                        var theme = document.getElementById('themeSelect').value;
                        var refreshInterval = parseInt(document.getElementById('refreshInterval').value);
                        var autoSaveLogs = document.getElementById('autoSaveLogs').checked;
                        var enableNotifications = document.getElementById('enableNotifications').checked;

                        bridge.saveSettings(theme, refreshInterval, autoSaveLogs, enableNotifications);
                        alert('设置已保存');
                    });
                });
            });
            </script>
        </body>
        </html>
        """
        
        # Inject values
        html_content = html_content.replace("__THEME__", settings["theme"])
        html_content = html_content.replace("__REFRESH_INTERVAL__", str(settings["refresh_interval"]))
        html_content = html_content.replace("__AUTO_SAVE_LOGS__", "checked" if settings["auto_save_logs"] else "")
        html_content = html_content.replace("__ENABLE_NOTIFICATIONS__", "checked" if settings["enable_notifications"] else "")

        # 保存HTML到临时文件
        setting_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "setting_page.html")
        os.makedirs(os.path.dirname(setting_html_path), exist_ok=True)
        with open(setting_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(setting_html_path))

class SettingsBridge(QObject):
    @pyqtSlot(str, int, bool, bool)
    def saveSettings(self, theme, refresh_interval, auto_save_logs, enable_notifications):
        """保存设置到JSON文件"""
        settings = {
            "theme": theme,
            "refresh_interval": refresh_interval,
            "auto_save_logs": auto_save_logs,
            "enable_notifications": enable_notifications
        }
        
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setting.json")
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
