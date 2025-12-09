#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基础UI组件
包含主窗口和基本布局结构
"""

import sys
import os
import time
import socket
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QStackedWidget)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QIcon, QFont

class BaseUI(QMainWindow):
    """浏览器风格UI基础窗口"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        """初始化UI界面"""
        # 设置窗口标题和大小
        self.setWindowTitle('浏览器风格UI')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建上中下三部分
        self.create_top_section()
        self.create_middle_section()
        self.create_bottom_section()
        
        # 添加到主布局
        self.main_layout.addWidget(self.top_section)
        self.main_layout.addWidget(self.middle_section)
        self.main_layout.addWidget(self.bottom_section)
        
        # 设置布局比例
        self.main_layout.setStretch(0, 1)  # 顶部占比
        self.main_layout.setStretch(1, 8)  # 中间占比
        self.main_layout.setStretch(2, 1)  # 底部占比
        
        # 初始化定时器，用于更新时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 每秒更新一次
    
    def create_top_section(self):
        """创建顶部部分 - 按钮栏"""
        self.top_section = QWidget()
        self.top_layout = QHBoxLayout(self.top_section)
        self.top_layout.setContentsMargins(10, 5, 10, 5)
        
        # 创建按钮
        self.home_btn = QPushButton('主页')
        self.project_btn = QPushButton('项目管理')
        self.settings_btn = QPushButton('设置')
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
        """
        self.home_btn.setStyleSheet(button_style)
        self.project_btn.setStyleSheet(button_style)
        self.settings_btn.setStyleSheet(button_style)
        
        # 连接按钮信号
        self.home_btn.clicked.connect(self.show_home_page)
        self.project_btn.clicked.connect(self.show_project_page)
        self.settings_btn.clicked.connect(self.show_settings_page)
        
        # 添加按钮到布局
        self.top_layout.addWidget(self.home_btn)
        self.top_layout.addWidget(self.project_btn)
        self.top_layout.addWidget(self.settings_btn)
        self.top_layout.addStretch(1)  # 右侧弹性空间
        
        # 设置顶部部分样式
        self.top_section.setStyleSheet("""
            background-color: #f0f0f0;
            border-bottom: 1px solid #dcdcdc;
        """)
    
    def create_middle_section(self):
        """创建中间部分 - 内容区域"""
        self.middle_section = QStackedWidget()
        
    def add_page(self, page, page_name):
        """添加页面到中间内容区域
        
        Args:
            page: 页面组件
            page_name: 页面名称，用于标识页面
        """
        self.middle_section.addWidget(page)
        # 如果是第一个添加的页面，默认显示
        if self.middle_section.count() == 1:
            self.show_home_page()
    
    def create_bottom_section(self):
        """创建底部部分 - 状态栏"""
        self.bottom_section = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_section)
        bottom_layout.setContentsMargins(10, 5, 10, 5)
        
        # 创建状态信息标签
        self.time_label = QLabel()
        self.ip_label = QLabel()
        
        # 获取IP地址
        ip_address = self.get_ip_address()
        self.ip_label.setText(f"IP: {ip_address}")
        
        # 设置标签样式
        label_style = """
            QLabel {
                color: #555;
                font-size: 12px;
            }
        """
        self.time_label.setStyleSheet(label_style)
        self.ip_label.setStyleSheet(label_style)
        
        # 添加标签到布局
        bottom_layout.addWidget(self.time_label)
        bottom_layout.addStretch(1)  # 中间弹性空间
        bottom_layout.addWidget(self.ip_label)
        
        # 设置底部部分样式
        self.bottom_section.setStyleSheet("""
            background-color: #f0f0f0;
            border-top: 1px solid #dcdcdc;
        """)
        
        # 初始化时间
        self.update_time()
    
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(f"当前时间: {current_time}")
    
    def get_ip_address(self):
        """获取本机IP地址"""
        try:
            # 创建一个临时socket连接来获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def show_home_page(self):
        """显示主页"""
        self.middle_section.setCurrentIndex(0)
        self.home_btn.setStyleSheet(self.home_btn.styleSheet() + "background-color: #2a66c8;")
        self.project_btn.setStyleSheet(self.project_btn.styleSheet().replace("background-color: #2a66c8;", ""))
        self.settings_btn.setStyleSheet(self.settings_btn.styleSheet().replace("background-color: #2a66c8;", ""))
    
    def show_project_page(self):
        """显示项目管理页面"""
        self.middle_section.setCurrentIndex(1)
        self.project_btn.setStyleSheet(self.project_btn.styleSheet() + "background-color: #2a66c8;")
        self.home_btn.setStyleSheet(self.home_btn.styleSheet().replace("background-color: #2a66c8;", ""))
        self.settings_btn.setStyleSheet(self.settings_btn.styleSheet().replace("background-color: #2a66c8;", ""))
    
    def show_settings_page(self):
        """显示设置页面"""
        self.middle_section.setCurrentIndex(2)
        self.settings_btn.setStyleSheet(self.settings_btn.styleSheet() + "background-color: #2a66c8;")
        self.home_btn.setStyleSheet(self.home_btn.styleSheet().replace("background-color: #2a66c8;", ""))
        self.project_btn.setStyleSheet(self.project_btn.styleSheet().replace("background-color: #2a66c8;", ""))