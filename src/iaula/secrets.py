"""Bóveda local de secretos (API keys y contraseñas).

En Windows usa DPAPI (CryptProtectData) ligado al usuario y al equipo: el archivo
solo se puede descifrar con la misma sesión de Windows que lo creó. Fuera de
Windows se guarda con permisos 0600 y el método queda marcado como "plain"
para que el diagnóstico lo advierta.

El vault nunca se registra en logs ni se sirve por HTTP.
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import sys
from pathlib import Path

VAULT_VERSION = 1
VAULT_METHOD = "dpapi" if sys.platform == "win32" else "plain"
_ENTROPY = b"IAulaVirtual:v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class SecretError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DataBlob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _crypt32():
    if sys.platform != "win32":
        raise SecretError("DPAPI solo está disponible en Windows")
    return ctypes.WinDLL("crypt32", use_last_error=True)


def _kernel32():
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _protect(data: bytes) -> bytes:
    if sys.platform != "win32":
        return data
    blob_in, _buf_in = _blob(data)
    entropy, _buf_entropy = _blob(_ENTROPY)
    blob_out = _DataBlob()
    ok = _crypt32().CryptProtectData(
        ctypes.byref(blob_in), "IAula Virtual", ctypes.byref(entropy),
        None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out),
    )
    if not ok:
        raise SecretError(f"No pude cifrar con DPAPI (código {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _kernel32().LocalFree(blob_out.pbData)


def _unprotect(data: bytes) -> bytes:
    if sys.platform != "win32":
        return data
    blob_in, _buf_in = _blob(data)
    entropy, _buf_entropy = _blob(_ENTROPY)
    blob_out = _DataBlob()
    ok = _crypt32().CryptUnprotectData(
        ctypes.byref(blob_in), None, ctypes.byref(entropy),
        None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out),
    )
    if not ok:
        raise SecretError(f"No pude descifrar con DPAPI (código {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _kernel32().LocalFree(blob_out.pbData)


def vault_path(root: Path) -> Path:
    return Path(root) / "data" / "secrets.bin"


def _empty() -> dict:
    return {"version": VAULT_VERSION, "method": VAULT_METHOD, "items": {}}


def _read(root: Path) -> dict:
    path = vault_path(root)
    if not path.exists():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty()
    if data.get("method") != VAULT_METHOD or not isinstance(data.get("items"), dict):
        # Vault creado en otra plataforma/usuario: no se puede descifrar aquí.
        return _empty()
    return data


def _write(root: Path, data: dict) -> None:
    path = vault_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    if sys.platform != "win32":
        try:
            path.chmod(0o600)
        except OSError:
            pass


def hint_for(value: str) -> str:
    clean = value.strip()
    return f"···{clean[-4:]}" if len(clean) >= 4 else "···"


def set_item(root: Path, name: str, value: str) -> None:
    data = _read(root)
    clean = value.strip()
    data["items"][name] = {
        "data": base64.b64encode(_protect(clean.encode("utf-8"))).decode("ascii"),
        "hint": hint_for(clean),
    }
    _write(root, data)


def get_item(root: Path, name: str) -> str:
    entry = _read(root).get("items", {}).get(name)
    if not entry:
        return ""
    try:
        raw = base64.b64decode(entry.get("data") or "")
        return _unprotect(raw).decode("utf-8")
    except (ValueError, SecretError, UnicodeDecodeError):
        return ""


def delete_item(root: Path, name: str) -> None:
    data = _read(root)
    if data.get("items", {}).pop(name, None) is not None:
        _write(root, data)


def has_item(root: Path, name: str) -> bool:
    return bool(get_item(root, name))


def item_hint(root: Path, name: str) -> str:
    entry = _read(root).get("items", {}).get(name)
    return str((entry or {}).get("hint") or "")


def method(root: Path) -> str:
    return _read(root).get("method", VAULT_METHOD)
