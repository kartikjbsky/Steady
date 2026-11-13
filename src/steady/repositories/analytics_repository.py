from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from steady.database import Database


class AnalyticsRepository:
    """Read-only, date-aware summaries for the Progress page.

    Calendar tasks and habits use the user's local calendar date. Focus sessions
    are stored in UTC, so their boundaries are converted from local midnight to
    UTC before querying and then grouped back into local dates.
    """

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _utc_iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.astimezone()
        return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def get_period_summary(
        self, days: int = 7, *, end_date: date | None = None
    ) -> dict[str, Any]:
        """Return daily task, habit and focus values for a rolling local-date window."""
        if not 1 <= int(days) <= 366:
            raise ValueError("The reporting period must be between 1 and 366 days.")

        last_day = end_date or date.today()
        first_day = last_day - timedelta(days=int(days) - 1)
        first_text, last_text = first_day.isoformat(), last_day.isoformat()

        daily: dict[str, dict[str, int | str]] = {
            (first_day + timedelta(days=index)).isoformat(): {
                "date": (first_day + timedelta(days=index)).isoformat(),
                "task_total": 0,
                "task_done": 0,
                "habit_total": 0,
                "habit_done": 0,
                "focus_seconds": 0,
                "focus_sessions": 0,
            }
            for index in range(int(days))
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
            daily[row["day"]]["task_total"] = int(row["task_total"] or 0)
            daily[row["day"]]["task_done"] = int(row["task_done"] or 0)

        habits = self.database.fetch_all(
            """SELECT id, weekday_mask, start_date,
                      CASE WHEN archived_at IS NULL THEN NULL
                           ELSE substr(archived_at, 1, 10) END AS archived_date
               FROM habits
               WHERE start_date <= ? AND (is_active = 1 OR archived_at IS NOT NULL)""",
            (last_text,),
        )
        habit_rows = self.database.fetch_all(
            """SELECT e.habit_id, e.entry_date, e.status
               FROM habit_entries AS e
               JOIN habits AS h ON h.id = e.habit_id
               WHERE e.entry_date BETWEEN ? AND ?
                 AND h.start_date <= e.entry_date
                 AND (h.is_active = 1 OR h.archived_at IS NOT NULL)
                 AND (h.archived_at IS NULL OR substr(h.archived_at, 1, 10) >= e.entry_date)""",
            (first_text, last_text),
        )
        habit_entries = {
            (int(row["habit_id"]), row["entry_date"]): row["status"]
            for row in habit_rows
        }
        for day_text, values in daily.items():
            weekday = date.fromisoformat(day_text).weekday()
            for habit in habits:
                archived_date = habit["archived_date"]
                if (
                    habit["start_date"] <= day_text
                    and (archived_date is None or archived_date >= day_text)
                    and habit["weekday_mask"][weekday] == "1"
                ):
                    values["habit_total"] = int(values["habit_total"]) + 1
                    if habit_entries.get((int(habit["id"]), day_text)) == "done":
                        values["habit_done"] = int(values["habit_done"]) + 1

        # Convert local day boundaries to UTC. This also handles daylight-saving
        # transitions correctly on platforms whose local zone observes them.
        local_start = datetime.combine(first_day, time.min).astimezone()
        local_end = datetime.combine(last_day + timedelta(days=1), time.min).astimezone()
        start_utc, end_utc = self._utc_iso(local_start), self._utc_iso(local_end)
        focus_rows = self.database.fetch_all(
            """SELECT started_at, actual_seconds
               FROM focus_sessions
               WHERE session_type = 'focus'
                 AND actual_seconds IS NOT NULL
                 AND started_at >= ? AND started_at < ?""",
            (start_utc, end_utc),
        )
        for row in focus_rows:
            local_date = self._parse_utc(row["started_at"]).astimezone().date().isoformat()
            if local_date in daily:
                daily[local_date]["focus_seconds"] = (
                    int(daily[local_date]["focus_seconds"]) + int(row["actual_seconds"] or 0)
                )
                daily[local_date]["focus_sessions"] = int(daily[local_date]["focus_sessions"]) + 1

        rows = list(daily.values())
        task_total = sum(int(row["task_total"]) for row in rows)
        task_done = sum(int(row["task_done"]) for row in rows)
        habit_total = sum(int(row["habit_total"]) for row in rows)
        habit_done = sum(int(row["habit_done"]) for row in rows)
        focus_seconds = sum(int(row["focus_seconds"]) for row in rows)
        focus_sessions = sum(int(row["focus_sessions"]) for row in rows)

        return {
            "start_date": first_text,
            "end_date": last_text,
            "days": rows,
            "task_total": task_total,
            "task_done": task_done,
            "habit_total": habit_total,
            "habit_done": habit_done,
            "focus_seconds": focus_seconds,
            "focus_sessions": focus_sessions,
            "task_percent": round(task_done / task_total * 100) if task_total else 0,
            "habit_percent": round(habit_done / habit_total * 100) if habit_total else 0,
        }

    def get_missed_reason_breakdown(
        self, days: int = 30, *, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Count explicitly recorded missed-task and missed-habit reasons."""
        if not 1 <= int(days) <= 366:
            raise ValueError("The reporting period must be between 1 and 366 days.")
        last_day = end_date or date.today()
        first_day = last_day - timedelta(days=int(days) - 1)
        rows = self.database.fetch_all(
            """SELECT mr.label, COUNT(*) AS total
               FROM (
                   SELECT miss_reason_id
                   FROM tasks
                   WHERE scheduled_date BETWEEN ? AND ?
                     AND status = 'missed' AND miss_reason_id IS NOT NULL
                   UNION ALL
                   SELECT miss_reason_id
                   FROM habit_entries
                   WHERE entry_date BETWEEN ? AND ?
                     AND status = 'missed' AND miss_reason_id IS NOT NULL
               ) AS missed
               JOIN miss_reasons AS mr ON mr.id = missed.miss_reason_id
               GROUP BY mr.id, mr.label
               ORDER BY total DESC, mr.sort_order ASC""",
            (
                first_day.isoformat(), last_day.isoformat(),
                first_day.isoformat(), last_day.isoformat(),
            ),
        )
        return [dict(row) for row in rows]
