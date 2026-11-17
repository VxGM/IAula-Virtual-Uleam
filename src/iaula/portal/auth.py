from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

from playwright.sync_api import Page, sync_playwright

from iaula.browsers import playwright_browser
from iaula.config import Config
from iaula.proc import run

LOGIN_TIMEOUT_S = 180


def session_path(cfg: Config) -> Path:
    return cfg.root / "data" / "session.json"


def ensure_chromium(log: Callable[[str], None] = print) -> None:
    try:
        with sync_playwright() as pw:
            path = pw.chromium.executable_path
        if path and Path(path).exists():
            return
    except Exception:
        pass
    log("Preparando el navegador interno (una sola vez, ~150 MB)…")
    cmd: list[str]
    try:
        from playwright._impl._driver import compute_driver_executable
        res = compute_driver_executable()
        parts = list(res) if isinstance(res, (tuple, list)) else [res]
        cmd = [*[str(x) for x in parts], "install", "chromium"]
    except Exception:
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
    p = run(cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=2400)
    if p.returncode != 0:
        raise RuntimeError("No pude preparar el navegador: " + (p.stderr or p.stdout or "")[-300:])
    log("Navegador listo.")


def _fill_microsoft(page: Page, username: str, password: str) -> None:
    try:
        page.fill("input[name=loginfmt]", username, timeout=15000)
        page.click("#idSIButton9")
        page.fill("input[name=passwd]", password, timeout=15000)
        page.click("#idSIButton9")
        page.click("#idSIButton9", timeout=5000)
    except Exception:
        pass


def login(cfg: Config, headless: bool = False,
          browser: Path | str | None = None) -> Path:
    path = session_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    base = cfg.portal.base_url
    with sync_playwright() as pw:
        exe = Path(browser) if browser else None
        if exe is None:
            preferred = playwright_browser(cfg.browser)
            exe = preferred.path if preferred else None
        if exe is not None:
            instance = pw.chromium.launch(headless=headless, executable_path=str(exe))
        else:
            ensure_chromium()
            instance = pw.chromium.launch(headless=headless)
        ctx = instance.new_context()
        page = ctx.new_page()
        page.goto(f"{base}/auth/oidc/?source=loginpage")
        _fill_microsoft(page, cfg.portal.username, cfg.portal.password)
        deadline = time.time() + LOGIN_TIMEOUT_S
        while time.time() < deadline:
            if page.url.startswith(base) and "/auth/oidc" not in page.url and "/login/" not in page.url:
                break
            page.wait_for_timeout(1000)
        else:
            instance.close()
            raise RuntimeError("Login no completado (¿MFA pendiente?)")
        ctx.storage_state(path=str(path))
        instance.close()
    return path
