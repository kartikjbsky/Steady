from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any

from steady.database import Database


class PlannerRepository:
    """Persistence operations for the dated task and daily-habit views."""

    TASK_STATUSES = {"todo", "in_progress", "done", "missed", "cancelled"}
    HABIT_STATUSES = {"pending", "done", "missed", "not_applicable"}

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _date_text(day: date | str) -> str:
        value = day.isoformat() if isinstance(day, date) else str(day)
        # Validate and normalise the value before it reaches SQLite.
        return date.fromisoformat(value).isoformat()

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def list_tasks(self, day: date | str) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            """SELECT id, title, description, scheduled_date, priority,
                      estimate_minutes, status, sort_order, miss_reason_id,
                      reflection_note, completed_at
               FROM tasks
               WHERE scheduled_date = ?
               ORDER BY sort_order, id""",
            (self._date_text(day),),
        )
        return [dict(row) for row in rows]

    def copy_tasks(self, source_day: date | str, target_day: date | str) -> int:
        """Copy every task occurrence from one date to another as fresh tasks.

        Task content and planning metadata are retained, while workflow state and
        reflection data are reset. Existing tasks on the target date are untouched.
        """
        source_value = self._date_text(source_day)
        target_value = self._date_text(target_day)
        if source_value == target_value:
            raise ValueError("Choose a different source date from the selected date.")
        if date.fromisoformat(target_value) < date.today():
            raise ValueError("Past dates are read-only. Tasks can only be copied to today or a future date.")

        with self.database.connect() as connection:
            source_rows = connection.execute(
                """SELECT title, description, priority, estimate_minutes, sort_order
                   FROM tasks
                   WHERE scheduled_date = ?
                   ORDER BY sort_order, id""",
                (source_value,),
            ).fetchall()
            if not source_rows:
                return 0

            connection.executemany(
                """INSERT INTO tasks
                       (title, description, scheduled_date, priority, estimate_minutes,
                        status, sort_order, miss_reason_id, reflection_note, completed_at)
                   VALUES (?, ?, ?, ?, ?, 'todo', ?, NULL, '', NULL)""",
                [
                    (
                        row["title"], row["description"], target_value,
                        row["priority"], row["estimate_minutes"], row["sort_order"],
                    )
                    for row in source_rows
                ],
            )
        return len(source_rows)

    def add_task(
        self,
        *,
        title: str,
        day: date | str,
        description: str = "",
        priority: int = 2,
        estimate_minutes: int | None = None,
    ) -> int:
        day_value = self._date_text(day)
        if date.fromisoformat(day_value) < date.today():
            raise ValueError("Past dates are read-only. Schedule new tasks for today or a future date.")
        title = title.strip()
        if not title:
            raise ValueError("A task title is required.")
        if priority not in (1, 2, 3):
            raise ValueError("Priority must be 1 (low), 2 (normal), or 3 (high).")
        if estimate_minutes is not None and estimate_minutes <= 0:
            raise ValueError("Estimated minutes must be positive or None.")

        return self.database.execute(
            """INSERT INTO tasks
               (title, description, scheduled_date, priority, estimate_minutes)
               VALUES (?, ?, ?, ?, ?)""",
            (title, description.strip(), day_value, priority, estimate_minutes),
        )

    def update_task(self, task_id: int, **changes: Any) -> None:
        allowed = {"title", "description", "priority", "estimate_minutes", "status", "miss_reason_id", "reflection_note", "scheduled_date"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported task fields: {', '.join(sorted(unknown))}")
        if not changes:
            return
        existing_rows = self.database.fetch_all(
            "SELECT scheduled_date FROM tasks WHERE id = ?", (int(task_id),)
        )
        if not existing_rows:
            raise ValueError("This task no longer exists.")
        original_day = date.fromisoformat(existing_rows[0]["scheduled_date"])
        if original_day < date.today():
            raise ValueError("Past task records are read-only. You can still review them.")
        if "scheduled_date" in changes:
            target_day = date.fromisoformat(self._date_text(changes["scheduled_date"]))
            if target_day < date.today():
                raise ValueError("Tasks can only be scheduled for today or a future date.")
            changes["scheduled_date"] = target_day.isoformat()
        if "title" in changes:
            changes["title"] = str(changes["title"]).strip()
            if not changes["title"]:
                raise ValueError("A task title is required.")
        if "priority" in changes and changes["priority"] not in (1, 2, 3):
            raise ValueError("Priority must be 1, 2, or 3.")
        if "status" in changes and changes["status"] not in self.TASK_STATUSES:
            raise ValueError("Invalid task status.")
        if "estimate_minutes" in changes and changes["estimate_minutes"] is not None and changes["estimate_minutes"] <= 0:
            raise ValueError("Estimated minutes must be positive or None.")

        now = self._now_utc()
        if changes.get("status") == "done":
            changes["completed_at"] = now
        elif changes.get("status") in self.TASK_STATUSES:
            changes["completed_at"] = None
        changes["updated_at"] = now

        assignments = ", ".join(f"{column} = ?" for column in changes)
        values = tuple(changes.values()) + (int(task_id),)
        self.database.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)

    def delete_task(self, task_id: int) -> None:
        rows = self.database.fetch_all(
            "SELECT scheduled_date FROM tasks WHERE id = ?", (int(task_id),)
        )
        if not rows:
            return
        if date.fromisoformat(rows[0]["scheduled_date"]) < date.today():
            raise ValueError("Past task records are read-only and cannot be removed.")
        self.database.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))

    def list_upcoming_tasks(self, *, limit: int = 8, from_date: date | None = None) -> list[dict[str, Any]]:
        start = (from_date or date.today()).isoformat()
        rows = self.database.fetch_all(
            """SELECT id, title, scheduled_date, priority, estimate_minutes, status
               FROM tasks WHERE scheduled_date >= ? AND status NOT IN ('done', 'cancelled')
               ORDER BY scheduled_date, CASE priority WHEN 3 THEN 0 WHEN 2 THEN 1 ELSE 2 END, sort_order, id
               LIMIT ?""",
            (start, max(1, min(int(limit), 50))),
        )
        return [dict(row) for row in rows]

    def list_habits(self, day: date | str) -> list[dict[str, Any]]:
        parsed_day = date.fromisoformat(self._date_text(day))
        weekday_index = parsed_day.weekday()  # Monday = 0
        rows = self.database.fetch_all(
            """SELECT h.id, h.name, h.description, h.weekday_mask,
                      COALESCE(e.status, 'pending') AS status,
                      e.id AS entry_id, e.miss_reason_id, e.reflection_note
               FROM habits AS h
               LEFT JOIN habit_entries AS e
                 ON e.habit_id = h.id AND e.entry_date = ?
               WHERE h.is_active = 1
                 AND h.archived_at IS NULL
                 AND h.start_date <= ?
               ORDER BY h.sort_order, h.id""",
            (parsed_day.isoformat(), parsed_day.isoformat()),
        )
        return [dict(row) for row in rows if row["weekday_mask"][weekday_index] == "1"]

    def set_habit_status(
        self,
        habit_id: int,
        day: date | str,
        status: str,
        *,
        miss_reason_id: int | None = None,
        reflection_note: str = "",
    ) -> None:
        if status not in self.HABIT_STATUSES:
            raise ValueError("Invalid habit status.")
        if status != "missed":
            miss_reason_id = None
            reflection_note = ""
        now = self._now_utc()
        completed_at = now if status == "done" else None
        self.database.execute(
            """INSERT INTO habit_entries
                   (habit_id, entry_date, status, miss_reason_id, reflection_note, completed_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(habit_id, entry_date) DO UPDATE SET
                   status = excluded.status,
                   miss_reason_id = excluded.miss_reason_id,
                   reflection_note = excluded.reflection_note,
                   completed_at = excluded.completed_at,
                   updated_at = excluded.updated_at""",
            (
                int(habit_id), self._date_text(day), status, miss_reason_id,
                str(reflection_note).strip(), completed_at, now,
            ),
        )

    def list_miss_reasons(self) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            "SELECT id, code, label FROM miss_reasons WHERE is_active = 1 ORDER BY sort_order, id"
        )
        return [dict(row) for row in rows]

    def get_month_summary(self, year: int, month: int) -> dict[str, dict[str, int]]:
        """Return task and habit totals keyed by ISO date for one calendar month.

        Cancelled tasks are excluded from planned-task totals. Habit totals include
        every active habit scheduled for that weekday, even when its entry is still
        pending and therefore has not yet been written to ``habit_entries``.
        """
        if not 1 <= int(month) <= 12:
            raise ValueError("Month must be between 1 and 12.")
        first_day = date(int(year), int(month), 1)
        last_day = date(int(year), int(month), monthrange(int(year), int(month))[1])
        first_text = first_day.isoformat()
        last_text = last_day.isoformat()

        summary: dict[str, dict[str, int]] = {}
        for day_number in range(1, last_day.day + 1):
            day_text = date(int(year), int(month), day_number).isoformat()
            summary[day_text] = {
                "task_total": 0,
                "task_done": 0,
                "habit_total": 0,
                "habit_done": 0,
            }

        task_rows = self.database.fetch_all(
            """SELECT scheduled_date AS day,
                      COUNT(*) AS task_total,
                      SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS task_done
               FROM tasks
               WHERE scheduled_date BETWEEN ? AND ? AND status != 'cancelled'
               GROUP BY scheduled_date""",
            (first_text, last_text),
        )
        for row in task_rows:
            summary[row["day"]]["task_total"] = int(row["task_total"] or 0)
            summary[row["day"]]["task_done"] = int(row["task_done"] or 0)

        active_habits = self.database.fetch_all(
            """SELECT id, weekday_mask, start_date,
                      CASE WHEN archived_at IS NULL THEN NULL ELSE substr(archived_at, 1, 10) END AS archived_date
               FROM habits
               WHERE start_date <= ? AND (is_active = 1 OR archived_at IS NOT NULL)""",
            (last_text,),
        )
        entry_rows = self.database.fetch_all(
            """SELECT e.habit_id, e.entry_date, e.status
               FROM habit_entries AS e
               JOIN habits AS h ON h.id = e.habit_id
               WHERE e.entry_date BETWEEN ? AND ?
                 AND h.start_date <= e.entry_date
                 AND (h.is_active = 1 OR h.archived_at IS NOT NULL)
                 AND (h.archived_at IS NULL OR substr(h.archived_at, 1, 10) >= e.entry_date)""",
            (first_text, last_text),
        )
        entries = {
            (int(row["habit_id"]), row["entry_date"]): row["status"]
            for row in entry_rows
        }

        for day_text, counts in summary.items():
            weekday = date.fromisoformat(day_text).weekday()  # Monday = 0
            for habit in active_habits:
                archived_date = habit["archived_date"]
                if (
                    habit["start_date"] <= day_text
                    and (archived_date is None or archived_date >= day_text)
                    and habit["weekday_mask"][weekday] == "1"
                ):
                    counts["habit_total"] += 1
                    if entries.get((int(habit["id"]), day_text)) == "done":
                        counts["habit_done"] += 1

        return summary
