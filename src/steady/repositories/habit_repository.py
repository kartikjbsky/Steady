from __future__ import annotations

from datetime import date, datetime
import sqlite3
from typing import Any

from steady.database import Database


class HabitRepository:
    """CRUD, scheduling and reminder operations for reusable habits."""

    CATEGORIES = {"study", "research", "wellbeing", "health", "personal", "other"}
    FILTERS = {"active", "paused", "archived", "all"}

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _date_text(value: date | str) -> str:
        text = value.isoformat() if isinstance(value, date) else str(value)
        return date.fromisoformat(text).isoformat()

    @staticmethod
    def _validate_mask(mask: str) -> str:
        mask = str(mask)
        if len(mask) != 7 or set(mask) - {"0", "1"} or "1" not in mask:
            raise ValueError("Choose at least one weekday for this habit.")
        return mask

    @staticmethod
    def _validate_reminder(enabled: bool, reminder_time: str | None) -> tuple[int, str | None]:
        if not enabled:
            return 0, None
        if not reminder_time:
            raise ValueError("Choose a reminder time or turn the reminder off.")
        try:
            parsed = datetime.strptime(reminder_time, "%H:%M")
        except ValueError as exc:
            raise ValueError("Reminder time must use 24-hour HH:MM format.") from exc
        return 1, parsed.strftime("%H:%M")

    def create_habit(
        self,
        *,
        name: str,
        description: str = "",
        category: str = "other",
        weekday_mask: str = "1111111",
        start_date: date | str | None = None,
        reminder_enabled: bool = False,
        reminder_time: str | None = None,
    ) -> int:
        name = str(name).strip()
        if not name:
            raise ValueError("A habit name is required.")
        if len(name) > 100:
            raise ValueError("Habit names must be 100 characters or fewer.")
        category = str(category).lower()
        if category not in self.CATEGORIES:
            raise ValueError("Choose a valid habit category.")
        mask = self._validate_mask(weekday_mask)
        first_day = self._date_text(start_date or date.today())
        reminder_enabled, reminder_time = self._validate_reminder(
            reminder_enabled, reminder_time
        )
        rows = self.database.fetch_all("SELECT COALESCE(MAX(sort_order), 0) AS n FROM habits")
        sort_order = int(rows[0]["n"]) + 10
        try:
            return self.database.execute(
                """INSERT INTO habits
                   (name, description, weekday_mask, category, start_date,
                    reminder_enabled, reminder_time, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, str(description).strip(), mask, category, first_day,
                 reminder_enabled, reminder_time, sort_order),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("A habit with that name already exists.") from exc

    def update_habit(self, habit_id: int, **changes: Any) -> None:
        allowed = {
            "name", "description", "category", "weekday_mask", "start_date",
            "reminder_enabled", "reminder_time",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported habit fields: {', '.join(sorted(unknown))}")
        if not changes:
            return
        existing = self.get_habit(habit_id)
        if existing is None:
            raise ValueError("This habit no longer exists.")

        if "name" in changes:
            changes["name"] = str(changes["name"]).strip()
            if not changes["name"]:
                raise ValueError("A habit name is required.")
            if len(changes["name"]) > 100:
                raise ValueError("Habit names must be 100 characters or fewer.")
        if "description" in changes:
            changes["description"] = str(changes["description"]).strip()
        if "category" in changes:
            changes["category"] = str(changes["category"]).lower()
            if changes["category"] not in self.CATEGORIES:
                raise ValueError("Choose a valid habit category.")
        if "weekday_mask" in changes:
            changes["weekday_mask"] = self._validate_mask(changes["weekday_mask"])
        if "start_date" in changes:
            changes["start_date"] = self._date_text(changes["start_date"])

        reminder_enabled = bool(changes.get("reminder_enabled", existing["reminder_enabled"]))
        reminder_time = changes.get("reminder_time", existing["reminder_time"])
        if "reminder_enabled" in changes or "reminder_time" in changes:
            enabled_value, time_value = self._validate_reminder(reminder_enabled, reminder_time)
            changes["reminder_enabled"] = enabled_value
            changes["reminder_time"] = time_value

        assignments = ", ".join(f"{column} = ?" for column in changes)
        values = tuple(changes.values()) + (int(habit_id),)
        try:
            self.database.execute(f"UPDATE habits SET {assignments} WHERE id = ?", values)
        except sqlite3.IntegrityError as exc:
            raise ValueError("A habit with that name already exists.") from exc

    def get_habit(self, habit_id: int) -> dict[str, Any] | None:
        rows = self.database.fetch_all(
            """SELECT id, name, description, weekday_mask, is_active, is_builtin,
                      category, start_date, reminder_enabled, reminder_time,
                      reminder_last_fired_date, archived_at, sort_order
               FROM habits WHERE id = ?""",
            (int(habit_id),),
        )
        return dict(rows[0]) if rows else None

    def list_habits(self, state: str = "active") -> list[dict[str, Any]]:
        if state not in self.FILTERS:
            raise ValueError("Unknown habit filter.")
        query = """SELECT id, name, description, weekday_mask, is_active, is_builtin,
                          category, start_date, reminder_enabled, reminder_time,
                          reminder_last_fired_date, archived_at, sort_order
                   FROM habits"""
        if state == "active":
            query += " WHERE archived_at IS NULL AND is_active = 1"
        elif state == "paused":
            query += " WHERE archived_at IS NULL AND is_active = 0"
        elif state == "archived":
            query += " WHERE archived_at IS NOT NULL"
        query += " ORDER BY sort_order, name COLLATE NOCASE, id"
        return [dict(row) for row in self.database.fetch_all(query)]

    def set_active(self, habit_id: int, active: bool) -> None:
        habit = self.get_habit(habit_id)
        if habit is None:
            raise ValueError("This habit no longer exists.")
        if habit["archived_at"] is not None:
            raise ValueError("Restore this habit before activating it.")
        self.database.execute(
            "UPDATE habits SET is_active = ? WHERE id = ?",
            (1 if active else 0, int(habit_id)),
        )

    def archive(self, habit_id: int) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        self.database.execute(
            """UPDATE habits SET is_active = 0, archived_at = ?
               WHERE id = ? AND archived_at IS NULL""",
            (now, int(habit_id)),
        )

    def restore(self, habit_id: int) -> None:
        self.database.execute(
            "UPDATE habits SET is_active = 1, archived_at = NULL WHERE id = ?",
            (int(habit_id),),
        )

    def delete_archived(self, habit_id: int) -> str:
        """Permanently delete an archived habit and its dependent check-ins.

        Active or paused habits cannot be deleted; they must be archived first.
        The schema's ON DELETE CASCADE removes this habit's habit_entries.
        """
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT name, archived_at FROM habits WHERE id = ?",
                (int(habit_id),),
            ).fetchone()
            if row is None:
                raise ValueError("This habit no longer exists.")
            if row["archived_at"] is None:
                raise ValueError("Only archived habits can be permanently deleted.")
            name = str(row["name"])
            connection.execute("DELETE FROM habits WHERE id = ?", (int(habit_id),))
        return name

    def list_month_entries(self, year: int, month: int) -> dict[tuple[int, str], str]:
        """Return recorded habit statuses for a month, keyed by (habit_id, ISO date)."""
        from calendar import monthrange

        if not 1 <= int(month) <= 12:
            raise ValueError("Month must be between 1 and 12.")
        first_day = date(int(year), int(month), 1).isoformat()
        last_day = date(int(year), int(month), monthrange(int(year), int(month))[1]).isoformat()
        rows = self.database.fetch_all(
            """SELECT habit_id, entry_date, status
               FROM habit_entries
               WHERE entry_date BETWEEN ? AND ?
               ORDER BY entry_date, habit_id""",
            (first_day, last_day),
        )
        return {
            (int(row["habit_id"]), str(row["entry_date"])): str(row["status"])
            for row in rows
        }

    def due_habit_reminders(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Claim scheduled reminders due by local time, at most once per habit per day.

        If Steady was temporarily asleep or the app opened after the chosen time,
        the reminder is delivered on the next poll rather than silently missed.
        """
        local_now = now.astimezone() if now and now.tzinfo else (now or datetime.now())
        today = local_now.date().isoformat()
        hhmm = local_now.strftime("%H:%M")
        weekday = local_now.weekday()
        due: list[dict[str, Any]] = []
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT id, name, description, weekday_mask
                   FROM habits
                   WHERE is_active = 1 AND archived_at IS NULL
                     AND start_date <= ? AND reminder_enabled = 1
                     AND reminder_time <= ?
                     AND reminder_last_fired_date IS NOT ?""",
                (today, hhmm, today),
            ).fetchall()
            for row in rows:
                if row["weekday_mask"][weekday] != "1":
                    continue
                cursor = connection.execute(
                    """UPDATE habits SET reminder_last_fired_date = ?
                       WHERE id = ? AND (reminder_last_fired_date IS NULL OR reminder_last_fired_date != ?)""",
                    (today, int(row["id"]), today),
                )
                if cursor.rowcount:
                    due.append(dict(row))
        return due
