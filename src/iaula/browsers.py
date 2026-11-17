from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from iaula.proc import run

BROWSERS = [
    ("brave", "Brave", r"BraveSoftware\Brave-Browser\Application\brave.exe"),
    ("chrome", "Chrome", r"Google\Chrome\Application\chrome.exe"),
    ("msedge", "Microsoft Edge", r"Microsoft\Edge\Application\msedge.exe"),
    ("firefox", "Firefox", r"Mozilla Firefox\firefox.exe"),
]


@dataclass
class Browser:
    key: str
    name: str
    path: Path


def _reg_query(path: str, name: str) -> str | None:
    try:
        r = run(
            ["reg", "query", path, "/ve"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5,
        )
        for line in r.stdout.splitlines():
            if "(Predeterminado)" in line or "REG_SZ" in line:
                m = re.search(r"REG_SZ\s+(.+)", line)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return None


def _find_in_registry() -> list[Browser]:
    out = []
    for key, name, sub in BROWSERS:
        exe = Path(sub).name
        for hive in (
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        ):
            val = _reg_query(f"{hive}\\{exe}", exe)
            if val:
                p = Path(val)
                if p.exists():
                    out.append(Browser(key, name, p))
                    break
    return out


def _find_by_path(seen: set[str]) -> list[Browser]:
    out = []
    program_files = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))),
    ]
    for key, name, sub in BROWSERS:
        if key in seen:
            continue
        for pf in program_files:
            p = pf / sub
            if p.exists():
                out.append(Browser(key, name, p))
                break
    return out


@lru_cache(maxsize=1)
def detect_browsers() -> list[Browser]:
    """Devuelve los navegadores instalados, sin duplicados, en orden conocido."""
    found = _find_in_registry()
    found += _find_by_path({b.key for b in found})
    by_key: dict[str, Browser] = {}
    for b in found:
        by_key.setdefault(b.key, b)
    return [by_key[k] for k in [b[0] for b in BROWSERS] if k in by_key]


def default_browser() -> Browser | None:
    browsers = detect_browsers()
    if not browsers:
        return None
    # Preferencia determinista: Brave (sesión Google ya usada) > Chrome > Edge > Firefox
    prefer = ("brave", "chrome", "msedge", "firefox")
    for key in prefer:
        for b in browsers:
            if b.key == key:
                return b
    return browsers[0]


PLAYWRIGHT_KEYS = ("brave", "chrome", "msedge")


def playwright_browser(key: str = "") -> Browser | None:
    """Navegador instalado que Playwright puede lanzar (Chromium: Brave/Chrome/Edge)."""
    browsers = {b.key: b for b in detect_browsers() if b.key in PLAYWRIGHT_KEYS}
    if key and key in browsers:
        return browsers[key]
    for k in PLAYWRIGHT_KEYS:
        if k in browsers:
            return browsers[k]
    return None


def browser_prompt(custom_message: str = "Elegí tu navegador para NotebookLM:") -> Browser | None:
    browsers = detect_browsers()
    if not browsers:
        print("No se detectó ningún navegado compatible (Brave, Chrome, Edge, Firefox).")
        return None
    if len(browsers) == 1:
        print(f"Navegador detectado: {browsers[0].name} ({browsers[0].path})")
        return browsers[0]
    print(custom_message)
    for i, b in enumerate(browsers, 1):
        print(f"  {i}) {b.name}  ({b.path})")
    print(f"  0) Ninguno / lo elijo yo")
    while True:
        try:
            choice = input("Opción: ").strip()
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(browsers):
                return browsers[idx - 1]
        except (ValueError, EOFError, KeyboardInterrupt):
            return None
