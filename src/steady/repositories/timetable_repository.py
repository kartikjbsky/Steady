from __future__ import annotations

from datetime import time, datetime, timezone
from typing import Any

from steady.database import Database


class TimetableRepository:
    """Persistence for a recurring Monday-to-Sunday timetable."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _normalise_time(value: time | str) -> str:
        text = value.strftime("%H:%M") if isinstance(value, time) else str(value)
        return time.fromisoformat(text).strftime("%H:%M")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _normalise_weekday(value: int) -> int:
        weekday = int(value)
        if weekday < 0 or weekday > 6:
            raise ValueError("Weekday must be between Monday (0) and Sunday (6).")
        return weekday

    def list_entries(self) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            """SELECT id, weekday, start_time, title, notes, created_at, updated_at
               FROM timetable_entries
               ORDER BY weekday, start_time, id"""
        )
        return [dict(row) for row in rows]

    def get_slot(self, weekday: int, start_time: time | str) -> dict[str, Any] | None:
        day = self._normalise_weekday(weekday)
        slot = self._normalise_time(start_time)
        rows = self.database.fetch_all(
            """SELECT id, weekday, start_time, title, notes, created_at, updated_at
               FROM timetable_entries WHERE weekday = ? AND start_time = ?""",
            (day, slot),
        )
        return dict(rows[0]) if rows else None

    def save_slot(
        self,
        *,
        weekday: int,
        start_time: time | str,
        title: str,
        notes: str = "",
    ) -> int:
        day = self._normalise_weekday(weekday)
        slot = self._normalise_time(start_time)
        clean_title = str(title).strip()
        clean_notes = str(notes).strip()
        if not clean_title:
            raise ValueError("Add a task or activity name before saving this time slot.")
        if len(clean_title) > 120:
            raise ValueError("Timetable task names must be 120 characters or fewer.")
        if len(clean_notes) > 500:
            raise ValueError("Timetable notes must be 500 characters or fewer.")

        now = self._utc_now()
        return self.database.execute(
            """INSERT INTO timetable_entries
                   (weekday, start_time, title, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(weekday, start_time) DO UPDATE SET
                   title = excluded.title,
                   notes = excluded.notes,
                   updated_at = excluded.updated_at""",
            (day, slot, clean_title, clean_notes, now, now),
        )

    def clear_slot(self, weekday: int, start_time: time | str) -> None:
        day = self._normalise_weekday(weekday)
        slot = self._normalise_time(start_time)
        self.database.execute(
            "DELETE FROM timetable_entries WHERE weekday = ? AND start_time = ?",
            (day, slot),
        )
