"""Servidor MCP (Model Context Protocol) de IAula Virtual.

Expone el aula virtual a cualquier agente IA (Claude Desktop, Claude Code,
Cursor, …) por stdio. Reutiliza la sesión guardada con `python -m iaula login`.

Ejecutar:  python -m iaula mcp            (stdio, para conectar agentes)
           python -m iaula mcp --sse      (HTTP/SSE en 127.0.0.1:7801)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from iaula import actions, notebooklm as nlm
from iaula.config import Config, load_config
from iaula.extract import extract_text
from iaula.portal.client import Portal
from iaula.portal.courses import find_course as _find_course
from iaula.portal.courses import list_courses as _list_courses
from iaula.portal.materials import list_materials as _list_materials
from iaula.portal.tasks import list_tasks as _list_tasks

mcp = MCPServer("iaula", instructions=(
    "Herramientas del aula virtual de la ULEAM (Moodle): cursos, materiales, "
    "tareas con vencimientos, y contexto completo de cada tarea (descripción "
    "más el contenido extraído de sus archivos adjuntos). Los archivos se "
    "descargan bajo downloads/ y se pueden subir a NotebookLM."
))

_LOGIN_HINT = (
    "No pude conectar al aula virtual. Si la sesión caducó, corre "
    "`python -m iaula login` desde la carpeta del proyecto y vuelve a intentar."
)


def _log(line: str) -> None:
    # En stdio, stdout es del protocolo MCP: los logs van a stderr.
    print(line, file=sys.stderr, flush=True)


def _connect(cfg: Config) -> Portal:
    try:
        return Portal(cfg).connect()
    except Exception as exc:
        raise RuntimeError(_LOGIN_HINT) from exc


def _due(epoch: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch))


@mcp.tool()
def status() -> dict:
    """Comprueba que la sesión del aula y de NotebookLM estén vivas."""
    cfg = load_config()
    portal = _connect(cfg)
    courses = _list_courses(portal)
    return {
        "portal": "OK",
        "courses": len(courses),
        "notebooklm": "OK" if nlm.auth_ok() else "NO — renueva la sesión desde el panel",
    }


@mcp.tool()
def courses() -> list[dict]:
    """Lista los cursos activos (id y nombre). El id sirve para buscar materiales."""
    cfg = load_config()
    portal = _connect(cfg)
    return [{"id": c.id, "name": c.short} for c in _list_courses(portal)]


@mcp.tool()
def check(days: int = 30) -> dict:
    """Novedades: materiales nuevos y tareas nuevas o próximas de entrega."""
    cfg = load_config()
    try:
        rep = actions.run_check(cfg, days=days, log=_log)
    except RuntimeError as exc:
        if "login" in str(exc):
            raise RuntimeError(_LOGIN_HINT) from exc
        raise
    return rep


@mcp.tool()
def tasks(days: int = 30) -> list[dict]:
    """Tareas próximas con su fecha de entrega (id, curso, nombre, vencimiento)."""
    cfg = load_config()
    portal = _connect(cfg)
    now = time.time() - 86400
    out = []
    for t in _list_tasks(portal, days=days):
        if t.due < now:
            continue
        out.append({
            "id": t.id,
            "course": t.course,
            "name": t.name,
            "due": _due(t.due),
            "due_epoch": t.due,
            "url": t.url,
            "action": t.action,
        })
    return out


@mcp.tool()
def task(name_or_id: str, download: bool = True, include_content: bool = True) -> dict:
    """Contexto completo de una tarea: descripción, vencimiento y sus archivos.

    Con download=True baja los adjuntos a downloads/<curso>/Tareas/<tarea>/ y,
    con include_content=True, incluye el texto extraído de cada archivo
    (PDF, txt, md, csv, html) para que el agente tenga el enunciado completo.
    """
    cfg = load_config()
    res = actions.run_task(cfg, name_or_id, download=download, log=_log)
    res["due"] = _due(res["due"])
    contents = []
    if download and include_content:
        for path in res.get("downloaded", []):
            entry = {"file": path.split("\\")[-1] if "\\" in path else path, "path": path}
            try:
                entry["content"] = extract_text(Path(path), max_chars=8000)
            except Exception as exc:
                entry["content"] = f"(no se pudo extraer texto: {exc})"
            contents.append(entry)
    res["contents"] = contents
    return res


@mcp.tool()
def materials(course: str) -> list[dict]:
    """Materiales de un curso (id, tipo y título). course acepta parte del nombre."""
    cfg = load_config()
    portal = _connect(cfg)
    c = _find_course(_list_courses(portal), course)
    return [{"id": m.id, "kind": m.kind, "title": m.title}
            for m in _list_materials(portal, c.id)]


@mcp.tool()
def download(course: str) -> list[dict]:
    """Descarga todos los materiales descargables de un curso. Devuelve las rutas."""
    cfg = load_config()
    try:
        out = actions.run_download(cfg, course, log=_log)
    except LookupError as exc:
        raise ValueError(str(exc)) from exc
    return out


@mcp.tool()
def extract(path: str) -> str:
    """Texto de un archivo ya descargado (PDF, txt, md, csv, html, json)."""
    return extract_text(Path(path), max_chars=12000)


@mcp.tool()
def notebooklm_sync(course: str = "", wait: bool = True) -> dict | list[dict]:
    """Sube los archivos descargados a NotebookLM (un cuaderno por curso).

    Sin curso, sincroniza todos los cursos. Requiere sesión de Google activa
    (botón "Renovar sesión" del panel si caducó).
    """
    cfg = load_config()
    if not nlm.auth_ok():
        raise RuntimeError(
            "NotebookLM sin sesión: usa el botón Renovar sesión del panel "
            "o corre scripts\\refresh-google-session.py"
        )
    if course:
        return actions.run_nlm_sync(cfg, course, log=_log, wait=wait)
    return actions.run_nlm_sync_all(cfg, log=_log, wait=wait)


@mcp.tool()
def notebooklm_refresh() -> dict:
    """Renueva la sesión de Google/NotebookLM si caducó.

    Primero intenta el refresco silencioso (server-side). Si no
    alcanza, cierra Brave y extrae la sesión de tu perfil de Brave
    (igual que el botón "Renovar sesión" del panel).
    Aviso: esta segunda vía cierra Brave si está abierto.
    """
    cfg = load_config()
    try:
        nlm._run("auth", "refresh")
        if nlm.auth_ok():
            return {"ok": True, "method": "auth-refresh"}
    except nlm.NotebookLMError:
        pass
    try:
        actions.run_brave_refresh(cfg, log=_log)
    except RuntimeError as exc:
        raise RuntimeError(f"No pude renovar la sesión: {exc}") from exc
    return {"ok": True, "method": "brave-extract"}


def serve(port: int = 7801, sse: bool = False) -> None:
    if sse:
        # Solo escucha en localhost: las credenciales del aula son locales.
        mcp.run(transport="sse", host="127.0.0.1", port=port)
    else:
        mcp.run(transport="stdio")
