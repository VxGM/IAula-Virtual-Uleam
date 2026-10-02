from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

from iaula.portal.client import Portal

DOWNLOADABLE = {"resource", "folder", "url"}


@dataclass(frozen=True)
class Material:
    id: int
    course_id: int
    kind: str
    title: str
    url: str
    section: str


def parse_course_page(html: str, course_id: int) -> list[Material]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[Material] = []
    for sec in soup.select("li.section"):
        head = sec.select_one(".sectionname, h3")
        section = head.get_text(" ", strip=True) if head else ""
        for act in sec.select("li.activity"):
            mod_id = (act.get("id") or "").removeprefix("module-")
            link = act.select_one("a.aalink, .activityname a")
            name = act.select_one(".instancename")
            if not (mod_id.isdigit() and link and name):
                continue
            for hidden in name.select(".accesshide"):
                hidden.extract()
            kind = next(
                (c.removeprefix("modtype_") for c in act.get("class", []) if c.startswith("modtype_")),
                "",
            )
            items.append(
                Material(
                    int(mod_id), course_id, kind,
                    name.get_text(" ", strip=True), link["href"], section,
                )
            )
    return items


def list_materials(portal: Portal, course_id: int) -> list[Material]:
    html = portal.get(f"/course/view.php?id={course_id}").text
    return parse_course_page(html, course_id)
