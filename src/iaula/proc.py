from __future__ import annotations

import subprocess
import sys
from typing import Any, Sequence

_CREATE_NO_WINDOW = 0x08000000


def _hidden() -> dict[str, Any]:
    if sys.platform != "win32":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": startupinfo, "creationflags": _CREATE_NO_WINDOW}


def _merge(kwargs: dict[str, Any]) -> dict[str, Any]:
    extra = _hidden()
    flags = extra.pop("creationflags", 0)
    kwargs.setdefault("startupinfo", extra.get("startupinfo"))
    kwargs["creationflags"] = kwargs.get("creationflags", 0) | flags
    return kwargs


def run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(args, **_merge(kwargs))


def popen(args: Sequence[str], **kwargs: Any) -> subprocess.Popen:
    return subprocess.Popen(args, **_merge(kwargs))
