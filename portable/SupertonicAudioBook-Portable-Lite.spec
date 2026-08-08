# -*- mode: python ; coding: utf-8 -*-
#
# Variante "Lite": el instalador NO incluye el modelo TTS.
# Al primer uso, la app lo descarga sola a la carpeta modelo/ junto al exe.
# El origen del payload se toma de la variable de entorno SUPERTONIC_APP_DIST
# (la prepara build_portables.py). Si no está definida, apunta al staging_lite
# creado por ese mismo script.

import os

_APP_DIST = os.environ.get(
    "SUPERTONIC_APP_DIST",
    r"C:\Users\rafae\Music\Supertonic\portable\staging_lite\SupertonicAudioBook",
)

a = Analysis(
    ['instalador_portable.py'],
    pathex=[],
    binaries=[],
    datas=[(_APP_DIST, 'SupertonicAudioBook')],
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
    a.binaries,
    a.datas,
    [],
    name='SupertonicAudioBook-Portable-Lite',
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
