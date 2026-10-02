from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from iaula.portal.client import Portal


@dataclass(frozen=True)
class Task:
    id: int
    course_id: int
    course: str
    name: str
    due: int
    url: str
    action: str


@dataclass(frozen=True)
class TaskFile:
    name: str
    url: str


@dataclass(frozen=True)
class TaskContext:
    intro: str
    files: list[TaskFile]


def list_tasks(portal: Portal, days: int = 60, past_days: int = 14) -> list[Task]:
    now = int(time.time())
    data = portal.ajax(
        "core_calendar_get_action_events_by_timesort",
        {
            "timesortfrom": now - past_days * 86400,
            "timesortto": now + days * 86400,
            "limitnum": 50,
        },
    )
    return [
        Task(
            e["id"], e["course"]["id"], e["course"]["fullname"],
            e["name"], e["timesort"], e["url"], (e.get("action") or {}).get("name", ""),
        )
        for e in data["events"]
    ]


def task_context(portal: Portal, url: str) -> TaskContext:
    html = portal.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    intro_el = soup.select_one("#intro, .activity-description, .assignintro")
    intro = intro_el.get_text(" ", strip=True) if intro_el else ""
    files: list[TaskFile] = []
    seen: set[str] = set()
    for a in soup.select('a[href*="pluginfile.php"]'):
        href = a["href"]
        if href in seen:
            continue
        seen.add(href)
        label = a.get_text(" ", strip=True)
        name = label or unquote(Path(urlparse(href).path).name)
        files.append(TaskFile(name=name, url=href))
    return TaskContext(intro=intro, files=files)
