from datetime import date, datetime
from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.habit_repository import HabitRepository
from steady.repositories.planner_repository import PlannerRepository


def make_repositories(tmp_path: Path):
    database = Database(tmp_path / "steady-habits.sqlite3")
    database.initialize()
    return database, HabitRepository(database), PlannerRepository(database)


def test_create_custom_habit_and_schedule_only_selected_days(tmp_path: Path) -> None:
    _, habits, planner = make_repositories(tmp_path)
    habit_id = habits.create_habit(
        name="DSA practice",
        category="study",
        weekday_mask="1111100",
        start_date=date(2026, 11, 10),
    )

    assert any(h["id"] == habit_id for h in planner.list_habits(date(2026, 11, 10)))
    assert any(h["id"] == habit_id for h in planner.list_habits(date(2026, 11, 13)))
    assert all(h["id"] != habit_id for h in planner.list_habits(date(2026, 11, 14)))
    assert all(h["id"] != habit_id for h in planner.list_habits(date(2026, 11, 9)))


def test_edit_pause_resume_and_archive_keep_habit_history(tmp_path: Path) -> None:
    database, habits, planner = make_repositories(tmp_path)
    day = date(2026, 11, 13)
    habit_id = habits.create_habit(name="Read research paper", category="research", start_date=day)
    planner.set_habit_status(habit_id, day, "done")

    habits.update_habit(habit_id, name="Read one research paper", weekday_mask="1111100")
    assert habits.get_habit(habit_id)["name"] == "Read one research paper"

    habits.set_active(habit_id, False)
    assert habits.list_habits("paused")[0]["id"] == habit_id
    assert all(item["id"] != habit_id for item in planner.list_habits(day))

    habits.set_active(habit_id, True)
    assert any(item["id"] == habit_id for item in planner.list_habits(day))

    habits.archive(habit_id)
    assert habits.list_habits("archived")[0]["id"] == habit_id
    assert all(item["id"] != habit_id for item in planner.list_habits(day))
    saved_entry = database.fetch_all(
        "SELECT status FROM habit_entries WHERE habit_id = ? AND entry_date = ?",
        (habit_id, day.isoformat()),
    )
    assert saved_entry[0]["status"] == "done"

    habits.restore(habit_id)
    assert any(item["id"] == habit_id for item in planner.list_habits(day))


def test_habit_reminder_fires_once_on_scheduled_local_day(tmp_path: Path) -> None:
    _, habits, _ = make_repositories(tmp_path)
    habit_id = habits.create_habit(
        name="Take a short walk",
        weekday_mask="1111111",
        start_date=date(2026, 11, 13),
        reminder_enabled=True,
        reminder_time="09:30",
    )
    due_time = datetime(2026, 11, 13, 9, 30)

    due = habits.due_habit_reminders(due_time)
    assert [item["id"] for item in due] == [habit_id]
    assert habits.due_habit_reminders(due_time) == []


def test_habit_reminder_does_not_fire_on_unscheduled_weekday(tmp_path: Path) -> None:
    _, habits, _ = make_repositories(tmp_path)
    habits.create_habit(
        name="Weekday reading",
        weekday_mask="1111100",
        reminder_enabled=True,
        reminder_time="08:00",
    )
    saturday = datetime(2026, 11, 14, 8, 0)
    assert habits.due_habit_reminders(saturday) == []


def test_habit_validation_rejects_empty_schedule_and_missing_reminder_time(tmp_path: Path) -> None:
    _, habits, _ = make_repositories(tmp_path)
    with pytest.raises(ValueError, match="at least one weekday"):
        habits.create_habit(name="No days", weekday_mask="0000000")
    with pytest.raises(ValueError, match="Choose a reminder time"):
        habits.create_habit(name="No time", reminder_enabled=True)


def test_habit_reminder_catches_up_after_scheduled_time(tmp_path: Path) -> None:
    _, habits, _ = make_repositories(tmp_path)
    habit_id = habits.create_habit(
        name="Morning reading",
        weekday_mask="1111111",
        start_date=date(2026, 11, 13),
        reminder_enabled=True,
        reminder_time="08:00",
    )

    due = habits.due_habit_reminders(datetime(2026, 11, 13, 10, 15))
    assert [item["id"] for item in due] == [habit_id]


def test_archived_habit_reminder_is_not_delivered(tmp_path: Path) -> None:
    _, habits, _ = make_repositories(tmp_path)
    habit_id = habits.create_habit(
        name="Archived reminder",
        weekday_mask="1111111",
        start_date=date(2026, 11, 13),
        reminder_enabled=True,
        reminder_time="08:00",
    )
    habits.archive(habit_id)

    assert habits.due_habit_reminders(datetime(2026, 11, 13, 10, 15)) == []
