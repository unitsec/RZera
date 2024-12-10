# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('D:\\PostDoctoral\\Works\\Paper\\RZera_Series_Expansion\\submit\\RZera\\BL09_TREND/*', './CSNS_Alg/configure')]
datas += copy_metadata('numpy')


a = Analysis(
    ['mainwindow.py'],
    pathex=[],
    binaries=[('D:/anaconda3/envs/RZERA/Lib/site-packages/rongzai/libs/*', './libs')],
    datas=datas,
    hiddenimports=[],
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
    exclude_binaries=True,
    name='mainwindow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo\\resized_rzera_logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mainwindow',
)
