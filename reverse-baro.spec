# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for reverse-baro (PySide6 desktop GUI).

Build:
    pyinstaller --clean reverse-baro.spec

Run:
    dist\\reverse-baro\\reverse-baro.exe

Why --onedir (COLLECT, not single-file):
  - Instant startup (no temp-extraction on every launch)
  - No AV false-positive extraction delays
  - Qt platform plugins (qwindows.dll) resolve cleanly
  - Zip the dist/ folder for distribution — still a few MBs
"""

import os

# Spec files are executed via exec() so __file__ may not be set.
# PyInstaller always runs from the spec file's directory.
here = os.getcwd()
src_dir  = os.path.join(here, "src")
assets   = os.path.join(here, "assets")

# ── Modules to exclude to keep the bundle small ──
excluded = [
    # Heavy PySide6 modules we never import
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtAxContainer", "PySide6.QtBluetooth",
    "PySide6.QtCharts", "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization", "PySide6.QtDBus", "PySide6.QtDesigner",
    "PySide6.QtGraphs", "PySide6.QtGraphsWidgets", "PySide6.QtHelp",
    "PySide6.QtHttpServer", "PySide6.QtLocation",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork", "PySide6.QtNetworkAuth", "PySide6.QtNfc",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2", "PySide6.QtQuickTest", "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSensors",
    "PySide6.QtSerialBus", "PySide6.QtSerialPort", "PySide6.QtSpatialAudio",
    "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.QtXml",
    # Unneeded stdlib
    "setuptools", "pip", "wheel", "tkinter", "unittest", "doctest",
    "pydoc", "lib2to3", "distutils", "idlelib", "ensurepip",
]

# ── Analysis ──
a = Analysis(
    [os.path.join(src_dir, "gui.py")],
    pathex=[src_dir],
    binaries=[],
    datas=[
        (os.path.join(assets, "app_icon.ico"), "assets"),
        (os.path.join(assets, "app_icon.png"), "assets"),
    ],
    hiddenimports=[
        "parser", "parser.data", "parser.decode", "parser.parse", "parser.parser",
    ],
    hookspath=[],
    excludes=excluded,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_bin=False,
    name="reverse-baro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(assets, "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="reverse-baro",
)
