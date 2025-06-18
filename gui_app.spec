# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('qc_indicators.csv', '.'), 
        ('R-4.4.2', 'R-4.4.2'), 
        ('config', 'config'), 
        ('core', 'core'), 
        ('processors', 'processors'), 
        ('r_scripts', 'r_scripts'), 
        ('utils', 'utils'),
        ('ARIMA', 'ARIMA'),
    ],
    hiddenimports=[
        'statsmodels', 
        'statsmodels.tsa.arima.model',
        'ARIMA.arima_imputation',
        'rpy2.robjects.pandas2ri',
    ],
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
    name='gui_app',
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
)
