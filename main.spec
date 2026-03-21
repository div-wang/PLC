# -*- mode: python ; coding: utf-8 -*-


import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all

minimalmodbus_datas, minimalmodbus_binaries, minimalmodbus_hiddenimports = collect_all("minimalmodbus")
serial_datas, serial_binaries, serial_hiddenimports = collect_all("serial")

def _find_dll(name: str):
    candidates = []
    try:
        candidates.append(os.path.join(sys.base_prefix, name))
        candidates.append(os.path.join(sys.base_prefix, "DLLs", name))
        candidates.append(os.path.join(sys.base_prefix, "Library", "bin", name))
        candidates.append(os.path.join(sys.base_prefix, "Library", "usr", "bin", name))
    except Exception:
        pass
    try:
        system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        candidates.append(os.path.join(system32, name))
    except Exception:
        pass
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

runtime_binaries = []
for dll in [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "msvcp140.dll",
    "concrt140.dll",
    "ucrtbase.dll",
    "d3dcompiler_47.dll",
]:
    p = _find_dll(dll)
    if p:
        runtime_binaries.append((p, "."))

try:
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    for p in glob.glob(os.path.join(system32, "api-ms-win-crt-*.dll")):
        if os.path.isfile(p):
            runtime_binaries.append((p, "."))
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[] + minimalmodbus_binaries + serial_binaries + runtime_binaries,
    datas=[
        ('ui', 'ui'),
        ('project.json', '.'),
        ('setting.json', '.'),
    ] + minimalmodbus_datas + serial_datas,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebChannel',
        'pyecharts',
        'pyecharts.charts',
        'pyecharts.options',
        'pyecharts.globals',
        'minimalmodbus',
        'minimalmodbus.serial',
        'serial',
    ] + minimalmodbus_hiddenimports + serial_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    name='plc_monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
    exclude_binaries=True,
    win_private_assemblies=True,
    win_no_prefer_redirects=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='plc_monitor',
)
