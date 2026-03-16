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
import PyInstaller.__main__

def clean_build_folders():
    """清理旧的构建文件夹"""
    folders_to_clean = ['build', 'dist']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def build_exe():
    """使用PyInstaller打包应用程序为Windows exe文件"""
    # 清理旧的构建文件
    clean_build_folders()
    
    # PyInstaller参数 - 针对Windows exe（需在Windows系统上运行）
    pyinstaller_args = [
        'main.spec',
        '--distpath=dist',  # 指定输出目录
        '--workpath=build',  # 指定工作目录
        '--clean',  # 清理临时文件
        '--noconfirm',  # 不询问确认
    ]
    
    print("开始打包Windows exe文件...")
    
    # 运行PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)

    print("打包完成！exe文件位于 dist/plc_monitor.exe")
    print("注意：此exe文件需要在Windows系统上运行")

if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        print(f"打包过程中出现错误：{str(e)}")
        sys.exit(1)
