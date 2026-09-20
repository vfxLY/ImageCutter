# -*- mode: python ; coding: utf-8 -*-

import os

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义资源文件的路径
resource_paths = [
    ('src/res', 'res'),  # 假设资源文件在 src/res 目录下
    ('src/icon.ico', '.'),  # 假设图标文件在 src 目录下
]

# 定义数据文件的路径
data_paths = []

# 定义隐藏导入的模块
hidden_imports = [
    'cv2',
    'torch',
    'yolov5',
    'myutils.myutils',
    'myutils.respath',
    'image_processing.image',
    'image_processing.model',
    'image_processing.panel',
    'gui.base_window_ui',
    'gui.splash_screen_ui',
    'gui.extractor',
    'gui.base_window',
    'gui.splash_screen',
]

a = Analysis(
    ['src\\main.py'],
    pathex=[current_dir],  # 添加当前目录到搜索路径
    binaries=[],
    datas=resource_paths + data_paths,  # 添加资源和数据文件
    hiddenimports=hidden_imports,  # 添加隐藏导入的模块
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)