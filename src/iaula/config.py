from __future__ import annotations

import json
import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from iaula import secrets

DEFAULT_PORTAL_URL = "https://aulavirtualmoodle.uleam.edu.ec"
DEFAULT_CHAT_URL = "https://api.openai.com/v1"
DEFAULT_CHAT_MODEL = "gpt-5.4-mini"
SECRET_PORTAL_PASSWORD = "portal.password"
SECRET_CHAT_KEY = "chat.api_key"


@dataclass
class PortalConfig:
    base_url: str = DEFAULT_PORTAL_URL
    username: str = ""
    password: str = ""


@dataclass
class ChatConfig:
    api_key: str = ""
    model: str = DEFAULT_CHAT_MODEL
    base_url: str = DEFAULT_CHAT_URL
    stt_model: str = "gpt-4o-mini-transcribe"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"


@dataclass
class Config:
    root: Path
    portal: PortalConfig = field(default_factory=PortalConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    browser: str = ""  # key del navegador preferido (brave, chrome, msedge)


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


def load_config(start: Path | None = None) -> Config:
    root = find_root(start)
    data = _load_toml(root / "config.toml")
    local = _load_toml(root / "config.local.toml")
    portal = {**data.get("portal", {}), **local.get("portal", {})}
    portal["password"] = (
        portal.get("password")
        or secrets.get_item(root, SECRET_PORTAL_PASSWORD)
        or ""
    )
    portal["base_url"] = os.environ.get(
        "PORTAL_BASE_URL", os.environ.get("IAULA_BASE_URL", portal.get("base_url") or DEFAULT_PORTAL_URL))
    portal["username"] = os.environ.get(
        "IAULA_USERNAME", os.environ.get("PORTAL_USERNAME", portal.get("username", "")))
    portal["password"] = os.environ.get(
        "IAULA_PASSWORD", os.environ.get("PORTAL_PASSWORD", portal["password"]))
    chat = {**data.get("chat", {}), **local.get("chat", {})}
    chat["api_key"] = (
        os.environ.get("OPENAI_API_KEY")
        or chat.get("api_key")
        or secrets.get_item(root, SECRET_CHAT_KEY)
        or ""
    )
    chat["base_url"] = os.environ.get("OPENAI_BASE_URL", chat.get("base_url") or DEFAULT_CHAT_URL)
    chat["model"] = os.environ.get("OPENAI_MODEL", chat.get("model") or DEFAULT_CHAT_MODEL)
    browser = (
        (local.get("browser") or {}).get("default")
        or (data.get("browser") or {}).get("default")
        or (local.get("notebooklm") or {}).get("browser")
        or (data.get("notebooklm") or {}).get("browser")
        or ""
    )
    return Config(root=root, portal=PortalConfig(**portal), chat=ChatConfig(**chat),
                  browser=str(browser))


def _write_local(root: Path, data: dict) -> None:
    lines: list[str] = []
    for sec, vals in data.items():
        lines.append(f"[{sec}]")
        for key, value in vals.items():
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
        lines.append("")
    path = root / "config.local.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def save_local(root: Path, section: str, values: dict) -> None:
    """Fusiona valores en config.local.toml sin tocar el resto de secciones."""
    path = root / "config.local.toml"
    data = _load_toml(path)
    data.setdefault(section, {}).update(values)
    _write_local(root, data)


def _migrate_bundled_key(root: Path) -> bool:
    """Mueve la clave de instalaciones 1.1.x a la bóveda y borra el archivo."""
    candidates = [
        Path(sys.executable).parent / "bundled_key.txt",
        Path(__file__).resolve().parent / "bundled_key.txt",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        local = _load_toml(root / "config.local.toml")
        has_local_key = bool((local.get("chat") or {}).get("api_key"))
        if value and not has_local_key and not secrets.get_item(root, SECRET_CHAT_KEY):
            try:
                secrets.set_item(root, SECRET_CHAT_KEY, value)
            except Exception:
                # No borres la clave si no se pudo guardar en la bóveda.
                return False
        try:
            path.unlink()
        except OSError:
            pass
        return True
    return False


def migrate_local_secrets(root: Path) -> bool:
    """Mueve contraseñas/API keys en claro a la bóveda DPAPI.

    Devuelve True si cambió algo (reescribió el TOML o migró la clave antigua).
    Idempotente.
    """
    changed = _migrate_bundled_key(root)
    path = root / "config.local.toml"
    data = _load_toml(path)

    portal = data.get("portal") or {}
    password = str(portal.get("password") or "").strip()
    if password:
        try:
            secrets.set_item(root, SECRET_PORTAL_PASSWORD, password)
        except Exception:
            pass
        else:
            portal.pop("password", None)
            data["portal"] = portal
            changed = True

    chat = data.get("chat") or {}
    api_key = str(chat.get("api_key") or "").strip()
    if api_key:
        try:
            secrets.set_item(root, SECRET_CHAT_KEY, api_key)
        except Exception:
            pass
        else:
            chat.pop("api_key", None)
            data["chat"] = chat
            changed = True

    if changed:
        _write_local(root, data)
    return changed
