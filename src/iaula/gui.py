from __future__ import annotations

import json
import os
import sys
import textwrap
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, urlsplit

import requests

from iaula import actions, doctor, notebooklm as nlm, secrets
from iaula import __version__
from iaula.config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_CHAT_URL,
    SECRET_CHAT_KEY,
    SECRET_PORTAL_PASSWORD,
    Config,
    load_config,
    migrate_local_secrets,
    save_local,
)
from iaula.downloader import safe
from iaula.extract import extract_text
from iaula.portal.client import Portal
from iaula.portal.tasks import list_tasks, task_context
from iaula.state import State

WEB_DIR = (Path(__file__).resolve().parent / "web").resolve()
MAX_JSON_BYTES = 2 * 1024 * 1024

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "microphone=(self), camera=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; media-src 'self' blob:; font-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}


class LocalServer(ThreadingHTTPServer):
    # En Windows SO_REUSEADDR permite que dos instancias escuchen el mismo puerto.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


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


AUDIO_TYPES = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_SPEECH_CHARS = 4000


def speech_text(text: str, limit: int = MAX_SPEECH_CHARS) -> str:
    clean = text.replace("**", "").replace("__", "").replace("`", "")
    clean = clean.replace("*", "").replace("#", "")
    clean = " ".join(clean.split())
    if len(clean) > limit:
        clean = clean[:limit].rsplit(" ", 1)[0] or clean[:limit]
    return clean


_AUTH_CACHE: dict = {"at": 0.0, "ok": False}
_AUTH_TTL = 300.0

_TASK_CTX_CACHE: dict = {}
_TASK_CTX_TTL = 900.0

_DIAG_CACHE: dict = {"at": 0.0, "result": None}
_DIAG_TTL = 60.0

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _env_locked() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _clean_base_url(raw: str) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        return DEFAULT_CHAT_URL
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("La URL debe empezar con https:// (o http:// en localhost).")
    if parsed.username or parsed.password:
        raise ValueError("La URL no puede incluir credenciales.")
    if not parsed.hostname:
        raise ValueError("La URL del proveedor no es válida.")
    if parsed.scheme == "http" and parsed.hostname not in _LOCAL_HOSTS:
        raise ValueError("Usa https:// salvo para un modelo local en 127.0.0.1.")
    return value


def _provider_error(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        message = (body.get("error") or {}).get("message") if isinstance(body.get("error"), dict) else ""
        if message:
            return str(message)
    return f"El proveedor respondió HTTP {resp.status_code}"


def _probe_provider(base_url: str, model: str, api_key: str) -> dict:
    started = time.time()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=15)
    except requests.RequestException as exc:
        raise RuntimeError(f"No pude conectar con {base_url}: {exc.__class__.__name__}") from exc
    if resp.status_code == 200:
        return {"method": "models", "latency_ms": int((time.time() - started) * 1000)}
    if resp.status_code not in (404, 405):
        raise RuntimeError(_provider_error(resp))

    payloads = [
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        {"model": model, "messages": [{"role": "user", "content": "ping"}],
         "max_completion_tokens": 1},
        {"model": model, "messages": [{"role": "user", "content": "ping"}]},
    ]
    error = ""
    for payload in payloads:
        try:
            resp = requests.post(f"{base_url}/chat/completions", headers=headers,
                                 json=payload, timeout=45)
        except requests.RequestException as exc:
            raise RuntimeError(f"No pude conectar con {base_url}: {exc.__class__.__name__}") from exc
        if resp.status_code == 200:
            return {"method": "chat", "latency_ms": int((time.time() - started) * 1000)}
        error = _provider_error(resp)
        if "max_tokens" not in error and "max_completion_tokens" not in error:
            break
    raise RuntimeError(error or "El proveedor rechazó la prueba de conexión")


def _mask(value: str) -> str:
    return f"···{value[-4:]}" if len(value) >= 4 else ("···" if value else "")


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

    def _security_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if not host:
            return True
        port = self.server.server_address[1]
        allowed = {
            f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}",
            "127.0.0.1", "localhost", "[::1]",
        }
        return host in allowed

    def _origin_ok(self) -> bool:
        port = self.server.server_address[1]
        allowed = {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            f"http://[::1]:{port}",
        }
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in allowed:
            return False
        site = self.headers.get("Sec-Fetch-Site")
        if site and site not in ("same-origin", "none"):
            return False
        return True

    def _guard(self, post: bool = False) -> bool:
        if not self._host_ok():
            self._error("host no permitido", 403)
            return False
        if post and not self._origin_ok():
            self._error("origen no permitido", 403)
            return False
        return True

    def _internal_error(self, exc: Exception) -> None:
        try:
            logdir = self.cfg.root / "data" / "logs"
            logdir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with (logdir / "error.log").open("a", encoding="utf-8") as fh:
                fh.write(f"[{stamp}] {self.command} {self.path}\n{traceback.format_exc()}\n")
        except OSError:
            pass
        if getattr(sys, "frozen", False):
            self._error("Error interno. Revisa Ajustes → Diagnóstico.", 500)
        else:
            self._error(str(exc), 500)

    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
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

    def _setup(self, payload: dict) -> None:
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not username or not password:
            self._error("Usuario y contraseña son obligatorios", 400)
            return
        root = self.cfg.root
        save_local(root, "portal", {"username": username})
        secrets.set_item(root, SECRET_PORTAL_PASSWORD, password)
        openai_key = str(payload.get("openai_key") or "").strip()
        if openai_key:
            secrets.set_item(root, SECRET_CHAT_KEY, openai_key)
        base_url = str(payload.get("base_url") or "").strip()
        model = str(payload.get("model") or "").strip()
        if base_url or model:
            save_local(root, "chat", {
                "base_url": _clean_base_url(base_url),
                "model": model or DEFAULT_CHAT_MODEL,
            })
        type(self).cfg = load_config()
        self._json({"ok": True})

    def _setup_browser(self, payload: dict) -> None:
        browser = str(payload.get("browser") or "").strip()
        if not browser:
            self._error("falta browser", 400)
            return
        save_local(self.cfg.root, "browser", {"default": browser})
        type(self).cfg = load_config()
        self._json({"ok": True, "browser": type(self).cfg.browser})

    def _chat_source(self) -> str:
        if _env_locked():
            return "env"
        if secrets.get_item(self.cfg.root, SECRET_CHAT_KEY):
            return "vault"
        return "local" if self.cfg.chat.api_key else "none"

    def _settings_chat_get(self) -> None:
        cfg = self.cfg
        source = self._chat_source()
        self._json({
            "configured": bool(cfg.chat.api_key),
            "base_url": cfg.chat.base_url,
            "model": cfg.chat.model,
            "key_hint": "gestionada por el entorno" if source == "env" else _mask(cfg.chat.api_key),
            "source": source,
            "locked_by_env": source == "env",
            "defaults": {"base_url": DEFAULT_CHAT_URL, "model": DEFAULT_CHAT_MODEL},
            "voice": {"stt": cfg.chat.stt_model, "tts": cfg.chat.tts_model,
                      "name": cfg.chat.tts_voice},
        })

    def _settings_chat_save(self, payload: dict) -> None:
        cfg = self.cfg
        root = cfg.root
        try:
            base_url = _clean_base_url(str(payload.get("base_url") or cfg.chat.base_url))
        except ValueError as exc:
            self._error(str(exc), 400)
            return
        model = str(payload.get("model") or cfg.chat.model).strip() or DEFAULT_CHAT_MODEL
        provided = str(payload.get("api_key") or "").strip()
        if _env_locked():
            api_key = cfg.chat.api_key
        else:
            api_key = provided or cfg.chat.api_key
        if not api_key:
            self._error("Falta la API key. Pega una clave válida de tu proveedor.", 400)
            return
        try:
            probe = _probe_provider(base_url, model, api_key)
        except RuntimeError as exc:
            self._error(str(exc), 400)
            return
        save_local(root, "chat", {"base_url": base_url, "model": model})
        if provided and not _env_locked():
            secrets.set_item(root, SECRET_CHAT_KEY, provided)
        type(self).cfg = load_config()
        self._json({"ok": True, "configured": True, "model": model,
                    "base_url": base_url, **probe})

    def _settings_chat_clear(self) -> None:
        secrets.delete_item(self.cfg.root, SECRET_CHAT_KEY)
        type(self).cfg = load_config()
        self._json({"ok": True, "configured": bool(type(self).cfg.chat.api_key)})

    def _settings_portal_get(self) -> None:
        cfg = self.cfg
        self._json({
            "username": cfg.portal.username,
            "has_password": bool(cfg.portal.password),
            "base_url": cfg.portal.base_url,
        })

    def _settings_portal(self, payload: dict) -> None:
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not username:
            self._error("El usuario del aula es obligatorio", 400)
            return
        root = self.cfg.root
        save_local(root, "portal", {"username": username})
        if password:
            secrets.set_item(root, SECRET_PORTAL_PASSWORD, password)
        type(self).cfg = load_config()
        self._json({"ok": True, "username": username,
                    "has_password": bool(self.cfg.portal.password)})

    def _diagnostics(self, force: bool) -> None:
        now = time.time()
        cached = _DIAG_CACHE["result"]
        if force or cached is None or now - _DIAG_CACHE["at"] > _DIAG_TTL:
            _DIAG_CACHE["result"] = doctor.check_all(self.cfg, network=True)
            _DIAG_CACHE["at"] = now
        self._json(_DIAG_CACHE["result"])

    def _diagnostics_repair(self, payload: dict) -> None:
        ids = payload.get("ids")
        if not isinstance(ids, list) or not ids:
            self._error("falta la lista de reparaciones", 400)
            return
        clean = [str(i) for i in ids if isinstance(i, str)][:10]
        _DIAG_CACHE["at"] = 0.0
        jid = self.jobs.start(
            "Preparando componentes",
            lambda log: doctor.repair(self.cfg, clean, log=log))
        self._json({"job_id": jid})

    def _task_ctx(self, task: dict, course: str) -> dict:
        tid = task["id"]
        entry = _TASK_CTX_CACHE.get(tid)
        if entry and time.time() - entry["at"] < _TASK_CTX_TTL:
            return entry
        entry = {"at": time.time(), "intro": "", "files": [], "text": ""}
        try:
            portal = Portal(self.cfg).connect()
            url = task.get("url") or ""
            if not url:
                for t in list_tasks(portal, days=180, past_days=180):
                    if t.id == tid:
                        url = t.url
                        break
            if url:
                ctx = task_context(portal, url)
                entry["intro"] = ctx.intro
                entry["files"] = [{"name": f.name, "url": f.url} for f in ctx.files]
            parts: list[str] = []
            target = self.cfg.root / "downloads" / safe(course) / "Tareas" / safe(task["name"])
            if target.exists():
                for f in sorted(target.glob("*")):
                    if sum(len(p) for p in parts) > 7000:
                        break
                    if f.suffix.lower() in {".pdf", ".txt", ".md", ".csv"}:
                        try:
                            parts.append(f"--- {f.name} ---\n" + extract_text(f, max_chars=4500))
                        except Exception:
                            pass
            entry["text"] = "\n".join(parts)
        except Exception:
            pass
        _TASK_CTX_CACHE[tid] = entry
        return entry

    def _chat_system(self) -> str:
        state = State(self.cfg)
        now = time.time()
        courses = state.get_courses()
        names = {c["id"]: c["short"] for c in courses}
        course_txt = ", ".join(c["short"] for c in courses) or "sin datos"
        blocks = []
        for t in [t for t in state.tasks_all() if t["due"] >= now - 86400][:5]:
            course = names.get(t["course_id"], "")
            due = time.strftime("%d/%m %H:%M", time.localtime(t["due"]))
            block = [f"- {t['name']} ({course}), vence {due}"]
            ctx = self._task_ctx(t, course)
            if ctx["intro"]:
                block.append(f"  Descripción: {ctx['intro'][:1200]}")
            if ctx["files"]:
                block.append("  Adjuntos: " + ", ".join(f["name"] for f in ctx["files"]))
            if ctx["text"]:
                block.append("  Contenido de los archivos:\n" + textwrap.indent(ctx["text"][:7000], "    "))
            blocks.append("\n".join(block))
        task_lines = "\n".join(blocks) or "(ninguna)"
        rep = self._latest()
        new = rep.get("new_materials") or []
        new_lines = "\n".join(f"- {m['course']}: {m['title']}" for m in new[:15]) or "(nada nuevo)"
        return (
            "Eres el asistente de estudio del panel IAula (aula virtual de la ULEAM, Moodle). "
            "Responde en español, claro y breve. Tienes datos reales del estudiante, incluida la "
            "descripción y el contenido de los archivos de sus tareas pendientes:\n"
            f"Fecha de hoy: {time.strftime('%A %d/%m/%Y', time.localtime(now))}\n"
            f"Cursos: {course_txt}\n"
            f"Tareas pendientes:\n{task_lines}\n"
            f"Materiales nuevos:\n{new_lines}"
        )

    def _chat(self, payload: dict) -> None:
        cfg = self.cfg
        if not cfg.chat.api_key:
            self._error("Falta tu API key del Asistente. Configúrala en Ajustes → Asistente IA.", 400)
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
            self._error(f"No pude conectar con el proveedor de IA: {exc.__class__.__name__}", 502)
            return
        try:
            data = r.json()
        except ValueError:
            self._error(f"Respuesta inválida del proveedor ({r.status_code})", 502)
            return
        if r.status_code != 200:
            self._error(_provider_error(r), 502)
            return
        reply = ((data.get("choices") or [{}])[0].get("message", {}).get("content")) or ""
        self._json({"reply": reply, "model": cfg.chat.model})

    def _voice_transcribe(self, body: bytes, content_type: str) -> None:
        cfg = self.cfg
        if not cfg.chat.api_key:
            self._error("Falta tu API key del Asistente. Configúrala en Ajustes → Asistente IA.", 400)
            return
        if not body:
            self._error("audio vacío", 400)
            return
        mime = (content_type or "audio/webm").split(";")[0].strip().lower()
        ext = AUDIO_TYPES.get(mime, "webm")
        try:
            r = requests.post(
                f"{cfg.chat.base_url.rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {cfg.chat.api_key}"},
                files={"file": (f"voz.{ext}", body, mime)},
                data={"model": cfg.chat.stt_model, "language": "es"},
                timeout=180)
        except requests.RequestException as exc:
            self._error(f"No pude conectar con el proveedor de IA: {exc.__class__.__name__}", 502)
            return
        try:
            data = r.json()
        except ValueError:
            self._error(f"Respuesta inválida del proveedor ({r.status_code})", 502)
            return
        if r.status_code != 200:
            self._error(_provider_error(r), 502)
            return
        self._json({"text": str(data.get("text") or "").strip(), "model": cfg.chat.stt_model})

    def _voice_speak(self, payload: dict) -> None:
        cfg = self.cfg
        if not cfg.chat.api_key:
            self._error("Falta tu API key del Asistente. Configúrala en Ajustes → Asistente IA.", 400)
            return
        text = speech_text(str(payload.get("text") or ""))
        if not text:
            self._error("texto vacío", 400)
            return
        try:
            r = requests.post(
                f"{cfg.chat.base_url.rstrip('/')}/audio/speech",
                headers={"Authorization": f"Bearer {cfg.chat.api_key}"},
                json={"model": cfg.chat.tts_model, "voice": cfg.chat.tts_voice,
                      "input": text, "response_format": "mp3"},
                timeout=180)
        except requests.RequestException as exc:
            self._error(f"No pude conectar con el proveedor de IA: {exc.__class__.__name__}", 502)
            return
        if r.status_code != 200:
            self._error(_provider_error(r), 502)
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(r.content)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(r.content)

    def do_GET(self) -> None:
        if not self._guard():
            return
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/"):
                self._api_get(path)
            else:
                self._static(path)
        except Exception as exc:
            self._internal_error(exc)

    def do_POST(self) -> None:
        if not self._guard(post=True):
            return
        path = urlparse(self.path).path
        try:
            if path == "/api/voice/transcribe":
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_AUDIO_BYTES:
                    self._error("audio demasiado grande", 413)
                    return
                body = self.rfile.read(length) if length else b""
                self._voice_transcribe(body, self.headers.get("Content-Type") or "")
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_JSON_BYTES:
                self._error("cuerpo demasiado grande", 413)
                return
            payload = json.loads(self.rfile.read(length)) if length else {}
            if path.startswith("/api/actions/"):
                self._action(path.removeprefix("/api/actions/"), payload or {})
            elif path == "/api/chat":
                self._chat(payload or {})
            elif path == "/api/voice/speak":
                self._voice_speak(payload or {})
            elif path == "/api/setup":
                self._setup(payload or {})
            elif path == "/api/setup/browser":
                self._setup_browser(payload or {})
            elif path == "/api/settings/chat":
                self._settings_chat_save(payload or {})
            elif path == "/api/settings/chat/clear":
                self._settings_chat_clear()
            elif path == "/api/settings/portal":
                self._settings_portal(payload or {})
            elif path == "/api/diagnostics/repair":
                self._diagnostics_repair(payload or {})
            else:
                self._error("ruta desconocida", 404)
        except json.JSONDecodeError:
            self._error("JSON inválido", 400)
        except Exception as exc:
            self._internal_error(exc)

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
            self._json({"ok": nlm_auth_cached(force="force=1" in self.path),
                        "browser": None})

        elif path == "/api/notebooklm/browsers":
            from iaula.browsers import detect_browsers, playwright_browser
            browsers = [{"key": b.key, "name": b.name, "path": str(b.path)}
                        for b in detect_browsers() if b.key in ("brave", "chrome", "msedge")]
            current = playwright_browser(cfg.browser)
            self._json({"browsers": browsers,
                        "default": current.key if current else None})

        elif path == "/api/chat/info":
            self._json({"configured": bool(cfg.chat.api_key), "model": cfg.chat.model,
                        "base_url": cfg.chat.base_url, "key_hint": _mask(cfg.chat.api_key),
                        "locked_by_env": _env_locked(),
                        "voice": {"stt": cfg.chat.stt_model, "tts": cfg.chat.tts_model,
                                  "name": cfg.chat.tts_voice}})

        elif path == "/api/settings/chat":
            self._settings_chat_get()

        elif path == "/api/settings/portal":
            self._settings_portal_get()

        elif path == "/api/diagnostics":
            self._diagnostics(force="force=1" in self.path)

        elif path == "/api/setup/status":
            needs = not (cfg.portal.username and cfg.portal.password)
            _DIAG_CACHE["at"] = 0.0
            self._json({"needs_setup": needs,
                        "mode": "app" if getattr(sys, "frozen", False) else "dev",
                        "version": __version__})

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
        elif kind == "login":
            jid = self.jobs.start(
                "Conectando con el aula (Microsoft)",
                lambda log: actions.run_login(cfg, log=log))
        elif kind == "login_browser":
            jid = self.jobs.start(
                "Conectando con el aula",
                lambda log: actions.run_login_with_browser(
                    cfg, browser_key=payload.get("browser", ""), log=log))
        elif kind == "refresh_session":
            jid = self.jobs.start(
                "Renovando sesión de Google",
                lambda log: actions.run_brave_refresh(cfg, log=log))
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
        if not target.is_relative_to(WEB_DIR) or not target.is_file():
            self._error("no encontrado", 404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def serve(cfg: Config, port: int = 7800, open_browser: bool = True) -> int:
    if migrate_local_secrets(cfg.root):
        cfg = load_config()
    handler = type("BoundHandler", (Handler,), {"cfg": cfg, "jobs": Jobs()})
    httpd = None
    for candidate in range(port, port + 12):
        try:
            httpd = LocalServer(("127.0.0.1", candidate), handler)
            break
        except OSError:
            continue
    if httpd is None:
        raise RuntimeError(f"sin puerto libre entre {port} y {port + 11}")
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
