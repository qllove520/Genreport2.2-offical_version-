# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# 方法1：使用绝对路径（推荐）
venv_site_packages = r"D:\Genreport\Genreport_0902\venv\Lib\site-packages"

# 方法2：使用相对路径（如果spec文件在项目根目录）
# venv_site_packages = os.path.join(os.getcwd(), 'venv', 'Lib', 'site-packages')

# 收集 xlwings 的所有资源文件
xlwings_datas = collect_data_files('xlwings')
xlwings_hiddenimports = collect_submodules('xlwings')

# 自定义核心文件夹
custom_datas = [
    ('config', 'config'),
    ('core', 'core'),
    ('ui', 'ui'),
]

datas = custom_datas + xlwings_datas

hiddenimports = xlwings_hiddenimports + [
    'win32com',
    'win32com.client',
    'win32com.server',
    'pythoncom',
    'pandas',
    'openpyxl',
    'openpyxl.utils',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.cell',
    'openpyxl.styles',
    'openpyxl.chart',
    'openpyxl.drawing',
    'openpyxl.image',
    'numpy',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.edge.service',
    'selenium.webdriver.edge.options',
]

a = Analysis(
    ['main.py'],
    pathex=[venv_site_packages],  # 这里填写虚拟环境的site-packages路径
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gen_py'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='验收测试报告生成工具_V2.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 如果调试可以改 True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
