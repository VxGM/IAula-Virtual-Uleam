# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

here = Path(SPECPATH)
root = here.parent

datas = [
    (str(root / "src" / "iaula" / "web"), "iaula/web"),
    (str(root / "scripts"), "scripts"),
]
datas += collect_data_files("webview")

hiddenimports = collect_submodules("webview") + [
    "pythonnet",
    "clr_loader",
    "clr_loader.util",
    "pymupdf",
    "playwright",
    "playwright.sync_api",
    "websocket",
    "win32ctypes",
]

a = Analysis(
    ["run_iaula.py"],
    pathex=[str(root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "numpy", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IAulaVirtual",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="iaula.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="IAulaVirtual",
)
