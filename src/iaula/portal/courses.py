from __future__ import annotations

import re
from dataclasses import dataclass

from iaula.portal.client import Portal


@dataclass(frozen=True)
class Course:
    id: int
    name: str
    short: str
    url: str


_CLEAN = re.compile(r"^A\s*--\s*|\s*/\s*TECNOLOG.*$", re.I)


def short_name(fullname: str) -> str:
    return _CLEAN.sub("", fullname).strip().title()


def list_courses(portal: Portal) -> list[Course]:
    data = portal.ajax(
        "core_course_get_enrolled_courses_by_timeline_classification",
        {"classification": "inprogress", "limit": 0, "offset": 0, "sort": "fullname"},
    )
    return [
        Course(c["id"], c["fullname"], short_name(c["fullname"]), c["viewurl"])
        for c in data["courses"]
    ]


def find_course(courses: list[Course], query: str) -> Course:
    q = query.lower()
    hits = [c for c in courses if q == str(c.id) or q in c.name.lower()]
    if len(hits) != 1:
        names = ", ".join(c.short for c in hits or courses)
        raise LookupError(f"Curso '{query}' → {len(hits)} coincidencias. Opciones: {names}")
    return hits[0]
