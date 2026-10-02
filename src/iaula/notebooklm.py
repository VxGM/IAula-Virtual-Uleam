from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

UPLOADABLE = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".epub", ".csv"}


class NotebookLMError(Exception):
    pass


def _run(*args: str) -> dict | str:
    exe = shutil.which("notebooklm")
    if not exe:
        raise NotebookLMError("CLI `notebooklm` no instalado: pip install \"notebooklm-py[browser]\"")
    p = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", timeout=900)
    if p.returncode != 0:
        err = (p.stderr or p.stdout).strip()
        raise NotebookLMError(err[-400:] if len(err) > 400 else err)
    out = p.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def auth_ok() -> bool:
    try:
        res = _run("auth", "check", "--test", "--json")
    except NotebookLMError:
        return False
    return isinstance(res, dict) and res.get("status") == "ok" and res["checks"].get("token_fetch") is True


def create_notebook(title: str) -> str:
    res = _run("create", title, "--json")
    return res["notebook"]["id"]


def add_source(notebook_id: str, path: Path) -> str:
    res = _run("source", "add", str(path), "--notebook", notebook_id, "--json")
    return res["source"]["id"]


def wait_source(notebook_id: str, source_id: str) -> None:
    _run("source", "wait", source_id, "-n", notebook_id, "--timeout", "600")
