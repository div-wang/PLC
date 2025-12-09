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
import PyInstaller.__main__

def clean_build_folders():
    """清理旧的构建文件夹"""
    folders_to_clean = ['build', 'dist']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    spec_file = 'plc_monitor.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)

def copy_ui_files():
    """复制UI文件到dist目录"""
    ui_folder = os.path.join('dist', 'ui')
    if not os.path.exists(ui_folder):
        os.makedirs(ui_folder)
    
    # 复制所有HTML文件
    src_ui_folder = 'ui'
    for file in os.listdir(src_ui_folder):
        if file.endswith('.html'):
            src_file = os.path.join(src_ui_folder, file)
            dst_file = os.path.join(ui_folder, file)
            shutil.copy2(src_file, dst_file)

def build_exe():
    """使用PyInstaller打包应用程序为Windows exe文件"""
    # 清理旧的构建文件
    clean_build_folders()
    
    # PyInstaller参数 - 针对Windows exe
    pyinstaller_args = [
        'main.py',  # 主程序入口
        '--name=plc_monitor',  # 输出文件名
        '--onefile',  # 打包成单个exe文件
        '--windowed',  # 不显示控制台窗口
        '--add-data=ui:ui',  # 添加UI文件夹 (使用冒号分隔符)
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtWebEngineWidgets',
        '--hidden-import=pyecharts',
        '--hidden-import=pyecharts.charts',
        '--hidden-import=pyecharts.options',
        '--hidden-import=pyecharts.globals',
        '--distpath=dist',  # 指定输出目录
        '--workpath=build',  # 指定工作目录
        '--clean',  # 清理临时文件
        '--noconfirm',  # 不询问确认
    ]
    
    print("开始打包Windows exe文件...")
    
    # 运行PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)
    
    # 复制必要的UI文件到exe同目录
    copy_ui_files()
    
    print("打包完成！exe文件位于 dist/plc_monitor.exe")
    print("注意：此exe文件需要在Windows系统上运行")

if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        print(f"打包过程中出现错误：{str(e)}")
        sys.exit(1)