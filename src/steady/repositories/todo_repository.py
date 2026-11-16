from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from steady.database import Database


class TodoRepository:
    """Persistence for one-off to-do items and their deadline notifications."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _normalise_date(value: date | str) -> str:
        text = value.isoformat() if isinstance(value, date) else str(value)
        return date.fromisoformat(text).isoformat()

    @staticmethod
    def _normalise_time(value: time | str) -> str:
        text = value.strftime("%H:%M") if isinstance(value, time) else str(value)
        parsed = time.fromisoformat(text)
        return parsed.strftime("%H:%M")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def list_items(self, *, include_completed: bool = True) -> list[dict[str, Any]]:
        where = "" if include_completed else "WHERE is_completed = 0"
        rows = self.database.fetch_all(
            f"""SELECT id, title, deadline_date, is_completed, notification_enabled,
                       notification_time, notified_at, created_at, updated_at
                FROM todo_items {where}
                ORDER BY is_completed, deadline_date, notification_time, id"""
        )
        return [dict(row) for row in rows]

    def create(
        self,
        *,
        title: str,
        deadline_date: date | str,
        notification_enabled: bool = True,
        notification_time: time | str = "09:00",
    ) -> int:
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("A to-do title is required.")
        if len(clean_title) > 120:
            raise ValueError("To-do titles must be 120 characters or fewer.")
        day_value = self._normalise_date(deadline_date)
        time_value = self._normalise_time(notification_time)
        return self.database.execute(
            """INSERT INTO todo_items
                   (title, deadline_date, notification_enabled, notification_time)
               VALUES (?, ?, ?, ?)""",
            (clean_title, day_value, int(bool(notification_enabled)), time_value),
        )

    def update(self, item_id: int, **changes: Any) -> None:
        allowed = {"title", "deadline_date", "is_completed", "notification_enabled", "notification_time"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported to-do fields: {', '.join(sorted(unknown))}")
        if not changes:
            return

        existing = self.database.fetch_all(
            "SELECT deadline_date, notification_time, notification_enabled, is_completed FROM todo_items WHERE id = ?",
            (int(item_id),),
        )
        if not existing:
            raise ValueError("This to-do item no longer exists.")
        previous = dict(existing[0])

        if "title" in changes:
            title = str(changes["title"]).strip()
            if not title:
                raise ValueError("A to-do title is required.")
            if len(title) > 120:
                raise ValueError("To-do titles must be 120 characters or fewer.")
            changes["title"] = title
        if "deadline_date" in changes:
            changes["deadline_date"] = self._normalise_date(changes["deadline_date"])
        if "notification_time" in changes:
            changes["notification_time"] = self._normalise_time(changes["notification_time"])
        for flag in ("is_completed", "notification_enabled"):
            if flag in changes:
                changes[flag] = int(bool(changes[flag]))

        deadline_changed = (
            changes.get("deadline_date", previous["deadline_date"]) != previous["deadline_date"]
            or changes.get("notification_time", previous["notification_time"]) != previous["notification_time"]
        )
        notifications_reenabled = (
            not bool(previous["notification_enabled"])
            and bool(changes.get("notification_enabled", previous["notification_enabled"]))
        )
        reopened = bool(previous["is_completed"]) and not bool(
            changes.get("is_completed", previous["is_completed"])
        )
        if deadline_changed or notifications_reenabled or reopened:
            changes["notified_at"] = None
        changes["updated_at"] = self._utc_now()

        assignments = ", ".join(f"{column} = ?" for column in changes)
        values = tuple(changes.values()) + (int(item_id),)
        self.database.execute(f"UPDATE todo_items SET {assignments} WHERE id = ?", values)

    def set_completed(self, item_id: int, completed: bool) -> None:
        self.update(item_id, is_completed=completed)

    def set_notification_enabled(self, item_id: int, enabled: bool) -> None:
        self.update(item_id, notification_enabled=enabled)

    def delete(self, item_id: int) -> None:
        self.database.execute("DELETE FROM todo_items WHERE id = ?", (int(item_id),))

    def due_notifications(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Return unfinished notified items whose local deadline time has arrived."""
        local_now = now or datetime.now().astimezone().replace(tzinfo=None)
        cutoff = local_now.strftime("%Y-%m-%dT%H:%M")
        rows = self.database.fetch_all(
            """SELECT id, title, deadline_date, notification_time
               FROM todo_items
               WHERE is_completed = 0
                 AND notification_enabled = 1
                 AND notified_at IS NULL
                 AND (deadline_date || 'T' || notification_time) <= ?
               ORDER BY deadline_date, notification_time, id""",
            (cutoff,),
        )
        return [dict(row) for row in rows]

    def mark_notified(self, item_id: int) -> bool:
        """Atomically mark a due item so only one alert is emitted for it."""
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE todo_items SET notified_at = ?, updated_at = ?
                   WHERE id = ? AND notified_at IS NULL
                     AND is_completed = 0 AND notification_enabled = 1""",
                (self._utc_now(), self._utc_now(), int(item_id)),
            )
            return cursor.rowcount == 1
