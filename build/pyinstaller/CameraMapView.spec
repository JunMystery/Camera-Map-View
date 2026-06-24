# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Git\\Camera-Map-View\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Git\\Camera-Map-View\\assets', 'assets'), ('C:\\Git\\Camera-Map-View\\config', 'config')],
    hiddenimports=['PyQt6.QtSvg', 'PyQt6.QtPrintSupport', 'PIL', 'cv2', 'ping3', 'aiohttp'],
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
    name='CameraMapView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CameraMapView',
)
