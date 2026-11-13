from datetime import date
from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.habit_repository import HabitRepository
from steady.repositories.planner_repository import PlannerRepository


def test_only_archived_habits_can_be_permanently_deleted(tmp_path: Path):
    database = Database(tmp_path / "habits.sqlite3")
    database.initialize()
    habits = HabitRepository(database)
    planner = PlannerRepository(database)

    habit_id = habits.create_habit(name="Temporary habit", weekday_mask="1111111")
    planner.set_habit_status(habit_id, date.today(), "done")

    with pytest.raises(ValueError, match="Only archived habits"):
        habits.delete_archived(habit_id)

    habits.archive(habit_id)
    deleted_name = habits.delete_archived(habit_id)

    assert deleted_name == "Temporary habit"
    assert habits.get_habit(habit_id) is None
    assert database.fetch_all(
        "SELECT id FROM habit_entries WHERE habit_id = ?", (habit_id,)
    ) == []

    # The unique name can be reused after explicit permanent deletion.
    replacement_id = habits.create_habit(name="Temporary habit")
    assert replacement_id != habit_id


def test_delete_archived_missing_habit_is_safe(tmp_path: Path):
    database = Database(tmp_path / "habits.sqlite3")
    database.initialize()
    habits = HabitRepository(database)

    with pytest.raises(ValueError, match="no longer exists"):
        habits.delete_archived(999999)


def test_deleted_builtin_habit_is_not_reseeded_on_next_startup(tmp_path: Path):
    database = Database(tmp_path / "builtins.sqlite3")
    database.initialize()
    habits = HabitRepository(database)

    builtin = next(
        item for item in habits.list_habits("active")
        if item["name"] == "Morning exercise"
    )
    habits.archive(int(builtin["id"]))
    habits.delete_archived(int(builtin["id"]))

    database.initialize()

    assert all(
        item["name"] != "Morning exercise"
        for item in habits.list_habits("all")
    )
