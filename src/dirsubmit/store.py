"""SQLite 存储：提交记录 + 文案。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Copy, Submission


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str | Path = "dirsubmit.db", product_url: str = ""):
        self.product_key = product_url.strip().rstrip("/")
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
        self.conn.execute("BEGIN")
        try:
            for table in ("submissions", "copies"):
                columns = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
                if "product_key" not in columns:
                    self.conn.execute(f"ALTER TABLE {table} RENAME TO {table}_legacy")
                    definitions = {
                        "submissions": "tier TEXT, status TEXT, submitted_at TEXT, last_checked_at TEXT, live_url TEXT, note TEXT",
                        "copies": "tagline TEXT, description TEXT, category TEXT, tags TEXT, created_at TEXT",
                    }
                    self.conn.execute(f"CREATE TABLE {table} (product_key TEXT NOT NULL, directory TEXT, {definitions[table]}, PRIMARY KEY(product_key, directory))")
                    old = [r[1] for r in self.conn.execute(f"PRAGMA table_info({table}_legacy)")]
                    names = ",".join(old)
                    self.conn.execute(f"INSERT INTO {table} (product_key,{names}) SELECT '',{names} FROM {table}_legacy")
                    self.conn.execute(f"DROP TABLE {table}_legacy")
        except Exception:
            self.conn.rollback()
            raise
        self.conn.commit()

    def upsert_copy(self, copy: Copy):
        self.conn.execute(
            "INSERT INTO copies (product_key, directory, tagline, description, category, tags, created_at) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(product_key, directory) DO UPDATE SET "
            "tagline=excluded.tagline, description=excluded.description, "
            "category=excluded.category, tags=excluded.tags, created_at=excluded.created_at",
            (self.product_key, copy.directory, copy.tagline, copy.description, copy.category,
             ",".join(copy.tags), _now()),
        )
        self.conn.commit()

    def get_copy(self, directory: str) -> Copy | None:
        row = self.conn.execute(
            "SELECT * FROM copies WHERE product_key=? AND directory=?", (self.product_key, directory,)
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
            "INSERT INTO submissions (product_key, directory, tier, status, submitted_at, note, live_url) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(product_key, directory) DO UPDATE SET "
            "tier=excluded.tier, status=excluded.status, note=excluded.note, live_url=excluded.live_url, submitted_at=COALESCE(excluded.submitted_at, submissions.submitted_at)",
            (self.product_key, directory, tier, status, now if status == "submitted" else None, note, live_url),
        )
        self.conn.commit()

    def protected_equivalent_status(self, directory: str, equivalent_product_keys: tuple[str, ...]) -> str | None:
        """Read only caller-supplied exact URL aliases; infer no sibling/eTLD scope."""
        keys = tuple(dict.fromkeys(k.lower().rstrip("/") for k in equivalent_product_keys))
        if not keys:
            return None
        placeholders = ",".join("?" for _ in keys)
        row = self.conn.execute(
            "SELECT status FROM submissions WHERE directory=? "
            "AND status IN ('submitted','approved','unverified') "
            f"AND lower(rtrim(product_key,'/')) IN ({placeholders}) LIMIT 1",
            (directory, *keys),
        ).fetchone()
        return row["status"] if row else None

    def reserve_attempt(self, directory: str, tier: str, note: str = "", *, equivalent_product_keys: tuple[str, ...] = ()) -> bool:
        """Atomically guard the original product key plus explicit exact URL aliases."""
        if not self.product_key:
            raise ValueError("A product-scoped Store is required")
        try:
            if equivalent_product_keys:
                # Serialize alias reads and reservation across different Store handles.
                self.conn.execute("BEGIN IMMEDIATE")
                if self.protected_equivalent_status(directory, equivalent_product_keys):
                    self.conn.rollback()
                    return False
            cursor = self.conn.execute(
                "INSERT INTO submissions (product_key,directory,tier,status,note) VALUES (?,?,?,'unverified',?) "
                "ON CONFLICT(product_key,directory) DO UPDATE SET tier=excluded.tier,status='unverified',note=excluded.note "
                "WHERE submissions.status NOT IN ('submitted','approved','unverified')",
                (self.product_key, directory, tier, note),
            )
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return cursor.rowcount == 1

    def get_status(self, directory: str) -> str | None:
        row = self.conn.execute(
            "SELECT status FROM submissions WHERE product_key=? AND directory=?", (self.product_key, directory,)
        ).fetchone()
        return row["status"] if row else None

    def update_checked(self, directory: str, status: str, live_url: str = "", note: str = ""):
        self.conn.execute(
            "UPDATE submissions SET status=?, last_checked_at=?, note=COALESCE(NULLIF(?, ''), note), live_url=COALESCE(NULLIF(?, ''), live_url) "
            "WHERE product_key=? AND directory=?",
            (status, _now(), note, live_url, self.product_key, directory),
        )
        self.conn.commit()

    def all_submissions(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM submissions WHERE product_key=?", (self.product_key,)).fetchall()]

    def close(self):
        self.conn.close()
