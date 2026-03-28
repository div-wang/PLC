
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置模块
负责系统设置相关功能
"""

import os
import json
import codecs
import zipfile
from datetime import datetime, timedelta
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSettings, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWidgets import QFileDialog, QMessageBox

import app_storage
from auto_update import AutoUpdater, UpdateChecker, UpdateDownloader


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


class SettingPage:
    """设置页面类"""
    
    def __init__(self, on_logout=None):
        self.page = QWebEngineView()
        self.bridge = SettingsBridge(on_logout=on_logout)
        self.channel = QWebChannel(self.page.page())
        self.channel.registerObject('bridge', self.bridge)
        self.page.page().setWebChannel(self.channel)
        
        self.updater = AutoUpdater()
        self._checker = None
        self._downloader = None
        self._update_data = None
        
        self.generate_setting_page()
        
        self.bridge.load_version_info_requested.connect(self._on_load_version_info)
        self.bridge.check_update_requested.connect(self._on_check_update)
        self.bridge.check_update_on_load_requested.connect(self._on_check_update_on_load)
        self.bridge.download_update_requested.connect(self._on_download_update)
        self.bridge.install_update_requested.connect(self._on_install_update)
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def load_settings(self):
        """从JSON文件加载设置"""
        template = _load_setting_template()
        user = app_storage.load_json("setting.json", {})
        if not isinstance(user, dict):
            user = {}
        merged = _deep_merge(template, user)
        if merged != user:
            try:
                app_storage.save_json("setting.json", merged)
            except Exception:
                pass
        return merged

    def generate_setting_page(self):
        """生成设置页面内容"""
        settings = self.load_settings()
        
        setting_html_path = app_storage.resource_file_path("ui/setting_page.html")
        if os.path.exists(setting_html_path):
            with open(setting_html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            html_content = html_content.replace('themeSelect.value = "浅色";', f'themeSelect.value = "{settings["theme"]}";')
            html_content = html_content.replace('id="refreshInterval" value="5"', f'id="refreshInterval" value="{settings["refresh_interval"]}"')
            html_content = html_content.replace('id="autoSaveLogs" >', f'id="autoSaveLogs" {"checked" if settings["auto_save_logs"] else ""}>')
            html_content = html_content.replace('id="enableNotifications" >', f'id="enableNotifications" {"checked" if settings["enable_notifications"] else ""}>')
            
            version = self.updater.current_version
            
            html_content = html_content.replace('<span id="currentVersion">1.0.0</span>', f'<span id="currentVersion">{version}</span>')
            html_content = html_content.replace('PLC监控系统 - 版本 1.0.0', f'PLC监控系统 - 版本 {version}')
            
            temp_html_path = os.path.join(app_storage.ui_cache_dir(), "setting_page.html")
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            self.page.load(QUrl.fromLocalFile(temp_html_path))
    
    def _on_load_version_info(self):
        """加载版本信息"""
        version = self.updater.current_version
        update_url = ""
        try:
            setting_file = app_storage.resource_file_path("setting.json")
            with open(setting_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                update_url = data.get("update_url", "")
        except Exception:
            pass
        self.bridge.load_version_info.emit(version, update_url)
    
    def _on_check_update_on_load(self):
        """页面加载时检查更新"""
        update_url = ""
        try:
            setting_file = app_storage.resource_file_path("setting.json")
            with open(setting_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                update_url = data.get("update_url", "")
        except Exception:
            pass
        
        if update_url:
            self._on_check_update(update_url)
    
    def _on_check_update(self, update_url: str):
        """检查更新"""
        self._checker = UpdateChecker(update_url, self.updater.current_version)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.error_occurred.connect(self._on_update_error)
        self._checker.start()
    
    def _on_update_available(self, data: dict):
        """发现新版本"""
        self._update_data = data
        version = data.get("version", "")
        download_url = data.get("download_url", "")
        release_notes = data.get("release_notes", "")
        self.bridge.update_available.emit(version, download_url, release_notes)
    
    def _on_no_update(self):
        """没有新版本"""
        self.bridge.no_update_available.emit()
    
    def _on_update_error(self, error_msg: str):
        """更新检查错误"""
        self.bridge.update_error.emit(error_msg)
    
    def _on_download_update(self, download_url: str):
        """下载更新"""
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plc_monitor_update.exe")
        self._downloader = UpdateDownloader(download_url, save_path)
        self._downloader.progress.connect(self._on_download_progress)
        self._downloader.download_finished.connect(self._on_download_finished)
        self._downloader.download_error.connect(self._on_download_error)
        self._downloader.start()
    
    def _on_download_progress(self, progress: int):
        """下载进度"""
        self.bridge.download_progress.emit(progress)
    
    def _on_download_finished(self, file_path: str):
        """下载完成"""
        self.bridge.download_finished.emit()
    
    def _on_download_error(self, error_msg: str):
        """下载错误"""
        self.bridge.download_error.emit(error_msg)
    
    def _on_install_update(self):
        """安装更新"""
        try:
            new_exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plc_monitor_update.exe")
            if not os.path.exists(new_exe_path):
                QMessageBox.warning(None, "更新", "更新文件不存在")
                return
            self.updater.install_update(new_exe_path)
        except Exception as e:
            QMessageBox.warning(None, "更新", f"更新失败: {e}")


class SettingsBridge(QObject):
    """设置页面桥接类"""
    
    load_version_info_requested = pyqtSignal()
    check_update_requested = pyqtSignal(str)
    check_update_on_load_requested = pyqtSignal()
    download_update_requested = pyqtSignal(str)
    install_update_requested = pyqtSignal()
    
    load_version_info = pyqtSignal(str, str)
    update_available = pyqtSignal(str, str, str)
    no_update_available = pyqtSignal()
    update_error = pyqtSignal(str)
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, on_logout=None):
        super().__init__()
        self._on_logout = on_logout

    @pyqtSlot(str, int, bool, bool)
    def saveSettings(self, theme, refresh_interval, auto_save_logs, enable_notifications):
        """保存设置到JSON文件"""
        existing = app_storage.load_json("setting.json", {})
        if not isinstance(existing, dict):
            existing = {}
        existing["theme"] = theme
        existing["refresh_interval"] = refresh_interval
        existing["auto_save_logs"] = auto_save_logs
        existing["enable_notifications"] = enable_notifications

        try:
            app_storage.save_json("setting.json", existing)
        except Exception as e:
            print(f"Error saving settings: {e}")

    @pyqtSlot()
    def logout(self):
        try:
            if callable(self._on_logout):
                self._on_logout()
        except Exception:
            pass

    @pyqtSlot()
    def exportLogs(self):
        try:
            base = app_storage.logs_dir()
            default_name = f"logs_{datetime.now().strftime('%Y%m%d')}.zip"
            dst, _ = QFileDialog.getSaveFileName(None, "导出日志", default_name, "Zip (*.zip)")
            if not dst:
                return
            if not dst.lower().endswith(".zip"):
                dst = dst + ".zip"
            cutoff = datetime.now() - timedelta(days=30)
            files = []
            for name in os.listdir(base):
                if not name.endswith(".log"):
                    continue
                stem = name[:-4]
                try:
                    dt = datetime.strptime(stem, "%Y-%m-%d")
                except Exception:
                    continue
                if dt >= cutoff:
                    files.append(os.path.join(base, name))
            with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for p in files:
                    z.write(p, arcname=os.path.basename(p))
            QMessageBox.information(None, "导出日志", f"已导出 {len(files)} 个日志文件。")
        except Exception as e:
            try:
                QMessageBox.warning(None, "导出日志", f"导出失败: {e}")
            except Exception:
                pass
    
    @pyqtSlot()
    def loadVersionInfoRequested(self):
        self.load_version_info_requested.emit()
    
    @pyqtSlot(str)
    def checkUpdate(self, update_url):
        self.check_update_requested.emit(update_url)
    
    @pyqtSlot()
    def checkUpdateOnLoad(self):
        self.check_update_on_load_requested.emit()
    
    @pyqtSlot(str)
    def downloadUpdate(self, download_url):
        self.download_update_requested.emit(download_url)
    
    @pyqtSlot()
    def installUpdate(self):
        self.install_update_requested.emit()

