from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from iaula.config import Config
from iaula.portal.client import Portal
from iaula.portal.courses import Course
from iaula.portal.materials import Material

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe(name: str) -> str:
    return _BAD.sub("_", name).strip(" .") or "sin_nombre"


def course_dir(cfg: Config, course: Course) -> Path:
    return cfg.root / "downloads" / safe(course.short)


def _filename(resp, material: Material) -> str:
    cd = resp.headers.get("content-disposition", "")
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
    if m:
        return safe(unquote(m.group(1)))
    path_name = unquote(Path(urlparse(resp.url).path).name)
    return safe(path_name) if "." in path_name else safe(material.title)


def download(portal: Portal, cfg: Config, course: Course, material: Material) -> Path | None:
    if material.kind not in {"resource", "folder"}:
        return None
    url = material.url
    if material.kind == "folder":
        url = f"{portal.base}/mod/folder/download_folder.php?id={material.id}"
    resp = portal.get(url, stream=True)
    ctype = resp.headers.get("content-type", "")
    if "text/html" in ctype:
        soup = BeautifulSoup(resp.text, "html.parser")
        link = soup.select_one('a[href*="pluginfile.php"]')
        if not link:
            return None
        resp = portal.get(link["href"], stream=True)
    target_dir = course_dir(cfg, course)
    target_dir.mkdir(parents=True, exist_ok=True)
    name = _filename(resp, material)
    if material.kind == "folder" and not name.lower().endswith(".zip"):
        name = f"{safe(material.title)}.zip"
    target = target_dir / name
    if target.exists():
        return target
    with target.open("wb") as fh:
        for chunk in resp.iter_content(1 << 16):
            fh.write(chunk)
    return target


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
