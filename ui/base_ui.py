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
        self.setWindowTitle('皮带秤')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)  # 改为水平布局
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建左侧导航栏和右侧内容区
        self.create_left_sidebar()
        self.create_right_content()
        
        # 添加到主布局
        self.main_layout.addWidget(self.left_sidebar)
        self.main_layout.addWidget(self.right_content)
        
        # 设置布局比例
        self.main_layout.setStretch(0, 1)  # 左侧占比
        self.main_layout.setStretch(1, 5)  # 右侧占比
        
        # 初始化定时器，用于更新时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 每秒更新一次
    
    def create_left_sidebar(self):
        """创建左侧导航栏"""
        self.left_sidebar = QWidget()
        self.left_layout = QVBoxLayout(self.left_sidebar)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)
        
        # 设置左侧背景色
        self.left_sidebar.setStyleSheet("""
            QWidget {
                background-color: #001529;
                color: white;
            }
        """)
        
        # 添加标题/Logo区域
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("PLC监控系统")
        title_label.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: bold;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(title_label)
        
        self.left_layout.addWidget(logo_widget)
        
        # 创建导航按钮
        self.home_btn = QPushButton('主页')
        self.project_btn = QPushButton('项目管理')
        self.plc_link_btn = QPushButton('PLC链接')
        self.settings_btn = QPushButton('设置')
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.65);
                border: none;
                padding: 15px 20px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                color: white;
                background-color: #1890ff;
            }
            QPushButton:checked {
                color: white;
                background-color: #1890ff;
                border-right: 4px solid #1890ff;
            }
        """
        
        for btn in [self.home_btn, self.project_btn, self.plc_link_btn, self.settings_btn]:
            btn.setStyleSheet(button_style)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            
        # 连接按钮信号
        self.home_btn.clicked.connect(self.show_home_page)
        self.project_btn.clicked.connect(self.show_project_page)
        self.plc_link_btn.clicked.connect(self.show_plc_link_page)
        self.settings_btn.clicked.connect(self.show_settings_page)
        
        # 添加按钮到布局
        self.left_layout.addWidget(self.home_btn)
        self.left_layout.addWidget(self.project_btn)
        self.left_layout.addWidget(self.plc_link_btn)
        self.left_layout.addWidget(self.settings_btn)
        self.left_layout.addStretch(1)  # 底部弹性空间
        
        # 底部状态信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 20, 20, 20)
        
        self.time_label = QLabel()
        self.ip_label = QLabel()
        
        # 获取IP地址
        ip_address = self.get_ip_address()
        self.ip_label.setText(f"IP: {ip_address}")
        
        label_style = """
            color: rgba(255, 255, 255, 0.45);
            font-size: 12px;
            margin-top: 5px;
        """
        self.time_label.setStyleSheet(label_style)
        self.ip_label.setStyleSheet(label_style)
        
        info_layout.addWidget(self.time_label)
        info_layout.addWidget(self.ip_label)
        
        self.left_layout.addWidget(info_widget)

    def create_right_content(self):
        """创建右侧内容区"""
        self.right_content = QWidget()
        self.right_layout = QVBoxLayout(self.right_content)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # 顶部标题栏
        header = QWidget()
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #e8e8e8;")
        header.setFixedHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.page_title = QLabel("主页")
        self.page_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header_layout.addWidget(self.page_title)
        
        self.right_layout.addWidget(header)
        
        # 内容区域
        self.middle_section = QStackedWidget()
        self.right_layout.addWidget(self.middle_section)

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
    
    def update_btn_style(self, active_btn):
        """更新按钮样式"""
        for btn in [self.home_btn, self.project_btn, self.plc_link_btn, self.settings_btn]:
            if btn == active_btn:
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1890ff;
                        color: white;
                        border: none;
                        padding: 15px 20px;
                        text-align: left;
                        font-size: 14px;
                    }
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: rgba(255, 255, 255, 0.65);
                        border: none;
                        padding: 15px 20px;
                        text-align: left;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        color: white;
                        background-color: #1890ff;
                    }
                """)

    def show_home_page(self):
        """显示主页"""
        self.middle_section.setCurrentIndex(0)
        self.page_title.setText("主页")
        self.update_btn_style(self.home_btn)
    
    def show_project_page(self):
        """显示项目管理页面"""
        self.middle_section.setCurrentIndex(1)
        self.page_title.setText("项目管理")
        self.update_btn_style(self.project_btn)
    
    def show_plc_link_page(self):
        """显示PLC连接页面"""
        self.middle_section.setCurrentIndex(2)
        self.page_title.setText("PLC连接")
        self.update_btn_style(self.plc_link_btn)
    
    def show_settings_page(self):
        """显示设置页面"""
        self.middle_section.setCurrentIndex(3)
        self.page_title.setText("设置")
        self.update_btn_style(self.settings_btn)

    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, 'time_label'):
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