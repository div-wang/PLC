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
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from ui.base_ui import BaseUI
from auth import AuthManager, LoginDialog
from home import HomePage
from project import ProjectPage
from plc_link import PLCLinkPage
from setting import SettingPage
from modbus import ModbusPage
import db


def _on_logout(main_window: BaseUI, auth: AuthManager, modbus_page: ModbusPage, home_page: HomePage) -> None:
    auth.logout()
    try:
        modbus_page.set_user_role("user")
    except Exception:
        pass
    try:
        main_window.set_user_role("user")
    except Exception:
        pass
    ok = _ensure_login(main_window, auth, modbus_page, home_page)
    if not ok:
        main_window.close()


def _on_login_success(main_window: BaseUI, auth: AuthManager, modbus_page: ModbusPage, home_page: HomePage) -> None:
    try:
        modbus_page.set_user_role(auth.role())
    except Exception:
        pass
    try:
        main_window.set_user_role(auth.role())
    except Exception:
        pass
    try:
        modbus_page.set_status_callback(lambda s: main_window.set_modbus_status(s))
        modbus_page.start_auto_connect(max_attempts=5, interval_ms=2000)
    except Exception:
        pass
    try:
        main_window.set_next_ring_handler(lambda: modbus_page.next_ring())
    except Exception:
        pass
    try:
        main_window.set_prev_ring_handler(lambda: modbus_page.prev_ring())
    except Exception:
        pass
    try:
        modbus_page.set_ring_callback(lambda n: main_window.set_current_ring_no(n))
        modbus_page.set_clear_ring_callback(lambda: home_page.update_data())
        from modbus import _active_project_id
        pid = _active_project_id()
        n = db.max_ring_no(str(pid))
        main_window.set_current_ring_no(0 if n is None else int(n))
    except Exception:
        pass
    try:
        main_window.set_home_shown_handler(
            lambda: (
                main_window.set_modbus_status("connecting"),
                modbus_page.start_auto_connect(max_attempts=5, interval_ms=2000),
            )
            if main_window.modbus_status_state() == "failed"
            else None
        )
    except Exception:
        pass
    main_window.show_home_page()


def _ensure_login(main_window: BaseUI, auth: AuthManager, modbus_page: ModbusPage, home_page: HomePage) -> bool:
    if auth.restore_session():
        _on_login_success(main_window, auth, modbus_page, home_page)
        return True

    mask = QWidget(main_window)
    mask.setStyleSheet("background: rgba(0,0,0,160);")
    mask.setGeometry(main_window.rect())
    mask.show()
    mask.raise_()

    dlg = LoginDialog(main_window, auth)
    dlg.setWindowModality(Qt.ApplicationModal)
    try:
        fg = dlg.frameGeometry()
        center = main_window.frameGeometry().center()
        fg.moveCenter(center)
        dlg.move(fg.topLeft())
    except Exception:
        pass

    ok = dlg.exec_() == dlg.Accepted
    try:
        mask.hide()
        mask.deleteLater()
    except Exception:
        pass
    if not ok:
        return False
    _on_login_success(main_window, auth, modbus_page, home_page)
    return True


def main():
    """主函数"""
    # 单实例运行检测
    import win32event
    import win32api
    from winerror import ERROR_ALREADY_EXISTS
    mutex = win32event.CreateMutex(None, False, "PLC_Monitor_App_Mutex")
    if win32api.GetLastError() == ERROR_ALREADY_EXISTS:
        win32api.MessageBox(0, "程序已经在运行中，请勿重复打开！", "提示", 0x40 | 0x1)
        return

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
    try:
        db.init_db()
        db.migrate_ring_records_json_if_needed()
    except Exception:
        pass

    auth = AuthManager()
    
    # 创建各页面
    main_window = BaseUI()
    main_window.set_auth(auth)

    modbus_page = ModbusPage(user_role=auth.role())
    home_page = HomePage()
    project_page = ProjectPage()
    plc_link_page = PLCLinkPage()
    setting_page = SettingPage(on_logout=lambda: _on_logout(main_window, auth, modbus_page, home_page))
    
    # 添加页面到主窗口
    main_window.add_page(home_page.get_page(), "home")
    main_window.add_page(project_page.get_page(), "project")
    main_window.add_page(plc_link_page.get_page(), "plc_link")
    main_window.add_page(setting_page.get_page(), "setting")
    main_window.add_page(modbus_page.get_page(), "modbus")

    main_window.set_login_handler(lambda: _ensure_login(main_window, auth, modbus_page, home_page))

    # 显示主窗口
    main_window.show()

    if not auth.restore_session():
        ok = _ensure_login(main_window, auth, modbus_page, home_page)
        if not ok:
            sys.exit(0)
    else:
        _on_login_success(main_window, auth, modbus_page, home_page)
    
    # 启动应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
