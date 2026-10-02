from __future__ import annotations

import time
from dataclasses import dataclass

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
