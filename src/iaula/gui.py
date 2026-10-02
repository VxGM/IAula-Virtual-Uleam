from __future__ import annotations

import json
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import requests

from iaula import actions, notebooklm as nlm
from iaula.config import Config
from iaula.downloader import safe
from iaula.portal.client import Portal
from iaula.state import State

WEB_DIR = (Path(__file__).resolve().parent / "web").resolve()

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}


class Jobs:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, title: str, fn) -> str:
        jid = uuid.uuid4().hex[:12]
        job = {"id": jid, "title": title, "state": "running", "log": [], "error": None,
               "started": time.time(), "ended": None}
        with self._lock:
            self._items[jid] = job

        def log(line: str) -> None:
            with self._lock:
                job["log"].append(str(line))

        def runner() -> None:
            try:
                fn(log)
            except Exception as exc:
                with self._lock:
                    job["state"] = "error"
                    job["error"] = str(exc)
                log(f"ERROR: {exc}")
            else:
                with self._lock:
                    job["state"] = "done"
            finally:
                with self._lock:
                    job["ended"] = time.time()

        threading.Thread(target=runner, daemon=True).start()
        return jid

    def get(self, jid: str) -> dict | None:
        with self._lock:
            job = self._items.get(jid)
            return dict(job) if job else None


def _downloaded_count(cfg: Config, short: str) -> int:
    folder = cfg.root / "downloads" / safe(short)
    return len([f for f in folder.glob("*") if f.is_file()]) if folder.exists() else 0


_AUTH_CACHE: dict = {"at": 0.0, "ok": False}
_AUTH_TTL = 300.0


def nlm_auth_cached(force: bool = False) -> bool:
    now = time.time()
    if force or now - _AUTH_CACHE["at"] > _AUTH_TTL:
        try:
            _AUTH_CACHE["ok"] = nlm.auth_ok()
        except Exception:
            _AUTH_CACHE["ok"] = False
        _AUTH_CACHE["at"] = now
    return bool(_AUTH_CACHE["ok"])


class Handler(BaseHTTPRequestHandler):
    cfg: Config
    jobs: Jobs

    def log_message(self, *args) -> None:
        pass

    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 500) -> None:
        self._json({"error": message}, status)

    def _latest(self) -> dict:
        path = self.cfg.root / "data" / "reports" / "latest.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _chat_system(self) -> str:
        state = State(self.cfg)
        now = time.time()
        courses = state.get_courses()
        names = {c["id"]: c["short"] for c in courses}
        course_txt = ", ".join(c["short"] for c in courses) or "sin datos"
        tasks = [t for t in state.tasks_all() if t["due"] >= now - 86400][:20]
        task_lines = "\n".join(
            f"- {names.get(t['course_id'], '')}: {t['name']} "
            f"(vence {time.strftime('%d/%m %H:%M', time.localtime(t['due']))})"
            for t in tasks) or "(ninguna)"
        rep = self._latest()
        new = rep.get("new_materials") or []
        new_lines = "\n".join(f"- {m['course']}: {m['title']}" for m in new[:15]) or "(nada nuevo)"
        return (
            "Eres el asistente de estudio del panel IAula (aula virtual de la ULEAM, Moodle). "
            "Responde en español, claro y breve. Tienes datos reales del estudiante:\n"
            f"Fecha de hoy: {time.strftime('%A %d/%m/%Y', time.localtime(now))}\n"
            f"Cursos: {course_txt}\n"
            f"Tareas pendientes:\n{task_lines}\n"
            f"Materiales nuevos:\n{new_lines}"
        )

    def _chat(self, payload: dict) -> None:
        cfg = self.cfg
        if not cfg.chat.api_key:
            self._error("Falta la API key de OpenAI: añade [chat] api_key en config.local.toml", 400)
            return
        raw = payload.get("messages")
        if not isinstance(raw, list) or not raw:
            self._error("mensajes vacíos", 400)
            return
        messages = [{"role": "system", "content": self._chat_system()}]
        for m in raw[-24:]:
            role = m.get("role")
            content = str(m.get("content") or "")[:8000]
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        try:
            r = requests.post(
                f"{cfg.chat.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {cfg.chat.api_key}"},
                json={"model": cfg.chat.model, "messages": messages},
                timeout=120)
        except requests.RequestException as exc:
            self._error(f"No pude llamar a OpenAI: {exc}", 502)
            return
        try:
            data = r.json()
        except ValueError:
            self._error(f"Respuesta inválida de OpenAI ({r.status_code})", 502)
            return
        if r.status_code != 200:
            msg = (data.get("error") or {}).get("message") or f"OpenAI respondió {r.status_code}"
            self._error(msg, 502)
            return
        reply = ((data.get("choices") or [{}])[0].get("message", {}).get("content")) or ""
        self._json({"reply": reply, "model": cfg.chat.model})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/"):
                self._api_get(path)
            else:
                self._static(path)
        except Exception as exc:
            self._error(str(exc))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length)) if length else {}
            if path.startswith("/api/actions/"):
                self._action(path.removeprefix("/api/actions/"), payload or {})
            elif path == "/api/chat":
                self._chat(payload or {})
            else:
                self._error("ruta desconocida", 404)
        except Exception as exc:
            self._error(str(exc))

    def _api_get(self, path: str) -> None:
        cfg = self.cfg
        state = State(cfg)
        base = cfg.portal.base_url.rstrip("/")
        now = time.time()

        if path == "/api/summary":
            latest = cfg.root / "data" / "reports" / "latest.json"
            rep = self._latest()
            courses = state.get_courses()
            names = {c["id"]: c["short"] for c in courses}
            tasks = [t for t in state.tasks_all() if t["due"] >= now - 86400]
            upcoming = [
                {"id": t["id"], "course_id": t["course_id"], "course": names.get(t["course_id"], ""),
                 "name": t["name"], "due": t["due"],
                 "url": t["url"] or f"{base}/mod/assign/view.php?id={t['id']}",
                 "days_left": int((t["due"] - now) // 86400)}
                for t in tasks
            ]
            seen = {m["id"]: m["first_seen"] for m in state.materials()}
            new_materials = rep.get("new_materials") or []
            for m in new_materials:
                m["first_seen"] = seen.get(m["id"])
            self._json({
                "portal_url": f"{base}/my/",
                "last_check": (
                    {"ts": latest.stat().st_mtime, "baseline": bool(rep.get("baseline"))}
                    if latest.exists() else None
                ),
                "counts": {
                    "courses": len(courses),
                    "new_materials": len(new_materials),
                    "pending_tasks": len(tasks),
                },
                "new_materials": new_materials,
                "upcoming_tasks": upcoming,
                "next_due": upcoming[0] if upcoming else None,
            })

        elif path == "/api/courses":
            rep = self._latest()
            out = []
            for c in state.get_courses():
                mats = state.materials(c["id"])
                new_ids = [m["id"] for m in mats
                           if m["id"] in {n["id"] for n in (rep.get("new_materials") or [])
                                          if n.get("course_id") == c["id"]}]
                pending = [t for t in state.tasks_all()
                           if t["course_id"] == c["id"] and t["due"] >= now - 86400]
                out.append({
                    "id": c["id"], "short": c["short"], "full": c["name"], "url": c["url"],
                    "materials": len(mats),
                    "new_materials": len(new_ids),
                    "new_ids": new_ids,
                    "pending_tasks": len(pending),
                    "downloads": _downloaded_count(cfg, c["short"]),
                    "notebook_id": state.notebook_for(c["id"]),
                })
            self._json(out)

        elif path.startswith("/api/courses/"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "materials":
                cid = int(parts[2])
                names = {c["id"]: c["short"] for c in state.get_courses()}
                self._json([{**m, "course": names.get(m["course_id"], "")}
                            for m in state.materials(cid)])
            else:
                self._error("ruta desconocida", 404)

        elif path == "/api/tasks":
            names = {c["id"]: c["short"] for c in state.get_courses()}
            items = [
                {"id": t["id"], "course_id": t["course_id"], "course": names.get(t["course_id"], ""),
                 "name": t["name"], "due": t["due"],
                 "url": t["url"] or f"{base}/mod/assign/view.php?id={t['id']}"}
                for t in state.tasks_all() if t["due"] >= now - 14 * 86400
            ]
            self._json(items)

        elif path == "/api/notebooklm":
            names = {c["id"]: c["short"] for c in state.get_courses()}
            courses = []
            for c in state.get_courses():
                folder = cfg.root / "downloads" / safe(c["short"])
                files = (len([f for f in folder.glob("*") if f.suffix.lower() in nlm.UPLOADABLE])
                         if folder.exists() else 0)
                courses.append({
                    "id": c["id"], "short": c["short"],
                    "notebook_id": state.notebook_for(c["id"]),
                    "files": files,
                    "uploaded": len(state.uploaded_list(c["id"])),
                })
            uploaded = [{"course": names.get(u["course_id"], ""), "filename": u["filename"]}
                        for u in state.uploaded_list()]
            self._json({"courses": courses, "uploaded": uploaded})

        elif path == "/api/notebooklm/auth":
            self._json({"ok": nlm_auth_cached(force="force=1" in self.path)})

        elif path == "/api/chat/info":
            self._json({"configured": bool(cfg.chat.api_key), "model": cfg.chat.model})

        elif path == "/api/sessions":
            try:
                Portal(cfg).connect(relogin=False)
                portal_ok = True
            except Exception:
                portal_ok = False
            self._json({"portal": {"ok": portal_ok}, "notebooklm": {"ok": nlm_auth_cached()}})

        elif path.startswith("/api/jobs/"):
            job = self.jobs.get(path.rsplit("/", 1)[-1])
            if job:
                self._json(job)
            else:
                self._error("job no encontrado", 404)

        else:
            self._error("ruta desconocida", 404)

    def _action(self, kind: str, payload: dict) -> None:
        cfg = self.cfg
        if kind == "check":
            jid = self.jobs.start(
                "Revisando cursos",
                lambda log: actions.run_check(cfg, days=int(payload.get("days", 30)), log=log))
        elif kind in {"download", "nlm_sync"}:
            cid = payload.get("course_id")
            if cid is None:
                self._error("falta course_id", 400)
                return
            if kind == "download":
                item = payload.get("item")
                jid = self.jobs.start(
                    "Descargando materiales",
                    lambda log: actions.run_download(cfg, str(cid), item=int(item) if item else None, log=log))
            else:
                jid = self.jobs.start(
                    "Sincronizando con NotebookLM",
                    lambda log: actions.run_nlm_sync(cfg, str(cid), log=log))
        else:
            self._error("acción desconocida", 404)
            return
        self._json({"job_id": jid})

    def _static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        target = (WEB_DIR / rel).resolve()
        if not str(target).startswith(str(WEB_DIR)) or not target.is_file():
            self._error("no encontrado", 404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def serve(cfg: Config, port: int = 7800, open_browser: bool = True) -> int:
    handler = type("BoundHandler", (Handler,), {"cfg": cfg, "jobs": Jobs()})
    httpd = None
    for candidate in range(port, port + 12):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            break
        except OSError:
            continue
    if httpd is None:
        raise RuntimeError(f"sin puerto libre entre {port} y {port + 11}")
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"IAula GUI: {url}  (Ctrl+C para salir)")
    if open_browser:
        threading.Timer(0.7, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")
    finally:
        httpd.server_close()
    return 0
