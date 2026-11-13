from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from steady.database import Database


class FocusRepository:
    """Persistence for focus sessions and local reminders."""

    SESSION_TYPES = {"focus", "short_break", "long_break"}
    SESSION_OUTCOMES = {"completed", "stopped", "interrupted"}
    REPEAT_RULES = {"none", "daily", "weekdays", "weekly"}

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _utc_text(value: datetime | None = None) -> str:
        current = value or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.astimezone()
        return current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def local_datetime_text(value: str) -> str:
        parsed = FocusRepository._parse_datetime(value).astimezone()
        return parsed.strftime("%a, %d %b %Y · %I:%M %p")

    # Focus sessions -----------------------------------------------------
    def start_session(
        self,
        *,
        planned_seconds: int,
        session_type: str = "focus",
        linked_task_id: int | None = None,
    ) -> int:
        if planned_seconds <= 0:
            raise ValueError("Planned duration must be greater than zero.")
        if session_type not in self.SESSION_TYPES:
            raise ValueError("Unknown session type.")
        return self.database.execute(
            """INSERT INTO focus_sessions
                   (linked_task_id, started_at, planned_seconds, outcome, session_type)
               VALUES (?, ?, ?, 'running', ?)""",
            (linked_task_id, self._utc_text(), int(planned_seconds), session_type),
        )

    def finish_session(
        self,
        session_id: int,
        *,
        outcome: str,
        actual_seconds: int,
        note: str = "",
    ) -> None:
        if outcome not in self.SESSION_OUTCOMES:
            raise ValueError("Invalid focus-session outcome.")
        if actual_seconds < 0:
            raise ValueError("Actual duration cannot be negative.")
        self.database.execute(
            """UPDATE focus_sessions
               SET ended_at = ?, actual_seconds = ?, outcome = ?, note = ?
               WHERE id = ? AND outcome = 'running'""",
            (self._utc_text(), int(actual_seconds), outcome, note.strip(), int(session_id)),
        )

    def recover_open_sessions(self) -> int:
        """Mark sessions left running by a crash or previous app exit as interrupted."""
        rows = self.database.fetch_all(
            "SELECT id FROM focus_sessions WHERE outcome = 'running'"
        )
        if not rows:
            return 0
        now = self._utc_text()
        with self.database.connect() as connection:
            connection.execute(
                """UPDATE focus_sessions
                   SET ended_at = ?, outcome = 'interrupted',
                       note = CASE WHEN note = '' THEN 'Application closed before the session was finalised.' ELSE note END
                   WHERE outcome = 'running'""",
                (now,),
            )
        return len(rows)

    def list_sessions(self, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            """SELECT fs.id, fs.started_at, fs.ended_at, fs.planned_seconds,
                      fs.actual_seconds, fs.outcome, fs.note, fs.session_type,
                      t.title AS task_title
               FROM focus_sessions AS fs
               LEFT JOIN tasks AS t ON t.id = fs.linked_task_id
               ORDER BY fs.started_at DESC, fs.id DESC
               LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        )
        return [dict(row) for row in rows]

    def get_focus_totals(self, days: int = 7) -> dict[str, int]:
        days = max(1, min(int(days), 365))
        since = self._utc_text(datetime.now(timezone.utc) - timedelta(days=days))
        rows = self.database.fetch_all(
            """SELECT COUNT(*) AS sessions,
                      COALESCE(SUM(actual_seconds), 0) AS seconds
               FROM focus_sessions
               WHERE session_type = 'focus'
                 AND outcome = 'completed'
                 AND started_at >= ?""",
            (since,),
        )
        row = rows[0]
        return {"sessions": int(row["sessions"]), "seconds": int(row["seconds"])}

    # Reminders ----------------------------------------------------------
    def create_reminder(
        self,
        *,
        title: str,
        due_at: datetime,
        message: str = "",
        repeat_rule: str = "none",
    ) -> int:
        title = title.strip()
        if not title:
            raise ValueError("A reminder title is required.")
        if repeat_rule not in self.REPEAT_RULES:
            raise ValueError("Invalid reminder repeat rule.")
        return self.database.execute(
            """INSERT INTO reminders(title, message, due_at, repeat_rule)
               VALUES (?, ?, ?, ?)""",
            (title, message.strip(), self._utc_text(due_at), repeat_rule),
        )

    def list_reminders(self, include_disabled: bool = True) -> list[dict[str, Any]]:
        query = """SELECT id, title, message, due_at, is_enabled, repeat_rule,
                          last_fired_at, dismissed_at
                   FROM reminders"""
        if not include_disabled:
            query += " WHERE is_enabled = 1"
        query += " ORDER BY is_enabled DESC, due_at ASC, id ASC"
        return [dict(row) for row in self.database.fetch_all(query)]

    def set_reminder_enabled(self, reminder_id: int, enabled: bool) -> None:
        self.database.execute(
            "UPDATE reminders SET is_enabled = ? WHERE id = ?",
            (1 if enabled else 0, int(reminder_id)),
        )

    def delete_reminder(self, reminder_id: int) -> None:
        self.database.execute("DELETE FROM reminders WHERE id = ?", (int(reminder_id),))

    def due_reminders(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now_text = self._utc_text(now)
        rows = self.database.fetch_all(
            """SELECT id, title, message, due_at, repeat_rule
               FROM reminders
               WHERE is_enabled = 1 AND due_at <= ?
               ORDER BY due_at ASC, id ASC""",
            (now_text,),
        )
        return [dict(row) for row in rows]

    def mark_reminder_fired(
        self, reminder_id: int, fired_at: datetime | None = None
    ) -> dict[str, Any] | None:
        rows = self.database.fetch_all(
            "SELECT id, title, message, due_at, repeat_rule FROM reminders WHERE id = ? AND is_enabled = 1",
            (int(reminder_id),),
        )
        if not rows:
            return None
        reminder = dict(rows[0])
        fired = fired_at or datetime.now(timezone.utc)
        if fired.tzinfo is None:
            fired = fired.astimezone()
        fired = fired.astimezone(timezone.utc)
        next_due: datetime | None = None
        rule = reminder["repeat_rule"]
        if rule == "daily":
            next_due = self._parse_datetime(reminder["due_at"]) + timedelta(days=1)
            while next_due <= fired:
                next_due += timedelta(days=1)
        elif rule == "weekly":
            next_due = self._parse_datetime(reminder["due_at"]) + timedelta(days=7)
            while next_due <= fired:
                next_due += timedelta(days=7)
        elif rule == "weekdays":
            next_due = self._parse_datetime(reminder["due_at"])
            while next_due <= fired or next_due.weekday() >= 5:
                next_due += timedelta(days=1)

        if rule == "none":
            self.database.execute(
                """UPDATE reminders SET is_enabled = 0, last_fired_at = ?, dismissed_at = NULL
                   WHERE id = ?""",
                (self._utc_text(fired), int(reminder_id)),
            )
        else:
            assert next_due is not None
            # Skip any missed occurrences rather than producing a burst of alerts.
            if rule == "weekdays":
                while next_due.weekday() >= 5:
                    next_due += timedelta(days=1)
            self.database.execute(
                """UPDATE reminders SET due_at = ?, last_fired_at = ?, dismissed_at = NULL
                   WHERE id = ?""",
                (self._utc_text(next_due), self._utc_text(fired), int(reminder_id)),
            )
        return reminder

    def snooze_reminder(self, reminder_id: int, minutes: int = 10) -> None:
        if minutes <= 0:
            raise ValueError("Snooze duration must be positive.")
        due = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.database.execute(
            """UPDATE reminders SET due_at = ?, is_enabled = 1, dismissed_at = NULL
               WHERE id = ?""",
            (self._utc_text(due), int(reminder_id)),
        )
