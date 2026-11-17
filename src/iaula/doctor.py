"""Diagnóstico de dependencias y entorno de IAula.

Se ejecuta al abrir el panel, desde la vista Diagnóstico y con `iaula doctor`.
Cada chequeo devuelve un estado (`ok`, `warn`, `error`, `skip`) y una pista de
arreglo. Solo los ítems con `fatal=True` bloquean la app.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable

import requests

from iaula import secrets
from iaula.config import Config
from iaula.proc import run

Log = Callable[[str], None]

_SESSION_MAX_AGE = 7 * 86400
_MIN_DISK_OK = 500 * 1024 * 1024
_MIN_DISK_ERROR = 100 * 1024 * 1024
_CORE_MODULES = (("requests", "requests"), ("bs4", "beautifulsoup4"), ("fitz", "pymupdf"))


def _item(item_id: str, label: str, status: str, detail: str = "", hint: str = "",
          fatal: bool = False, fixable: bool = False) -> dict:
    return {
        "id": item_id,
        "label": label,
        "status": status,
        "detail": detail,
        "hint": hint,
        "fatal": fatal,
        "fixable": fixable,
    }


def _found(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _check_runtime() -> dict:
    ok = sys.version_info >= (3, 11)
    frozen = bool(getattr(sys, "frozen", False))
    return _item(
        "runtime", "Entorno de ejecución",
        "ok" if ok else "error",
        f"Python {sys.version.split()[0]}" + (" (empaquetado)" if frozen else ""),
        "" if ok else "Instala Python 3.11 o superior.",
        fatal=not ok,
    )


def _check_deps() -> dict:
    missing = [pkg for mod, pkg in _CORE_MODULES if not _found(mod)]
    if missing:
        return _item(
            "deps", "Paquetes de Python", "error",
            "Faltan: " + ", ".join(missing),
            "Reinstala con: pip install -e \".[dev]\"",
            fatal=True,
        )
    if not _found("playwright"):
        return _item(
            "deps", "Paquetes de Python", "warn",
            "Falta playwright (login y NotebookLM).",
            "Reinstala con: pip install -e \".[dev]\"",
        )
    return _item("deps", "Paquetes de Python", "ok", "Todo instalado.")


def _check_webview2() -> dict:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return _item("webview2", "WebView2 (ventana de escritorio)", "skip",
                     "Solo aplica a la app instalada en Windows.")
    import winreg

    key = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    found = False
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\" + key[9:]),
                       (winreg.HKEY_CURRENT_USER, key)):
        try:
            with winreg.OpenKey(hive, path):
                found = True
                break
        except OSError:
            continue
    if found:
        return _item("webview2", "WebView2 (ventana de escritorio)", "ok", "Instalado.")
    return _item(
        "webview2", "WebView2 (ventana de escritorio)", "warn",
        "No detectado; el panel puede abrirse en el navegador.",
        "Vuelve a ejecutar el instalador de IAula para repararlo.",
    )


def _check_browser() -> dict:
    from iaula.browsers import detect_browsers

    browsers = detect_browsers()
    names = [b.name for b in browsers]
    chromium = [b for b in browsers if b.key in ("brave", "chrome", "msedge")]
    if chromium:
        return _item("browser", "Navegador para el aula", "ok", ", ".join(names))
    if browsers:
        return _item("browser", "Navegador para el aula", "warn",
                     "Solo " + ", ".join(names) + " (Playwright necesita Chromium).",
                     "Instala Brave, Chrome o Edge.")
    return _item("browser", "Navegador para el aula", "warn",
                 "No encontré Brave, Chrome ni Edge.",
                 "Instala uno, o deja que IAula descargue su navegador interno.")


def _playwright_root() -> Path:
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env and env != "0":
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "ms-playwright"


def _check_chromium(cfg: Config) -> dict:
    from iaula.browsers import playwright_browser

    installed = playwright_browser(cfg.browser)
    if installed:
        return _item("chromium", "Navegador interno", "ok",
                     f"Se usará {installed.name} instalado en el sistema.")
    root = _playwright_root()
    patterns = ("chromium-*/chrome-win/chrome.exe", "chromium-*/chrome-linux/chrome",
                "chromium_headless_shell-*/chrome-win/headless_shell.exe")
    for pattern in patterns:
        try:
            if any(root.glob(pattern)):
                return _item("chromium", "Navegador interno", "ok", str(root))
        except OSError:
            continue
    return _item(
        "chromium", "Navegador interno", "warn",
        "Aún no está descargado (≈180 MB, una sola vez).",
        "Descárgalo para poder iniciar sesión y usar NotebookLM sin depender de tu navegador.",
        fixable=True,
    )


def _check_portal_config(cfg: Config) -> dict:
    if cfg.portal.username and cfg.portal.password:
        return _item("portal_config", "Cuenta de la ULEAM", "ok", cfg.portal.username)
    return _item("portal_config", "Cuenta de la ULEAM", "warn",
                 "Falta usuario o contraseña del aula.",
                 "Complétalos en Ajustes → Cuenta del aula.")


def _check_session(cfg: Config) -> dict:
    path = cfg.root / "data" / "session.json"
    if not path.exists():
        return _item("session", "Sesión del aula", "warn",
                     "Sin sesión guardada.",
                     "Pulsa Revisar ahora para iniciar sesión.")
    age = time.time() - path.stat().st_mtime
    days = int(age // 86400)
    if age > _SESSION_MAX_AGE:
        return _item("session", "Sesión del aula", "warn",
                     f"Guardada hace {days} días; puede haber caducado.",
                     "Si falla, vuelve a conectar el aula.", fixable=True)
    return _item("session", "Sesión del aula", "ok", f"Guardada hace {days} día(s).")


def _check_network(cfg: Config, network: bool) -> dict:
    if not network:
        return _item("network", "Conexión con el aula", "skip", "Comprobación omitida.")
    base = cfg.portal.base_url.rstrip("/")
    try:
        r = requests.get(base + "/", timeout=5, allow_redirects=True)
    except requests.RequestException as exc:
        return _item("network", "Conexión con el aula", "error",
                     f"No pude conectar: {exc.__class__.__name__}",
                     "Revisa tu conexión a Internet o el firewall.")
    return _item("network", "Conexión con el aula", "ok",
                 f"HTTP {r.status_code} en {base}")


def _existing(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return Path.cwd()


def _check_disk(cfg: Config) -> dict:
    usage = shutil.disk_usage(_existing(Path(cfg.root)))
    free = usage.free
    gib = free / (1024 ** 3)
    try:
        probe = Path(cfg.root) / "data"
        probe.mkdir(parents=True, exist_ok=True)
        test = probe / ".write-test"
        test.write_bytes(b"ok")
        test.unlink(missing_ok=True)
    except OSError:
        return _item("disk", "Espacio y permisos", "error",
                     "No puedo escribir en la carpeta de datos.",
                     "Revisa los permisos de %LOCALAPPDATA%\\IAulaVirtual.", fatal=True)
    if free < _MIN_DISK_ERROR:
        return _item("disk", "Espacio y permisos", "error",
                     f"Solo {gib:.1f} GB libres.", "Libera espacio en disco.", fatal=True)
    if free < _MIN_DISK_OK:
        return _item("disk", "Espacio y permisos", "warn",
                     f"{gib:.1f} GB libres; las descargas pueden no caber.",
                     "Libera espacio antes de descargar cursos completos.")
    return _item("disk", "Espacio y permisos", "ok", f"{gib:.1f} GB libres.")


def _check_secrets(cfg: Config) -> dict:
    method = secrets.method(cfg.root)
    if method == "dpapi":
        return _item("secrets", "Bóveda de credenciales", "ok", "Cifrada con DPAPI.")
    return _item(
        "secrets", "Bóveda de credenciales", "warn",
        "En este sistema los secretos se guardan con permisos 0600, sin cifrar.",
        "En Windows usa la app instalada para cifrarlos con DPAPI.",
    )


def _check_legacy_key() -> dict:
    candidates = [
        Path(sys.executable).parent / "bundled_key.txt",
        Path(__file__).resolve().parent / "bundled_key.txt",
    ]
    for path in candidates:
        if path.exists():
            return _item(
                "legacy_key", "Claves antiguas", "warn",
                "Hay una clave en texto plano en " + str(path),
                "Se migra a la bóveda y se borra al iniciar.",
                fixable=True,
            )
    return _item("legacy_key", "Claves antiguas", "ok", "Sin claves en texto plano.")


def _check_ai(cfg: Config) -> dict:
    if cfg.chat.api_key:
        return _item("ai", "Asistente IA", "ok", f"{cfg.chat.model} · {cfg.chat.base_url}")
    return _item("ai", "Asistente IA", "warn",
                 "Sin clave configurada; el Asistente está apagado.",
                 "Añade tu clave en Ajustes → Asistente IA.")


def _check_notebooklm() -> dict:
    exe = shutil.which("notebooklm")
    if exe:
        return _item("notebooklm", "NotebookLM", "ok", "CLI disponible.")
    return _item("notebooklm", "NotebookLM", "warn",
                 "CLI de NotebookLM no encontrado (opcional).",
                 "Instálalo con: pip install notebooklm")


def _check_daily_task() -> dict:
    if sys.platform != "win32":
        return _item("daily_task", "Revisión diaria", "skip", "Solo Windows.")
    try:
        p = run(["schtasks", "/Query", "/TN", "IAula-Check"],
                capture_output=True, text=True, timeout=10)
    except Exception:
        return _item("daily_task", "Revisión diaria", "skip", "No pude consultarla.")
    if p.returncode == 0:
        return _item("daily_task", "Revisión diaria", "ok", "Tarea IAula-Check activa.")
    return _item("daily_task", "Revisión diaria", "skip",
                 "Opcional; no configurada.")


def _safe(check: Callable[[], dict], item_id: str, label: str) -> dict:
    try:
        return check()
    except Exception as exc:
        return _item(item_id, label, "warn", f"No pude comprobarlo: {exc.__class__.__name__}")


def check_all(cfg: Config, network: bool = True) -> dict:
    items = [
        _safe(_check_runtime, "runtime", "Entorno de ejecución"),
        _safe(_check_deps, "deps", "Paquetes de Python"),
        _safe(_check_webview2, "webview2", "WebView2"),
        _safe(_check_browser, "browser", "Navegador para el aula"),
        _safe(lambda: _check_chromium(cfg), "chromium", "Navegador interno"),
        _safe(lambda: _check_portal_config(cfg), "portal_config", "Cuenta de la ULEAM"),
        _safe(lambda: _check_session(cfg), "session", "Sesión del aula"),
        _safe(lambda: _check_network(cfg, network), "network", "Conexión con el aula"),
        _safe(lambda: _check_disk(cfg), "disk", "Espacio y permisos"),
        _safe(lambda: _check_secrets(cfg), "secrets", "Bóveda de credenciales"),
        _safe(_check_legacy_key, "legacy_key", "Claves antiguas"),
        _safe(lambda: _check_ai(cfg), "ai", "Asistente IA"),
        _safe(_check_notebooklm, "notebooklm", "NotebookLM"),
        _safe(_check_daily_task, "daily_task", "Revisión diaria"),
    ]
    summary = {"ok": 0, "warn": 0, "error": 0, "skip": 0}
    for item in items:
        summary[item["status"]] = summary.get(item["status"], 0) + 1
    return {
        "checked_at": time.time(),
        "summary": summary,
        "fatal": any(i["status"] == "error" and i["fatal"] for i in items),
        "items": items,
    }


def repair(cfg: Config, ids: list[str], log: Log = print) -> dict:
    repaired: list[str] = []
    failed: list[dict] = []

    for item_id in ids:
        try:
            if item_id == "chromium":
                from iaula.portal.auth import ensure_chromium

                ensure_chromium(log)
                repaired.append(item_id)
            elif item_id == "session":
                path = cfg.root / "data" / "session.json"
                path.unlink(missing_ok=True)
                log("Sesión guardada eliminada.")
                repaired.append(item_id)
            elif item_id == "dirs":
                (cfg.root / "data").mkdir(parents=True, exist_ok=True)
                (cfg.root / "downloads").mkdir(parents=True, exist_ok=True)
                repaired.append(item_id)
            elif item_id == "legacy_key":
                from iaula.config import migrate_local_secrets

                migrate_local_secrets(cfg.root)
                repaired.append(item_id)
            else:
                failed.append({"id": item_id, "error": "sin reparación automática"})
        except Exception as exc:
            log(f"ERROR {item_id}: {exc}")
            failed.append({"id": item_id, "error": str(exc)})

    return {"repaired": repaired, "failed": failed}
