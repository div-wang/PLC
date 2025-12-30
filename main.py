#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口
整合所有UI组件并启动应用
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from ui.base_ui import BaseUI
from home import HomePage
from project import ProjectPage
from plc_link import PLCLinkPage
from setting import SettingPage

def main():
    """主函数"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # 创建主窗口
    main_window = BaseUI()
    
    # 创建各页面
    home_page = HomePage()
    project_page = ProjectPage()
    plc_link_page = PLCLinkPage()
    setting_page = SettingPage()
    
    # 添加页面到主窗口
    main_window.add_page(home_page.get_page(), "home")
    main_window.add_page(project_page.get_page(), "project")
    main_window.add_page(plc_link_page.get_page(), "plc_link")
    main_window.add_page(setting_page.get_page(), "setting")
    
    # 显示主窗口
    main_window.show()
    
    # 启动应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
