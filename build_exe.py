
'''
Author: Div gh110827@gmail.com
Date: 2025-10-20 23:32:14
LastEditors: Div gh110827@gmail.com
LastEditTime: 2026-03-16 16:11:29
Description: 
Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
'''
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
打包脚本
将应用程序打包成Windows exe文件
使用方法：python build_exe.py
"""

import os
import sys
import shutil
import subprocess
import re
import json
from datetime import datetime

def clean_build_folders():
    """清理旧的构建文件夹"""
    folders_to_clean = ['build']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def update_version_json():
    """更新version.json的版本号为当前时间"""
    version_file = "version.json"
    now = datetime.now()
    version_str = now.strftime("%y.%m.%d%H%M")
    
    try:
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        
        data["version"] = version_str
        data["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"已更新版本号为: {version_str}")
        return version_str
    except Exception as e:
        print(f"更新version.json失败: {e}")
        return None

def get_versioned_exe_path(dist_dir: str, base_name: str) -> str:
    """生成带时间戳的exe文件名：plc_monitor.yy.mm.ddHHMM.exe"""
    now = datetime.now()
    date_str = now.strftime("%y.%m.%d%H%M")
    return os.path.join(dist_dir, f"{base_name}.{date_str}.exe")

def build_exe():
    """使用PyInstaller打包应用程序为Windows exe文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # 清理旧的构建文件
    clean_build_folders()
    
    # 更新version.json版本号
    update_version_json()
    
    # PyInstaller参数 - 针对Windows exe（需在Windows系统上运行）
    pyinstaller_args = [
        os.path.join(base_dir, 'main.spec'),
        '--distpath=dist',
        '--workpath=build',
        '--clean',
        '--noconfirm',
    ]
    
    print("开始打包Windows exe文件...")
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_args)
    except Exception:
        subprocess.check_call([sys.executable, "-m", "PyInstaller"] + pyinstaller_args)

    dist_dir = os.path.join(base_dir, "dist")
    src_exe = os.path.join(dist_dir, "plc_monitor.exe")
    dst_exe = get_versioned_exe_path(dist_dir, "plc_monitor")
    
    if not os.path.exists(src_exe):
        raise FileNotFoundError(f"未找到打包产物：{src_exe}")
    
    os.replace(src_exe, dst_exe)

    print(f"打包完成！exe文件位于 {os.path.relpath(dst_exe, base_dir)}")
    print("注意：此exe文件需要在Windows系统上运行")

if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        print(f"打包过程中出现错误：{str(e)}")
        sys.exit(1)

