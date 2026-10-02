from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from iaula.config import Config
from iaula.portal.courses import Course
from iaula.portal.materials import Material
from iaula.portal.tasks import Task

SCHEMA = """
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY, course_id INTEGER, kind TEXT, title TEXT, url TEXT,
    first_seen INTEGER);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY, course_id INTEGER, name TEXT, due INTEGER, first_seen INTEGER,
    url TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY, name TEXT, short TEXT, url TEXT, seen INTEGER);
CREATE TABLE IF NOT EXISTS notebooks (course_id INTEGER PRIMARY KEY, notebook_id TEXT);
CREATE TABLE IF NOT EXISTS uploaded (
    course_id INTEGER, sha256 TEXT, filename TEXT, PRIMARY KEY (course_id, sha256));
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class State:
    def __init__(self, cfg: Config) -> None:
        path: Path = cfg.root / "data" / "state.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.executescript(SCHEMA)
        try:
            self.db.execute("ALTER TABLE tasks ADD COLUMN url TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    def is_baseline(self) -> bool:
        return self.db.execute("SELECT 1 FROM meta WHERE key='baseline'").fetchone() is None

    def mark_baseline(self) -> None:
        self.db.execute("INSERT OR REPLACE INTO meta VALUES ('baseline', ?)", (str(int(time.time())),))
        self.db.commit()

    def record_materials(self, items: list[Material]) -> list[Material]:
        known = {r[0] for r in self.db.execute("SELECT id FROM materials")}
        new = [m for m in items if m.id not in known]
        now = int(time.time())
        self.db.executemany(
            "INSERT INTO materials VALUES (?,?,?,?,?,?)",
            [(m.id, m.course_id, m.kind, m.title, m.url, now) for m in new],
        )
        self.db.commit()
        return new

    def record_tasks(self, items: list[Task]) -> list[Task]:
        known = {r[0]: r[1] for r in self.db.execute("SELECT id, due FROM tasks")}
        new = [t for t in items if t.id not in known or known[t.id] != t.due]
        now = int(time.time())
        self.db.executemany(
            "INSERT OR REPLACE INTO tasks (id, course_id, name, due, first_seen, url) VALUES (?,?,?,?,?,?)",
            [(t.id, t.course_id, t.name, t.due, now, t.url) for t in new],
        )
        self.db.commit()
        return new

    def upsert_courses(self, courses: list[Course]) -> None:
        now = int(time.time())
        self.db.executemany(
            "INSERT OR REPLACE INTO courses VALUES (?,?,?,?,?)",
            [(c.id, c.name, c.short, c.url, now) for c in courses],
        )
        self.db.commit()

    def get_courses(self) -> list[dict]:
        return [
            {"id": r[0], "name": r[1], "short": r[2], "url": r[3]}
            for r in self.db.execute("SELECT id, name, short, url FROM courses ORDER BY short")
        ]

    def materials(self, course_id: int | None = None) -> list[dict]:
        q = "SELECT id, course_id, kind, title, url, first_seen FROM materials"
        args: tuple = ()
        if course_id:
            q += " WHERE course_id=?"
            args = (course_id,)
        q += " ORDER BY first_seen DESC, title"
        cols = ("id", "course_id", "kind", "title", "url", "first_seen")
        return [dict(zip(cols, r)) for r in self.db.execute(q, args)]

    def tasks_all(self) -> list[dict]:
        cols = ("id", "course_id", "name", "due", "first_seen", "url")
        return [dict(zip(cols, r)) for r in self.db.execute(
            "SELECT id, course_id, name, due, first_seen, url FROM tasks ORDER BY due")]

    def uploaded_list(self, course_id: int | None = None) -> list[dict]:
        q = "SELECT course_id, sha256, filename FROM uploaded"
        args: tuple = ()
        if course_id:
            q += " WHERE course_id=?"
            args = (course_id,)
        return [
            {"course_id": r[0], "sha256": r[1], "filename": r[2]}
            for r in self.db.execute(q, args)
        ]

    def notebook_for(self, course_id: int) -> str | None:
        row = self.db.execute("SELECT notebook_id FROM notebooks WHERE course_id=?", (course_id,)).fetchone()
        return row[0] if row else None

    def set_notebook(self, course_id: int, notebook_id: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO notebooks VALUES (?,?)", (course_id, notebook_id))
        self.db.commit()

    def is_uploaded(self, course_id: int, sha256: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM uploaded WHERE course_id=? AND sha256=?", (course_id, sha256)
        ).fetchone() is not None

    def mark_uploaded(self, course_id: int, sha256: str, filename: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO uploaded VALUES (?,?,?)", (course_id, sha256, filename))
        self.db.commit()

    def notebooks(self) -> list[tuple[int, str]]:
        return list(self.db.execute("SELECT course_id, notebook_id FROM notebooks"))
