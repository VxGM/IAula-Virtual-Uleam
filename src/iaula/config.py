from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PORTAL_URL = "https://aulavirtualmoodle.uleam.edu.ec"


@dataclass
class PortalConfig:
    base_url: str = DEFAULT_PORTAL_URL
    username: str = ""
    password: str = ""


@dataclass
class ChatConfig:
    api_key: str = ""
    model: str = "gpt-5.4-mini"
    base_url: str = "https://api.openai.com/v1"


@dataclass
class Config:
    root: Path
    portal: PortalConfig = field(default_factory=PortalConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)


def app_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "IAulaVirtual"


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("IAULA_HOME")
    if env:
        return Path(env).expanduser().resolve()
    if getattr(sys, "frozen", False):
        root = app_dir()
        root.mkdir(parents=True, exist_ok=True)
        return root
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "config.toml").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def bundled_key() -> str:
    for candidate in (Path(sys.executable).parent / "bundled_key.txt",
                      Path(__file__).resolve().parent / "bundled_key.txt"):
        try:
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except OSError:
            pass
    return ""


def load_config(start: Path | None = None) -> Config:
    root = find_root(start)
    data = _load_toml(root / "config.toml")
    local = _load_toml(root / "config.local.toml")
    portal = {**data.get("portal", {}), **local.get("portal", {})}
    portal["username"] = os.environ.get("IAULA_USERNAME", portal.get("username", ""))
    portal["password"] = os.environ.get("IAULA_PASSWORD", portal.get("password", ""))
    chat = {**data.get("chat", {}), **local.get("chat", {})}
    chat["api_key"] = chat.get("api_key") or bundled_key() or os.environ.get("OPENAI_API_KEY", "")
    return Config(root=root, portal=PortalConfig(**portal), chat=ChatConfig(**chat))
