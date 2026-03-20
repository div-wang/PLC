# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_all

minimalmodbus_datas, minimalmodbus_binaries, minimalmodbus_hiddenimports = collect_all("minimalmodbus")
serial_datas, serial_binaries, serial_hiddenimports = collect_all("serial")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
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
    a.binaries,
    a.datas,
    [],
    name='plc_monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
