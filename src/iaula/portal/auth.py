from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from iaula.config import Config

LOGIN_TIMEOUT_S = 180


def session_path(cfg: Config) -> Path:
    return cfg.root / "data" / "session.json"


def _fill_microsoft(page: Page, username: str, password: str) -> None:
    try:
        page.fill("input[name=loginfmt]", username, timeout=15000)
        page.click("#idSIButton9")
        page.fill("input[name=passwd]", password, timeout=15000)
        page.click("#idSIButton9")
        page.click("#idSIButton9", timeout=5000)
    except Exception:
        pass


def login(cfg: Config, headless: bool = False) -> Path:
    path = session_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    base = cfg.portal.base_url
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{base}/auth/oidc/?source=loginpage")
        _fill_microsoft(page, cfg.portal.username, cfg.portal.password)
        deadline = time.time() + LOGIN_TIMEOUT_S
        while time.time() < deadline:
            if page.url.startswith(base) and "/auth/oidc" not in page.url and "/login/" not in page.url:
                break
            page.wait_for_timeout(1000)
        else:
            browser.close()
            raise RuntimeError("Login no completado (¿MFA pendiente?)")
        ctx.storage_state(path=str(path))
        browser.close()
    return path
