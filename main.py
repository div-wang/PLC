'''
Author: Div gh110827@gmail.com
Date: 2025-12-29 10:07:51
LastEditors: Div gh110827@gmail.com
LastEditTime: 2026-03-16 15:08:20
Description: 
Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
'''
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
from jy500 import JY500Page

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
    app.setOrganizationName("PLCApp")
    app.setApplicationName("plc_monitor")
    
    # 创建主窗口
    main_window = BaseUI()
    
    # 创建各页面
    home_page = HomePage()
    project_page = ProjectPage()
    plc_link_page = PLCLinkPage()
    setting_page = SettingPage()
    jy500_page = JY500Page()
    
    # 添加页面到主窗口
    main_window.add_page(home_page.get_page(), "home")
    main_window.add_page(project_page.get_page(), "project")
    main_window.add_page(plc_link_page.get_page(), "plc_link")
    main_window.add_page(setting_page.get_page(), "setting")
    main_window.add_page(jy500_page.get_page(), "jy500")
    
    # 显示主窗口
    main_window.show()
    
    # 启动应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
