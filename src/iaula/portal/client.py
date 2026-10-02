from __future__ import annotations

import json
import re

import requests

from iaula.config import Config
from iaula.portal.auth import login, session_path

_SESSKEY = re.compile(r'"sesskey":"([^"]+)"')


class SessionExpired(Exception):
    pass


class Portal:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.base = cfg.portal.base_url.rstrip("/")
        self.http = requests.Session()
        self.http.headers["User-Agent"] = "Mozilla/5.0 iaula"
        self.sesskey = ""

    def _load_cookies(self) -> bool:
        path = session_path(self.cfg)
        if not path.exists():
            return False
        state = json.loads(path.read_text(encoding="utf-8"))
        for ck in state.get("cookies", []):
            self.http.cookies.set(ck["name"], ck["value"], domain=ck["domain"])
        return True

    def _probe(self) -> bool:
        r = self.http.get(f"{self.base}/my/", timeout=30)
        m = _SESSKEY.search(r.text)
        if "/login/" in r.url or not m:
            return False
        self.sesskey = m.group(1)
        return True

    def connect(self, relogin: bool = True) -> "Portal":
        if self._load_cookies() and self._probe():
            return self
        if not relogin:
            raise SessionExpired("Sesión vencida: ejecuta `iaula login`")
        login(self.cfg, headless=True)
        self.http.cookies.clear()
        if not (self._load_cookies() and self._probe()):
            raise SessionExpired("Re-login falló: ejecuta `iaula login` (visible)")
        return self

    def get(self, path: str, **kw) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base}{path}"
        kw.setdefault("timeout", 60)
        return self.http.get(url, **kw)

    def ajax(self, method: str, args: dict) -> dict:
        r = self.http.post(
            f"{self.base}/lib/ajax/service.php?sesskey={self.sesskey}&info={method}",
            json=[{"index": 0, "methodname": method, "args": args}],
            timeout=60,
        )
        res = r.json()[0]
        if res.get("error"):
            raise RuntimeError(f"{method}: {res.get('exception', res)}")
        return res["data"]
