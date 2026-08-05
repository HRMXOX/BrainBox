"""
core/database.py
مدیریت دیتابیس SQLite برای برنامه MyVault.
جدول‌ها: categories, items, tags, item_tags (many-to-many).
Guide migration خودکار روی schema change با PRAGMA user_version.
"""

from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2  # bump کنید اگر schema تغییر کرد

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,        -- ciphertext برای پسورد، plaintext برای بقیه
    item_type   TEXT NOT NULL CHECK (item_type IN ('note','link','password')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS item_tags (
    item_id INTEGER NOT NULL,
    tag_id  INTEGER NOT NULL,
    PRIMARY KEY (item_id, tag_id),
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES tags  (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_category      ON items (category_id);
CREATE INDEX IF NOT EXISTS idx_items_type           ON items (item_type);
CREATE INDEX IF NOT EXISTS idx_items_title          ON items (title);
CREATE INDEX IF NOT EXISTS idx_item_tags_tag       ON item_tags (tag_id);
"""

DEFAULT_CATEGORIES = [
    ("یادداشت‌ها", "📝"),
    ("لینک‌ها",    "🔗"),
    ("پسوردها",   "🔐"),
    ("کدها",      "💻"),
]


class DatabaseManager:
    """ارتباط امن و ساده با SQLite."""

    def __init__(self, db_path: str | Path = "vault.db") -> None:
        self.db_path = str(db_path)
        # check_same_thread=False چون idle-timer از after استفاده می‌کند نه thread
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._migrate()

    # ──────────────────────────────────────────────
    def _migrate(self) -> None:
        """اجرای schema و migrate بر اساس user_version."""
        cur = self._conn.cursor()
        cur.execute("PRAGMA user_version")
        current = cur.fetchone()[0]
        if current < SCHEMA_VERSION:
            self._conn.executescript(SCHEMA_SQL)
            self._seed_defaults()
            cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._conn.commit()

    def _seed_defaults(self) -> None:
        cur = self._conn.cursor()
        for name, icon in DEFAULT_CATEGORIES:
            cur.execute(
                "INSERT OR IGNORE INTO categories (name, icon) VALUES (?, ?)",
                (name, icon),
            )
        self._conn.commit()

    # ── CRUD دسته‌بندی ────────────────────────────
    def list_categories(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def add_category(self, name: str, icon: str | None = None) -> int:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO categories (name, icon) VALUES (?, ?)",
            (name, icon),
        )
        self._conn.commit()
        return cur.lastrowid  # ممکن است None باشد اگر duplicate بود

    # ── CRUD آیتم ─────────────────────────────────
    def add_item(
        self,
        *,
        category_id: int | None,
        title: str,
        content: str,
        item_type: str,
        tags: list[str] | None = None,
    ) -> int:
        if item_type not in ("note", "link", "password"):
            raise ValueError(f"item_type invalid: {item_type}")
        now = datetime.now().isoformat(timespec="seconds")
        cur = self._conn.execute(
            """INSERT INTO items
                 (category_id, title, content, item_type, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (category_id, title, content, item_type, now, now),
        )
        item_id = cur.lastrowid
        if tags:
            self._set_tags(item_id, tags)
        self._conn.commit()
        return item_id  # type: ignore[return-value]

    def _set_tags(self, item_id: int, tags: list[str]) -> None:
        cur = self._conn.cursor()
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            tag_id = cur.execute(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            ).fetchone()[0]
            cur.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (item_id, tag_id),
            )

    def get_items_by_category(self, category_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT i.*,
                      (SELECT GROUP_CONCAT(t.name, ',')
                          FROM item_tags it JOIN tags t ON t.id = it.tag_id
                          WHERE it.item_id = i.id) AS tags
                 FROM items i
                WHERE i.category_id = ?
                ORDER BY i.updated_at DESC""",
            (category_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_items(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT i.*,
                      (SELECT GROUP_CONCAT(t.name, ',')
                          FROM item_tags it JOIN tags t ON t.id = it.tag_id
                          WHERE it.item_id = i.id) AS tags
                 FROM items i
                ORDER BY i.updated_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str) -> list[dict[str, Any]]:
        """جستجو در title و content و tags. Case-insensitive + LIKE."""
        q = f"%{query.strip()}%"
        rows = self._conn.execute(
            """SELECT DISTINCT i.*,
                      (SELECT GROUP_CONCAT(t.name, ',')
                          FROM item_tags it JOIN tags t ON t.id = it.tag_id
                          WHERE it.item_id = i.id) AS tags
                 FROM items i
            LEFT JOIN item_tags it ON it.item_id = i.id
            LEFT JOIN tags t ON t.id = it.tag_id
                WHERE i.title LIKE ?
                   OR i.content LIKE ?
                   OR t.name LIKE ?
                ORDER BY i.updated_at DESC""",
            (q, q, q),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_item(self, item_id: int) -> None:
        self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self._conn.commit()

    def update_item(
        self,
        item_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
        category_id: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        cur = self._conn.cursor()
        if title is not None:
            cur.execute("UPDATE items SET title=?, updated_at=? WHERE id=?",
                        (title, now, item_id))
        if content is not None:
            cur.execute("UPDATE items SET content=?, updated_at=? WHERE id=?",
                        (content, now, item_id))
        if category_id is not None:
            cur.execute("UPDATE items SET category_id=?, updated_at=? WHERE id=?",
                        (category_id, now, item_id))
        if tags is not None:
            # tags را دوباره بنویس
            self._conn.execute("DELETE FROM item_tags WHERE item_id=?", (item_id,))
            self._set_tags(item_id, tags)
        self._conn.commit()

    # ── برای backup ──────────────────────────────
    def export_plaintext_dict(self) -> dict[str, list[dict]]:
        """دریافت تمام داده‌ها به صورت dict — decrypt bởi caller انجام می‌شود."""
        tables = ["categories", "items", "tags", "item_tags"]
        out: dict[str, list[dict]] = {}
        for t in tables:
            rows = self._conn.execute(f"SELECT * FROM {t}").fetchall()
            out[t] = [dict(r) for r in rows]
        return out

    def close(self) -> None:
        self._conn.close()
