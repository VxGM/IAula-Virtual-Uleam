from __future__ import annotations

import os
import sys
import threading
from http.server import ThreadingHTTPServer

import webview

from iaula.config import Config
from iaula.gui import Handler, Jobs

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

APP_TITLE = "IAula Virtual — Aula ULEAM"


def start_server(cfg: Config, port: int = 7800) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"cfg": cfg, "jobs": Jobs()})
    httpd = None
    for candidate in range(port, port + 12):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            break
        except OSError:
            continue
    if httpd is None:
        raise RuntimeError(f"sin puerto libre entre {port} y {port + 11}")
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run(cfg: Config, port: int = 7800, width: int = 1360, height: int = 900) -> int:
    httpd = start_server(cfg, port=port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    webview.create_window(APP_TITLE, url, width=width, height=height, min_size=(880, 600))
    try:
        webview.start()
    finally:
        httpd.shutdown()
    return 0
