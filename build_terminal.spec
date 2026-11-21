# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

work_dir = os.path.abspath(os.path.dirname(__file__) if '__file__' in locals() else '.')

datas = [
    ('dashboard.html', '.'),
    ('Match_Sniper_Capital_Proof.html', '.'),
    ('Match_Sniper_User_Manual.html', '.'),
    ('credentials.json', '.'),
]

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'fastapi',
    'fastapi.responses',
    'aiohttp',
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'websockets.legacy.client',
    'multiprocessing',
    'asyncio',
]

a = Analysis(
    ['app.py'],
    pathex=[work_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'IPython', 'torch', 'torchvision', 'torchaudio',
        'cv2', 'PIL', 'tkinter', 'transformers', 'accelerate', 'tensorboard'
    ],
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
    name='MatchSniperTerminal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='terminal.ico' if os.path.exists('terminal.ico') else None,
)
