from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from iaula.config import Config
from iaula.portal.courses import Course, short_name
from iaula.portal.materials import Material
from iaula.portal.tasks import Task


def fmt_due(ts: int) -> str:
    return time.strftime("%a %d/%m %H:%M", time.localtime(ts))


def days_left(ts: int) -> int:
    return int((ts - time.time()) // 86400)


def task_line(t: Task) -> str:
    d = days_left(t.due)
    when = "VENCIDA" if d < 0 else "hoy" if d == 0 else f"en {d}d"
    return f"[{when}] {short_name(t.course)}: {t.name} — {fmt_due(t.due)}"


def build_report(
    courses: list[Course], new_materials: list[Material], new_tasks: list[Task],
    upcoming: list[Task], baseline: bool,
) -> dict:
    names = {c.id: c.short for c in courses}
    return {
        "baseline": baseline,
        "new_materials": [
            {"course": names.get(m.course_id, str(m.course_id)), "course_id": m.course_id,
             "id": m.id, "kind": m.kind, "title": m.title, "section": m.section, "url": m.url}
            for m in new_materials
        ],
        "new_tasks": [
            {"course": short_name(t.course), "course_id": t.course_id, "id": t.id,
             "name": t.name, "due": fmt_due(t.due), "url": t.url}
            for t in new_tasks
        ],
        "upcoming_tasks": [
            {"course": short_name(t.course), "course_id": t.course_id, "id": t.id,
             "name": t.name, "due": fmt_due(t.due), "days_left": days_left(t.due), "url": t.url}
            for t in upcoming
        ],
    }


def render_text(rep: dict) -> str:
    lines: list[str] = []
    if rep["baseline"]:
        lines.append("Primera corrida: línea base guardada (sin novedades).")
    else:
        by_course: dict[str, list[str]] = {}
        for m in rep["new_materials"]:
            by_course.setdefault(m["course"], []).append(m["title"])
        for c, titles in by_course.items():
            lines.append(f"{c}: {len(titles)} material(es) nuevo(s): {', '.join(titles)}")
        for t in rep["new_tasks"]:
            lines.append(f"Tarea nueva/cambiada — {t['course']}: {t['name']} ({t['due']})")
        if not (rep["new_materials"] or rep["new_tasks"]):
            lines.append("Sin novedades.")
    lines.append("")
    lines.append("Tareas pendientes:")
    if rep["upcoming_tasks"]:
        for t in rep["upcoming_tasks"]:
            when = "VENCIDA" if t["days_left"] < 0 else "hoy" if t["days_left"] == 0 else f"en {t['days_left']}d"
            lines.append(f"  [{when}] {t['course']}: {t['name']} — {t['due']}")
    else:
        lines.append("  ninguna")
    return "\n".join(lines)


def save_report(cfg: Config, rep: dict) -> Path:
    out = cfg.root / "data" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{time.strftime('%Y-%m-%d')}.md"
    path.write_text(render_text(rep) + "\n", encoding="utf-8")
    (out / "latest.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def notify(title: str, message: str) -> None:
    ps = (
        "[void][Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime];"
        "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent('ToastText02');"
        "$n=$t.GetElementsByTagName('text');"
        f"$n.Item(0).AppendChild($t.CreateTextNode('{_esc(title)}'))|Out-Null;"
        f"$n.Item(1).AppendChild($t.CreateTextNode('{_esc(message)}'))|Out-Null;"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('IAula').Show("
        "[Windows.UI.Notifications.ToastNotification]::new($t))"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=30)


def _esc(s: str) -> str:
    return s.replace("'", "''")[:240]
