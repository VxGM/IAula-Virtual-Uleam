from __future__ import annotations

import json
import os
import socket
import time
import urllib.request
from pathlib import Path
from typing import Callable

from iaula.browsers import playwright_browser
from iaula.config import Config
from iaula.proc import popen, run

PROFILE_DIR = Path.home() / ".notebooklm" / "profiles" / "default"
STATE_PATH = PROFILE_DIR / "storage_state.json"

USER_DATA = {
    "brave": ("BraveSoftware", "Brave-Browser", "brave.exe"),
    "chrome": ("Google", "Chrome", "chrome.exe"),
    "msedge": ("Microsoft", "Edge", "msedge.exe"),
}

KEEP = ("name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite")


def user_data_dir(key: str) -> Path | None:
    vendor = USER_DATA.get(key)
    base = os.environ.get("LOCALAPPDATA")
    if vendor is None or not base:
        return None
    path = Path(base) / vendor[0] / vendor[1] / "User Data"
    return path if path.exists() else None


def process_name(key: str) -> str:
    vendor = USER_DATA.get(key)
    return vendor[2] if vendor else ""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stop_browser(name: str, log: Callable[[str], None]) -> None:
    log(f"Cerrando {name} (si está abierto)…")
    run(["taskkill", "/IM", name, "/F"], capture_output=True)
    for _ in range(15):
        out = run(["tasklist", "/FI", f"IMAGENAME eq {name}"], capture_output=True, text=True)
        if name.lower() not in (out.stdout or "").lower():
            return
        time.sleep(1)
    raise RuntimeError(f"{name} no se cerró; ciérralo a mano e intenta otra vez")


def _cookies(exe: Path, data_dir: Path, port: int) -> list[dict]:
    proc = popen([
        str(exe), f"--user-data-dir={data_dir}", f"--remote-debugging-port={port}",
        "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
        "--window-position=-32000,-32000",
    ])
    try:
        version = None
        for _ in range(30):
            try:
                version = json.load(urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/version", timeout=2))
                break
            except Exception:
                time.sleep(1)
        if not version:
            raise RuntimeError("El navegador no abrió el puerto de depuración")
        import websocket

        ws = websocket.create_connection(version["webSocketDebuggerUrl"], timeout=60)
        try:
            ws.send(json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}}))
            deadline = time.time() + 30
            while time.time() < deadline:
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    return ((msg.get("result") or {}).get("cookies") or [])
            raise RuntimeError("Sin respuesta de las cookies")
        finally:
            ws.close()
    finally:
        run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def refresh(cfg: Config, log: Callable[[str], None] = print) -> dict:
    browser = playwright_browser(cfg.browser)
    if browser is None:
        raise RuntimeError("No se detectó Brave, Chrome ni Edge instalado")
    data_dir = user_data_dir(browser.key)
    if data_dir is None:
        raise RuntimeError(f"No encuentro el perfil de {browser.name}")
    _stop_browser(process_name(browser.key), log)
    log(f"Extrayendo la sesión de Google desde {browser.name}…")

    all_cookies = _cookies(browser.path, data_dir, _free_port())
    google = [c for c in all_cookies
              if "google" in c.get("domain", "") or "youtube" in c.get("domain", "")]
    has_sid = any(c.get("name") == "SID" and c.get("domain") == ".google.com" and c.get("value")
                  for c in google)
    log(f"cookies: {len(all_cookies)} total, {len(google)} Google; SID {'OK' if has_sid else 'falta'}")
    if not has_sid:
        raise RuntimeError("No hay sesión de Google en ese navegador; inicia sesión y reintenta")

    state = {"cookies": [{k: c[k] for k in KEEP if k in c} for c in google], "origins": []}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATE_PATH.exists():
        backup = STATE_PATH.with_name(f"storage_state.json.bak-{int(time.time())}")
        backup.write_text(STATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    log("Sesión de Google guardada.")
    return {"cookies": len(google), "browser": browser.key}
