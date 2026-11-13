from datetime import date
from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.reflection_repository import ReflectionRepository


def make_repository(tmp_path: Path) -> tuple[Database, ReflectionRepository]:
    database = Database(tmp_path / "steady-reflection-test.sqlite3")
    database.initialize()
    return database, ReflectionRepository(database)


def test_daily_reflection_insert_update_and_delete(tmp_path: Path) -> None:
    _database, repository = make_repository(tmp_path)
    day = date(2026, 11, 12)

    repository.save_daily_reflection(
        day, energy_level=2, mood_label="Restless", note="Had trouble getting started."
    )
    saved = repository.get_daily_reflection(day)
    assert saved is not None
    assert saved["energy_level"] == 2
    assert saved["mood_label"] == "Restless"
    assert saved["note"] == "Had trouble getting started."

    repository.save_daily_reflection(day, energy_level=4, mood_label="Focused", note="A better afternoon.")
    updated = repository.get_daily_reflection(day)
    assert updated is not None
    assert updated["energy_level"] == 4
    assert updated["mood_label"] == "Focused"
    assert updated["note"] == "A better afternoon."

    assert repository.delete_daily_reflection(day) is True
    assert repository.get_daily_reflection(day) is None
    assert repository.delete_daily_reflection(day) is False


def test_daily_reflection_validation(tmp_path: Path) -> None:
    _database, repository = make_repository(tmp_path)
    with pytest.raises(ValueError):
        repository.save_daily_reflection(date(2026, 11, 12), energy_level=6)
    with pytest.raises(ValueError):
        repository.save_daily_reflection(date(2026, 11, 12), note="x" * 5001)


def test_missed_activities_combines_tasks_and_habits_and_can_update_reason(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    day = date(2026, 11, 12)
    reason = database.fetch_all(
        "SELECT id FROM miss_reasons WHERE code = 'low_energy'"
    )[0]
    reason_id = int(reason["id"])

    task_id = database.execute(
        """INSERT INTO tasks(title, scheduled_date, status, miss_reason_id, reflection_note)
           VALUES (?, ?, 'missed', ?, ?)""",
        ("Read a paper", day.isoformat(), reason_id, "Low energy after lunch."),
    )
    habit = database.fetch_all("SELECT id FROM habits ORDER BY sort_order LIMIT 1")[0]
    habit_entry_id = database.execute(
        """INSERT INTO habit_entries(habit_id, entry_date, status, miss_reason_id, reflection_note)
           VALUES (?, ?, 'missed', ?, ?)""",
        (int(habit["id"]), day.isoformat(), None, "Could not make time."),
    )

    rows = repository.list_missed_activities(1, end_date=day)
    assert len(rows) == 2
    assert {row["activity_type"] for row in rows} == {"Task", "Habit"}

    assert repository.update_missed_activity(
        "Task", task_id, miss_reason_id=None, note="Reason intentionally left blank."
    ) is True
    assert repository.update_missed_activity(
        "Habit", habit_entry_id, miss_reason_id=reason_id, note="Energy was low."
    ) is True

    updated = repository.list_missed_activities(1, end_date=day)
    task = next(row for row in updated if row["activity_type"] == "Task")
    habit_record = next(row for row in updated if row["activity_type"] == "Habit")
    assert task["reason"] == "Not recorded"
    assert task["note"] == "Reason intentionally left blank."
    assert habit_record["reason"] == "Low energy"
    assert habit_record["note"] == "Energy was low."


def test_habit_missed_status_can_store_reason_and_note(tmp_path: Path) -> None:
    database, _repository = make_repository(tmp_path)
    from steady.repositories.planner_repository import PlannerRepository

    planner = PlannerRepository(database)
    habit_id = int(database.fetch_all("SELECT id FROM habits ORDER BY sort_order LIMIT 1")[0]["id"])
    reason_id = int(database.fetch_all("SELECT id FROM miss_reasons WHERE code = 'got_distracted'")[0]["id"])
    day = date.today()

    planner.set_habit_status(
        habit_id, day, "missed", miss_reason_id=reason_id, reflection_note="Got pulled into email."
    )
    row = next(item for item in planner.list_habits(day) if int(item["id"]) == habit_id)
    assert row["status"] == "missed"
    assert row["miss_reason_id"] == reason_id
    assert row["reflection_note"] == "Got pulled into email."

    planner.set_habit_status(habit_id, day, "done")
    row = next(item for item in planner.list_habits(day) if int(item["id"]) == habit_id)
    assert row["status"] == "done"
    assert row["miss_reason_id"] is None
    assert row["reflection_note"] == ""
