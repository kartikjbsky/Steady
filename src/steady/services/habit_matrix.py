from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any


def compute_month_progress(
    habits: list[dict[str, Any]],
    entries: dict[tuple[int, str], str],
    year: int,
    month: int,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Calculate monthly habit completion over scheduled days that have occurred.

    Active habits count through today (or the end of a past month). Archived
    habits count only through their archive date. Paused habits are excluded
    because the schema does not record the exact date they were paused.
    Future scheduled days are never included in the denominator.
    """
    if not 1 <= int(month) <= 12:
        raise ValueError("Month must be between 1 and 12.")
    today = today or date.today()
    first = date(int(year), int(month), 1)
    last = date(int(year), int(month), monthrange(int(year), int(month))[1])
    elapsed_last = min(last, today)

    rows: dict[int, dict[str, int]] = {}
    total_scheduled = 0
    total_done = 0

    for habit in habits:
        habit_id = int(habit["id"])
        start = date.fromisoformat(str(habit["start_date"]))
        archived_at = habit.get("archived_at")
        archived_day = date.fromisoformat(str(archived_at)[:10]) if archived_at else None
        is_active = bool(habit.get("is_active"))
        counts_for_progress = is_active or archived_day is not None

        scheduled = 0
        done = 0
        if counts_for_progress and elapsed_last >= first:
            lower = max(first, start)
            upper = min(elapsed_last, archived_day) if archived_day else elapsed_last
            if upper >= lower:
                mask = str(habit["weekday_mask"])
                day = lower
                while day <= upper:
                    if mask[day.weekday()] == "1":
                        scheduled += 1
                        if entries.get((habit_id, day.isoformat())) == "done":
                            done += 1
                    day += timedelta(days=1)

        rows[habit_id] = {
            "scheduled": scheduled,
            "done": done,
            "percent": round(done / scheduled * 100) if scheduled else 0,
        }
        total_scheduled += scheduled
        total_done += done

    return {
        "habits": rows,
        "scheduled": total_scheduled,
        "done": total_done,
        "percent": round(total_done / total_scheduled * 100) if total_scheduled else 0,
    }
