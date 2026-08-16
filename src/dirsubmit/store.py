"""SQLite 存储：提交记录 + 文案。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Copy, Submission


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str | Path = "dirsubmit.db"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                directory TEXT PRIMARY KEY,
                tier TEXT,
                status TEXT,
                submitted_at TEXT,
                last_checked_at TEXT,
                live_url TEXT,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS copies (
                directory TEXT PRIMARY KEY,
                tagline TEXT,
                description TEXT,
                category TEXT,
                tags TEXT,
                created_at TEXT
            );
            """
        )
        self.conn.commit()

    def upsert_copy(self, copy: Copy):
        self.conn.execute(
            "INSERT INTO copies (directory, tagline, description, category, tags, created_at) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(directory) DO UPDATE SET "
            "tagline=excluded.tagline, description=excluded.description, "
            "category=excluded.category, tags=excluded.tags, created_at=excluded.created_at",
            (copy.directory, copy.tagline, copy.description, copy.category,
             ",".join(copy.tags), _now()),
        )
        self.conn.commit()

    def get_copy(self, directory: str) -> Copy | None:
        row = self.conn.execute(
            "SELECT * FROM copies WHERE directory=?", (directory,)
        ).fetchone()
        if not row:
            return None
        return Copy(
            directory=row["directory"], tagline=row["tagline"],
            description=row["description"], category=row["category"],
            tags=row["tags"].split(",") if row["tags"] else [],
        )

    def set_status(self, directory: str, tier: str, status: str, note: str = "", live_url: str = ""):
        now = _now()
        self.conn.execute(
            "INSERT INTO submissions (directory, tier, status, submitted_at, note, live_url) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(directory) DO UPDATE SET "
            "tier=excluded.tier, status=excluded.status, note=excluded.note, live_url=excluded.live_url",
            (directory, tier, status, now, note, live_url),
        )
        self.conn.commit()

    def get_status(self, directory: str) -> str | None:
        row = self.conn.execute(
            "SELECT status FROM submissions WHERE directory=?", (directory,)
        ).fetchone()
        return row["status"] if row else None

    def update_checked(self, directory: str, status: str, live_url: str = ""):
        self.conn.execute(
            "UPDATE submissions SET status=?, last_checked_at=?, live_url=COALESCE(NULLIF(?, ''), live_url) "
            "WHERE directory=?",
            (status, _now(), live_url, directory),
        )
        self.conn.commit()

    def all_submissions(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM submissions").fetchall()]

    def close(self):
        self.conn.close()
