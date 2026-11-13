from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from steady.database import Database


class ReflectionRepository:
    """Store daily check-ins and retrieve optional missed-activity reflections."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _date_text(day: date | str) -> str:
        value = day.isoformat() if isinstance(day, date) else str(day)
        return date.fromisoformat(value).isoformat()

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def get_daily_reflection(self, day: date | str) -> dict[str, Any] | None:
        rows = self.database.fetch_all(
            """SELECT id, reflection_date, energy_level, mood_label, note,
                      created_at, updated_at
               FROM daily_reflections WHERE reflection_date = ?""",
            (self._date_text(day),),
        )
        return dict(rows[0]) if rows else None

    def save_daily_reflection(
        self,
        day: date | str,
        *,
        energy_level: int | None = None,
        mood_label: str = "",
        note: str = "",
    ) -> None:
        if energy_level is not None and int(energy_level) not in range(1, 6):
            raise ValueError("Energy level must be between 1 and 5, or None.")
        mood_label = str(mood_label).strip()
        note = str(note).strip()
        if len(mood_label) > 40:
            raise ValueError("Mood label must be 40 characters or fewer.")
        if len(note) > 5000:
            raise ValueError("Reflection note must be 5000 characters or fewer.")

        now = self._now_utc()
        self.database.execute(
            """INSERT INTO daily_reflections
                   (reflection_date, energy_level, mood_label, note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(reflection_date) DO UPDATE SET
                   energy_level = excluded.energy_level,
                   mood_label = excluded.mood_label,
                   note = excluded.note,
                   updated_at = excluded.updated_at""",
            (self._date_text(day), energy_level, mood_label, note, now, now),
        )

    def delete_daily_reflection(self, day: date | str) -> bool:
        day_text = self._date_text(day)
        existed = bool(
            self.database.fetch_all(
                "SELECT id FROM daily_reflections WHERE reflection_date = ?",
                (day_text,),
            )
        )
        if existed:
            self.database.execute(
                "DELETE FROM daily_reflections WHERE reflection_date = ?", (day_text,)
            )
        return existed

    def list_missed_activities(
        self, days: int = 30, *, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        if not 1 <= int(days) <= 366:
            raise ValueError("The reflection window must be between 1 and 366 days.")
        last_day = end_date or date.today()
        first_day = last_day - timedelta(days=int(days) - 1)
        start_text, end_text = first_day.isoformat(), last_day.isoformat()
        rows = self.database.fetch_all(
            """SELECT * FROM (
                   SELECT 'Task' AS activity_type,
                          t.id AS activity_id,
                          t.scheduled_date AS activity_date,
                          t.title AS activity,
                          t.miss_reason_id AS miss_reason_id,
                          COALESCE(mr.label, 'Not recorded') AS reason,
                          t.reflection_note AS note
                   FROM tasks AS t
                   LEFT JOIN miss_reasons AS mr ON mr.id = t.miss_reason_id
                   WHERE t.status = 'missed'
                     AND t.scheduled_date BETWEEN ? AND ?
                   UNION ALL
                   SELECT 'Habit' AS activity_type,
                          e.id AS activity_id,
                          e.entry_date AS activity_date,
                          h.name AS activity,
                          e.miss_reason_id AS miss_reason_id,
                          COALESCE(mr.label, 'Not recorded') AS reason,
                          e.reflection_note AS note
                   FROM habit_entries AS e
                   JOIN habits AS h ON h.id = e.habit_id
                   LEFT JOIN miss_reasons AS mr ON mr.id = e.miss_reason_id
                   WHERE e.status = 'missed'
                     AND e.entry_date BETWEEN ? AND ?
               )
               ORDER BY activity_date DESC, activity_type, activity COLLATE NOCASE""",
            (start_text, end_text, start_text, end_text),
        )
        return [dict(row) for row in rows]

    def list_miss_reasons(self) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            "SELECT id, code, label FROM miss_reasons WHERE is_active = 1 ORDER BY sort_order, id"
        )
        return [dict(row) for row in rows]

    def update_missed_activity(
        self,
        activity_type: str,
        activity_id: int,
        *,
        miss_reason_id: int | None,
        note: str = "",
    ) -> bool:
        if activity_type not in {"Task", "Habit"}:
            raise ValueError("Activity type must be Task or Habit.")
        note = str(note).strip()
        if len(note) > 2000:
            raise ValueError("Missed-activity note must be 2000 characters or fewer.")
        table = "tasks" if activity_type == "Task" else "habit_entries"
        id_column = "id"
        existing = self.database.fetch_all(
            f"SELECT {id_column} FROM {table} WHERE {id_column} = ? AND status = 'missed'",
            (int(activity_id),),
        )
        if not existing:
            return False
        now = self._now_utc()
        self.database.execute(
            f"""UPDATE {table}
                SET miss_reason_id = ?, reflection_note = ?, updated_at = ?
                WHERE {id_column} = ? AND status = 'missed'""",
            (miss_reason_id, note, now, int(activity_id)),
        )
        return True
