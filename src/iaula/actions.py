from __future__ import annotations

import time
from typing import Callable

from iaula import notebooklm as nlm
from iaula.config import Config
from iaula.downloader import course_dir, download, sha256
from iaula.portal.client import Portal
from iaula.portal.courses import find_course, list_courses
from iaula.portal.materials import DOWNLOADABLE, list_materials
from iaula.portal.tasks import list_tasks
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


def run_download(cfg: Config, course_query: str, item: int | None = None, log: Log = print) -> list[dict]:
    portal = Portal(cfg).connect()
    course = find_course(list_courses(portal), str(course_query))
    log(f"Curso: {course.short}")
    items = [m for m in list_materials(portal, course.id) if m.kind in {"resource", "folder"}]
    if item:
        items = [m for m in items if m.id == int(item)]
    out = []
    for m in items:
        path = download(portal, cfg, course, m)
        out.append({"id": m.id, "title": m.title, "path": str(path) if path else None})
        log(f"{'OK  ' if path else 'SKIP'} {m.title} -> {path or 'sin archivo'}")
    return out


def run_nlm_sync(cfg: Config, course_query: str, log: Log = print) -> dict:
    if not nlm.auth_ok():
        raise nlm.NotebookLMError(
            "NotebookLM sin sesión: cierra Brave y corre scripts\\refresh-google-session.py")
    course = find_course(list_courses(Portal(cfg).connect()), str(course_query))
    state = State(cfg)
    folder = course_dir(cfg, course)
    files = ([f for f in sorted(folder.glob("*")) if f.suffix.lower() in nlm.UPLOADABLE]
             if folder.exists() else [])
    if not files:
        log("Nada que subir: primero descarga materiales (botón Descargar).")
        return {"uploaded": 0, "notebook": None}
    nb = state.notebook_for(course.id)
    if not nb:
        nb = nlm.create_notebook(course.short)
        state.set_notebook(course.id, nb)
        log(f"Notebook creado: {nb}")
    done = 0
    for f in files:
        h = sha256(f)
        if state.is_uploaded(course.id, h):
            log(f"= {f.name} (ya subido)")
            continue
        nlm.wait_source(nb, nlm.add_source(nb, f))
        state.mark_uploaded(course.id, h, f.name)
        log(f"+ {f.name}")
        done += 1
    log(f"Notebook: {nb}")
    return {"uploaded": done, "notebook": nb}
