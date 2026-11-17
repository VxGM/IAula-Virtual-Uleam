from __future__ import annotations

import ctypes
import os
import sys
import threading

import webview

from iaula.config import Config, load_config, migrate_local_secrets
from iaula.gui import Handler, Jobs, LocalServer

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

APP_TITLE = "IAula Virtual — Aula ULEAM"
_MUTEX_HANDLE = None


def _single_instance() -> bool:
    """Una sola instancia (coincide con AppMutex del instalador)."""
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "IAulaVirtual")
    if not _MUTEX_HANDLE:
        return True
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


def start_server(cfg: Config, port: int = 7800) -> LocalServer:
    handler = type("BoundHandler", (Handler,), {"cfg": cfg, "jobs": Jobs()})
    httpd = None
    for candidate in range(port, port + 12):
        try:
            httpd = LocalServer(("127.0.0.1", candidate), handler)
            break
        except OSError:
            continue
    if httpd is None:
        raise RuntimeError(f"sin puerto libre entre {port} y {port + 11}")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run(cfg: Config, port: int = 7800, width: int = 1360, height: int = 900) -> int:
    if not _single_instance():
        return 0
    if migrate_local_secrets(cfg.root):
        cfg = load_config()
    httpd = start_server(cfg, port=port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    webview.create_window(APP_TITLE, url, width=width, height=height, min_size=(880, 600))
    try:
        webview.start()
    finally:
        httpd.shutdown()
    return 0
