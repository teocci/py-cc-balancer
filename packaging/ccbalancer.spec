# -*- mode: python ; coding: utf-8 -*-
'''PyInstaller one-dir spec for the ccbalancer portable bundle.

Build from the repo root:

    pyinstaller packaging/ccbalancer.spec

Produces ``dist/ccbalancer/`` containing the launcher (``ccbalancer`` /
``ccbalancer.exe``) plus an ``_internal/`` payload. Zip the whole folder for
distribution; the user extracts and runs the launcher — no Python required.

Bundling notes:
    * ``ccxt`` ships per-exchange data files and lazily imports exchange
      modules, so ``collect_all`` is required to pull data + submodules.
    * ``keyring`` resolves its OS secret backends through entry-point metadata,
      which a frozen build otherwise drops. We collect the package, copy its
      distribution metadata, and pin the platform backends as hidden imports so
      the keyring credential store keeps working in the bundle (the file-backed
      fallback works regardless).
'''

import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SRC = os.path.join(ROOT, 'src')
ENTRY = os.path.join(SRC, 'ccbalancer', '__main__.py')

datas = []
binaries = []
hiddenimports = []

for package in ('ccxt', 'keyring'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# keyring discovers backends via entry points — preserve metadata and pin the
# per-OS backends so the bundle never falls back to a no-op keyring.
datas += copy_metadata('keyring')
hiddenimports += [
    'keyring.backends.Windows',
    'keyring.backends.macOS',
    'keyring.backends.SecretService',
    'keyring.backends.chainer',
    'keyring.backends.fail',
]

a = Analysis(
    [ENTRY],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pytest_mock', '_pytest', 'PyInstaller'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ccbalancer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
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
    upx=False,
    upx_exclude=[],
    name='ccbalancer',
)
