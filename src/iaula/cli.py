from __future__ import annotations

import argparse
import json
import sys
import time

from iaula import __version__, actions, notebooklm as nlm
from iaula.config import load_config
from iaula.portal.auth import login
from iaula.portal.client import Portal
from iaula.portal.courses import find_course, list_courses
from iaula.portal.materials import list_materials
from iaula.portal.tasks import list_tasks
from iaula.report import notify, render_text, task_line
from iaula.state import State


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iaula", description="Monitor del aula virtual: novedades, tareas y NotebookLM.")
    p.add_argument("--version", action="version", version=f"iaula {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="Login Microsoft; guarda sesión").add_argument("--headless", action="store_true")
    sub.add_parser("courses", help="Cursos en curso").add_argument("--json", action="store_true")

    t = sub.add_parser("tasks", help="Tareas/entregas próximas")
    t.add_argument("--days", type=int, default=30)
    t.add_argument("--json", action="store_true")

    c = sub.add_parser("check", help="Novedades de materiales + tareas")
    c.add_argument("--json", action="store_true")
    c.add_argument("--notify", action="store_true", help="Toast Windows")
    c.add_argument("--days", type=int, default=30)

    m = sub.add_parser("materials", help="Materiales de un curso")
    m.add_argument("--course", required=True)
    m.add_argument("--json", action="store_true")

    d = sub.add_parser("download", help="Descarga materiales de un curso")
    d.add_argument("--course", required=True)
    d.add_argument("--item", type=int, help="ID de módulo (omitir = todos)")

    n = sub.add_parser("nlm", help="NotebookLM")
    ns = n.add_subparsers(dest="nlm_cmd", required=True)
    s = ns.add_parser("sync", help="Sube archivos descargados del curso a su notebook")
    s.add_argument("--course", required=True)
    ns.add_parser("status", help="Auth NotebookLM + notebooks por curso")

    g = sub.add_parser("gui", help="Panel visual local (se abre en el navegador)")
    g.add_argument("--port", type=int, default=7800)
    g.add_argument("--no-open", action="store_true", help="No abrir el navegador automáticamente")
    return p


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _pending(portal: Portal, days: int):
    return [t for t in list_tasks(portal, days=days) if t.due >= time.time() - 86400]


def cmd_check(cfg, args) -> int:
    rep = actions.run_check(cfg, days=args.days, log=lambda _line: None)
    print(_dump(rep) if args.json else render_text(rep))
    if args.notify and (rep["new_materials"] or rep["new_tasks"] or rep["upcoming_tasks"]):
        notify("IAula", f"{len(rep['new_materials'])} material(es) nuevo(s), "
                        f"{len(rep['upcoming_tasks'])} tarea(s) pendiente(s)")
    return 0


def cmd_download(cfg, args) -> int:
    actions.run_download(cfg, args.course, item=args.item)
    return 0


def cmd_nlm_sync(cfg, args) -> int:
    actions.run_nlm_sync(cfg, args.course)
    return 0


def cmd_gui(cfg, args) -> int:
    from iaula import gui
    return gui.serve(cfg, port=args.port, open_browser=not args.no_open)


def run(cfg, args) -> int:
    if args.cmd == "login":
        print(login(cfg, headless=args.headless))
    elif args.cmd == "courses":
        cs = list_courses(Portal(cfg).connect())
        print(_dump([c.__dict__ for c in cs]) if args.json else "\n".join(f"{c.id}  {c.short}" for c in cs))
    elif args.cmd == "tasks":
        ts = _pending(Portal(cfg).connect(), args.days)
        print(_dump([t.__dict__ for t in ts]) if args.json else "\n".join(task_line(t) for t in ts) or "Sin tareas pendientes.")
    elif args.cmd == "check":
        return cmd_check(cfg, args)
    elif args.cmd == "materials":
        portal = Portal(cfg).connect()
        ms = list_materials(portal, find_course(list_courses(portal), args.course).id)
        print(_dump([m.__dict__ for m in ms]) if args.json else "\n".join(f"{m.id}  [{m.kind}] {m.title}" for m in ms))
    elif args.cmd == "download":
        return cmd_download(cfg, args)
    elif args.cmd == "nlm" and args.nlm_cmd == "sync":
        return cmd_nlm_sync(cfg, args)
    elif args.cmd == "nlm":
        print("NotebookLM auth:", "OK" if nlm.auth_ok() else "NO — ejecuta `notebooklm login`")
        for cid, nb in State(cfg).notebooks():
            print(f"  curso {cid} -> {nb}")
    elif args.cmd == "gui":
        return cmd_gui(cfg, args)
    return 0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        code = run(load_config(), args)
    except (LookupError, RuntimeError, nlm.NotebookLMError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        code = 1
    sys.exit(code)
