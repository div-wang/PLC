
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动升级模块
提供版本检查、下载、安装等功能
"""

import json
import os
import sys
import requests
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import app_storage


class UpdateChecker(QThread):
    """后台检查更新线程"""
    
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, update_url: str, current_version: str):
        super().__init__()
        self.update_url = update_url
        self.current_version = current_version
    
    def run(self):
        try:
            response = requests.get(self.update_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            latest_version = data.get("version", "")
            if self._compare_versions(latest_version, self.current_version) > 0:
                self.update_available.emit(data)
            else:
                self.no_update.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，v1 > v2 返回1，v1 == v2 返回0，v1 <v2 返回-1"""
        def normalize(v):
            return [int(x) for x in v.replace("-", ".").split(".") if x.isdigit()]
        n1, n2 = normalize(v1), normalize(v2)
        for i in range(max(len(n1), len(n2))):
            a = n1[i] if i < len(n1) else 0
            b = n2[i] if i <len(n2) else 0
            if a > b:
                return 1
            if a <b:
                return -1
        return 0


class UpdateDownloader(QThread):
    """下载更新线程"""
    
    progress = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, download_url: str, save_path: str):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path
    
    def run(self):
        try:
            response = requests.get(self.download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(self.save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(downloaded * 100 / total_size)
                            self.progress.emit(progress)
            
            self.progress.emit(100)
            self.download_finished.emit(self.save_path)
        except Exception as e:
            self.download_error.emit(str(e))


class AutoUpdater:
    """自动更新管理器"""
    
    def __init__(self, version_file: str = None):
        if version_file is None:
            self.version_file = app_storage.resource_file_path("version.json")
        else:
            self.version_file = version_file
        self.current_version = self._load_current_version()
    
    def _load_current_version(self) -> str:
        """加载当前版本号"""
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("version", "1.0.0")
            except Exception:
                pass
        return "1.0.0"
    
    def save_version(self, version: str, update_url: str = ""):
        """保存版本信息"""
        data = {
            "version": version,
            "update_url": update_url,
            "updated_at": ""
        }
        try:
            with open(self.version_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件SHA256哈希"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def install_update(self, new_exe_path: str):
        """安装更新（替换当前exe）"""
        current_exe = sys.executable
        
        if not current_exe.endswith(".exe"):
            raise RuntimeError("当前不是打包后的exe，无法更新")
        
        bat_content = f'''@echo off
chcp 65001 >nul
echo 正在更新程序，请稍候...
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}"
ren "{new_exe_path}" "{os.path.basename(current_exe)}"
start "" "{current_exe}"
del /f /q "%~f0"
'''
        
        bat_path = os.path.join(os.path.dirname(current_exe), "update.bat")
        with open(bat_path, "w", encoding="gbk") as f:
            f.write(bat_content)
        
        subprocess.Popen([bat_path], shell=True, cwd=os.path.dirname(current_exe))
        sys.exit(0)

