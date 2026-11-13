from datetime import date
from pathlib import Path

from steady.database import Database
from steady.repositories.habit_repository import HabitRepository
from steady.repositories.planner_repository import PlannerRepository


def test_list_month_entries_returns_statuses_for_selected_month(tmp_path: Path):
    db = Database(tmp_path / "habit-month.sqlite3")
    db.initialize()
    habits = HabitRepository(db)
    planner = PlannerRepository(db)
    habit_id = habits.create_habit(
        name="Month matrix test habit", weekday_mask="1111111", start_date=date(2026, 12, 1)
    )
    planner.set_habit_status(habit_id, date(2026, 12, 1), "done")
    planner.set_habit_status(habit_id, date(2026, 12, 2), "missed")

    entries = habits.list_month_entries(2026, 12)

    assert entries[(habit_id, "2026-12-01")] == "done"
    assert entries[(habit_id, "2026-12-02")] == "missed"
    assert not any(day.startswith("2027-01") for _, day in entries)
