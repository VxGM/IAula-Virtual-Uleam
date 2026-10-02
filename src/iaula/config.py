from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PortalConfig:
    base_url: str = ""
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


def find_root(start: Path | None = None) -> Path:
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


def load_config(start: Path | None = None) -> Config:
    root = find_root(start)
    data = _load_toml(root / "config.toml")
    local = _load_toml(root / "config.local.toml")
    portal = {**data.get("portal", {}), **local.get("portal", {})}
    portal["username"] = os.environ.get("IAULA_USERNAME", portal.get("username", ""))
    portal["password"] = os.environ.get("IAULA_PASSWORD", portal.get("password", ""))
    chat = {**data.get("chat", {}), **local.get("chat", {})}
    chat["api_key"] = os.environ.get("OPENAI_API_KEY", chat.get("api_key", ""))
    return Config(root=root, portal=PortalConfig(**portal), chat=ChatConfig(**chat))
