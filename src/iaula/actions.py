from __future__ import annotations

import time
from typing import Callable

from iaula import notebooklm as nlm
from iaula.config import Config
from iaula.downloader import course_dir, download, download_url, safe, sha256
from iaula.portal.client import Portal
from iaula.portal.courses import find_course, list_courses
from iaula.portal.materials import DOWNLOADABLE, list_materials
from iaula.portal.tasks import list_tasks, task_context
from iaula.report import build_report, save_report
from iaula.state import State

Log = Callable[[str], None]


def run_check(cfg: Config, days: int = 30, log: Log = print) -> dict:
    portal = Portal(cfg).connect()
    state = State(cfg)
    log("Conectado al aula")
    courses = list_courses(portal)
    state.upsert_courses(courses)
    log(f"{len(courses)} cursos en curso")
    baseline = state.is_baseline()
    new_materials = []
    for c in courses:
        items = [m for m in list_materials(portal, c.id) if m.kind in DOWNLOADABLE]
        new_materials += state.record_materials(items)
        log(f"  {c.short}: {len(items)} materiales")
    tasks = [t for t in list_tasks(portal, days=days) if t.due >= time.time() - 86400]
    new_tasks = state.record_tasks(tasks)
    if baseline:
        state.mark_baseline()
        new_materials, new_tasks = [], []
        log("Línea base guardada (sin novedades).")
    elif new_materials or new_tasks:
        log(f"Novedades: {len(new_materials)} materiales, {len(new_tasks)} tareas")
    else:
        log("Sin novedades.")
    rep = build_report(courses, new_materials, new_tasks, tasks, baseline)
    save_report(cfg, rep)
    return rep


def _download_course(portal: Portal, cfg: Config, course, item: int | None, log: Log) -> list[dict]:
    items = [m for m in list_materials(portal, course.id) if m.kind in {"resource", "folder"}]
    if item:
        items = [m for m in items if m.id == int(item)]
    out = []
    for m in items:
        path = download(portal, cfg, course, m)
        out.append({"id": m.id, "title": m.title, "path": str(path) if path else None})
        log(f"  {'OK  ' if path else 'SKIP'} {m.title} -> {path or 'sin archivo'}")
    return out


def run_download(cfg: Config, course_query: str, item: int | None = None, log: Log = print) -> list[dict]:
    portal = Portal(cfg).connect()
    course = find_course(list_courses(portal), str(course_query))
    log(f"Curso: {course.short}")
    return _download_course(portal, cfg, course, item, log)


def run_download_all(cfg: Config, log: Log = print) -> dict:
    portal = Portal(cfg).connect()
    total = 0
    for c in list_courses(portal):
        log(f"== {c.short}")
        out = _download_course(portal, cfg, c, None, log)
        if not out:
            log("  sin materiales")
        total += len([o for o in out if o["path"]])
    log(f"Descargados {total} archivos")
    return {"files": total}


def run_task(cfg: Config, task_query: str, download: bool = False, log: Log = print) -> dict:
    state = State(cfg)
    tasks = state.tasks_all()
    task = None
    for t in tasks:
        if str(t["id"]) == str(task_query) or str(task_query) in (t.get("url") or ""):
            task = t
            break
    if task is None:
        q = str(task_query).lower()
        hits = [t for t in tasks if q in t["name"].lower()]
        if len(hits) != 1:
            names = "; ".join(f"{t['id']} {t['name']}" for t in tasks[:20])
            raise LookupError(f"Tarea '{task_query}' → {len(hits)} coincidencias. Opciones: {names}")
        task = hits[0]
    names = {c["id"]: c["short"] for c in state.get_courses()}
    course = names.get(task["course_id"], "")
    portal = Portal(cfg).connect()
    url = task.get("url") or ""
    if not url:
        try:
            for t in list_tasks(portal, days=180, past_days=180):
                if t.id == task["id"]:
                    url = t.url
                    break
        except Exception:
            pass
    if not url:
        raise LookupError(f"No pude resolver la URL de la tarea {task['id']} (corre `check`)")
    if not task.get("url"):
        state.db.execute("UPDATE tasks SET url=? WHERE id=?", (url, task["id"]))
        state.db.commit()
    ctx = task_context(portal, url)
    log(f"Tarea: {task['name']} ({course})")
    if ctx.intro:
        log(f"Descripción: {ctx.intro[:600]}")
    out = {
        "id": task["id"], "course": course, "name": task["name"], "due": task["due"],
        "url": url, "intro": ctx.intro,
        "files": [{"name": f.name, "url": f.url} for f in ctx.files],
        "downloaded": [],
    }
    if not ctx.files:
        log("Sin archivos adjuntos en la tarea.")
        return out
    for f in ctx.files:
        log(f"  - {f.name}")
    if download:
        target_dir = cfg.root / "downloads" / safe(course) / "Tareas" / safe(task["name"])
        for f in ctx.files:
            path = download_url(portal, target_dir, f.url, f.name)
            out["downloaded"].append(str(path))
            log(f"  OK -> {path}")
    return out


def _sync_course(cfg: Config, state: State, course, log: Log, wait: bool) -> dict:
    folder = course_dir(cfg, course)
    files = ([f for f in sorted(folder.glob("*")) if f.suffix.lower() in nlm.UPLOADABLE]
             if folder.exists() else [])
    if not files:
        log(f"  {course.short}: nada que subir (descarga materiales primero)")
        return {"course": course.short, "uploaded": 0, "notebook": None}
    nb = state.notebook_for(course.id)
    if not nb:
        nb = nlm.create_notebook(course.short)
        state.set_notebook(course.id, nb)
        log(f"  notebook creado: {nb}")
    existing: set[str] = set()
    try:
        data = nlm._run("source", "list", "--notebook", nb, "--json")
        existing = {s.get("title", "") for s in data.get("sources", [])}
    except nlm.NotebookLMError:
        pass
    done = 0
    failed = 0
    for f in files:
        h = sha256(f)
        if state.is_uploaded(course.id, h):
            log(f"  = {f.name} (ya subido)")
            continue
        if f.name in existing:
            state.mark_uploaded(course.id, h, f.name)
            log(f"  = {f.name} (ya en el notebook)")
            continue
        ok = False
        err = ""
        for _attempt in range(3):
            try:
                sid = nlm.add_source(nb, f)
                if wait:
                    nlm.wait_source(nb, sid)
                ok = True
                break
            except nlm.NotebookLMError as exc:
                err = str(exc)
        if not ok:
            failed += 1
            log(f"  ! FALLO {f.name}: {err}")
            continue
        state.mark_uploaded(course.id, h, f.name)
        log(f"  + {f.name}")
        done += 1
    if failed:
        log(f"  ({failed} fallidos; re-ejecuta para reintentar)")
    return {"course": course.short, "uploaded": done, "failed": failed, "notebook": nb}


def run_nlm_sync(cfg: Config, course_query: str, log: Log = print, wait: bool = True) -> dict:
    if not nlm.auth_ok():
        raise nlm.NotebookLMError(
            "NotebookLM sin sesión: cierra Brave y corre scripts\\refresh-google-session.py")
    course = find_course(list_courses(Portal(cfg).connect()), str(course_query))
    state = State(cfg)
    res = _sync_course(cfg, state, course, log, wait)
    if res["notebook"]:
        log(f"Notebook: {res['notebook']}")
    return res


def run_nlm_sync_all(cfg: Config, log: Log = print, wait: bool = True) -> list[dict]:
    if not nlm.auth_ok():
        raise nlm.NotebookLMError(
            "NotebookLM sin sesión: cierra Brave y corre scripts\\refresh-google-session.py")
    portal = Portal(cfg).connect()
    state = State(cfg)
    out = []
    for c in list_courses(portal):
        log(f"== {c.short}")
        out.append(_sync_course(cfg, state, c, log, wait))
    return out
