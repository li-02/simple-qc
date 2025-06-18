# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 获取Python环境路径
PYTHON_PATH = sys.executable
PYTHON_DIR = os.path.dirname(PYTHON_PATH)

# R环境路径 - 使用项目内置的R环境
R_PATH = os.path.join(os.path.dirname(os.path.abspath('.')), 'R-4.4.2')

# 设置R_HOME环境变量
os.environ['R_HOME'] = R_PATH
os.environ['R_USER'] = os.path.expanduser('~')

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[PYTHON_DIR],
    binaries=[
        # 包含项目内置的R环境
        ('R-4.4.2', 'R-4.4.2'),
    ],
    datas=[
        # 包含项目文件 - 新增ARIMA目录
        ('core', 'core'),
        ('utils', 'utils'), 
        ('config', 'config'),
        ('processors', 'processors'),
        ('r_scripts', 'r_scripts'),
        ('ARIMA', 'ARIMA'),  # 新增ARIMA目录
        # QC指标文件
        ('qc_indicators.csv', '.'),
    ],
    hiddenimports=[
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'seaborn',
        'rpy2',
        'rpy2.robjects',
        'rpy2.robjects.pandas2ri',
        'rpy2.robjects.conversion',
        'PyQt5',
        'openpyxl',
        'PyInstaller',
        # 新增ARIMA相关依赖
        'statsmodels',
        'statsmodels.tsa',
        'statsmodels.tsa.arima',
        'statsmodels.tsa.arima.model',
        'statsmodels.tsa.stattools',
        'statsmodels.graphics',
        'statsmodels.graphics.tsaplots',
        'statsmodels.tsa.seasonal',
        'ARIMA',
        'ARIMA.arima_imputation',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='SimpleQC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SimpleQC',
)