from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 3
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_MISS_REASONS = (
    ("low_energy", "Low energy", 10),
    ("ran_out_of_time", "Ran out of time", 20),
    ("got_distracted", "Got distracted", 30),
    ("forgot", "Forgot about it", 40),
    ("task_too_large", "The task felt too large", 50),
    ("unexpected_event", "Something unexpected came up", 60),
    ("unclear_next_step", "I was unsure how to start", 70),
    ("other", "Something else", 80),
)

DEFAULT_HABITS = (
    ("Morning exercise", "A little movement counts.", "1111111", 10),
    ("Meditation", "Even a short pause is useful.", "1111111", 20),
)


class Database:
    """Small SQLite database manager with per-connection safety settings."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the current schema or migrate older databases in place."""
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {current_version} is newer than "
                    f"this application supports ({SCHEMA_VERSION}). Update Steady."
                )

            if current_version == 0:
                connection.executescript(schema)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            else:
                if current_version == 1:
                    # v1 -> v2: distinguish focus sessions from break sessions.
                    columns = {
                        row["name"]
                        for row in connection.execute("PRAGMA table_info(focus_sessions)").fetchall()
                    }
                    if "session_type" not in columns:
                        connection.execute(
                            """ALTER TABLE focus_sessions
                               ADD COLUMN session_type TEXT NOT NULL DEFAULT 'focus'
                               CHECK (session_type IN ('focus', 'short_break', 'long_break'))"""
                        )
                    current_version = 2
                    connection.execute("PRAGMA user_version = 2")

                if current_version == 2:
                    # v2 -> v3: add custom-habit management fields without
                    # replacing the habits table or losing existing check-ins.
                    columns = {
                        row["name"]
                        for row in connection.execute("PRAGMA table_info(habits)").fetchall()
                    }
                    additions = (
                        ("category", "TEXT NOT NULL DEFAULT 'other'"),
                        ("start_date", "TEXT NOT NULL DEFAULT '1970-01-01'"),
                        ("reminder_enabled", "INTEGER NOT NULL DEFAULT 0"),
                        ("reminder_time", "TEXT"),
                        ("reminder_last_fired_date", "TEXT"),
                        ("archived_at", "TEXT"),
                    )
                    for column, definition in additions:
                        if column not in columns:
                            connection.execute(
                                f"ALTER TABLE habits ADD COLUMN {column} {definition}"
                            )
                    connection.execute(
                        """CREATE INDEX IF NOT EXISTS idx_habits_reminder
                           ON habits(is_active, reminder_enabled, reminder_time)"""
                    )
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

            self._seed_defaults(connection)

    @staticmethod
    def _seed_defaults(connection: sqlite3.Connection) -> None:
        connection.executemany(
            """INSERT INTO miss_reasons(code, label, sort_order)
               VALUES (?, ?, ?)
               ON CONFLICT(code) DO NOTHING""",
            DEFAULT_MISS_REASONS,
        )
        # Seed built-in habits only once. If a user later archives and
        # permanently deletes one, it must not silently reappear at next launch.
        seeded = connection.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?",
            ("default_habits_seeded_v1",),
        ).fetchone()
        if seeded is None:
            connection.executemany(
                """INSERT INTO habits(name, description, weekday_mask, is_builtin, sort_order)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(name) DO NOTHING""",
                DEFAULT_HABITS,
            )
            connection.execute(
                """INSERT INTO app_settings(setting_key, setting_value)
                   VALUES ('default_habits_seeded_v1', '1')
                   ON CONFLICT(setting_key) DO NOTHING"""
            )

    def fetch_all(self, query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(query, parameters).fetchall())

    def execute(self, query: str, parameters: tuple = ()) -> int:
        """Execute a write query and return its last inserted row ID (if any)."""
        with self.connect() as connection:
            cursor = connection.execute(query, parameters)
            return int(cursor.lastrowid or 0)
