from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.timetable_repository import TimetableRepository


def make_repo(tmp_path: Path) -> TimetableRepository:
    database = Database(tmp_path / "steady.sqlite3")
    database.initialize()
    return TimetableRepository(database)


def test_weekly_timetable_starts_empty_and_saves_one_entry_per_day_and_time(tmp_path: Path) -> None:
    timetable = make_repo(tmp_path)
    assert timetable.list_entries() == []

    timetable.save_slot(weekday=0, start_time="07:00", title="Quantum mechanics", notes="Lecture")
    timetable.save_slot(weekday=1, start_time="07:00", title="Research work")
    rows = timetable.list_entries()

    assert len(rows) == 2
    assert timetable.get_slot(0, "07:00")["title"] == "Quantum mechanics"
    assert timetable.get_slot(0, "07:00")["notes"] == "Lecture"
    assert timetable.get_slot(1, "07:00")["title"] == "Research work"


def test_saving_existing_weekly_cell_updates_instead_of_duplicating(tmp_path: Path) -> None:
    timetable = make_repo(tmp_path)
    timetable.save_slot(weekday=2, start_time="09:00", title="Read paper")
    timetable.save_slot(weekday=2, start_time="09:00", title="Write notes", notes="Chapter 2")

    rows = timetable.list_entries()
    assert len(rows) == 1
    assert rows[0]["title"] == "Write notes"
    assert rows[0]["notes"] == "Chapter 2"


def test_clear_slot_removes_only_selected_weekday_and_time(tmp_path: Path) -> None:
    timetable = make_repo(tmp_path)
    timetable.save_slot(weekday=0, start_time="10:00", title="Monday activity")
    timetable.save_slot(weekday=1, start_time="10:00", title="Tuesday activity")

    timetable.clear_slot(0, "10:00")

    assert timetable.get_slot(0, "10:00") is None
    assert timetable.get_slot(1, "10:00")["title"] == "Tuesday activity"


def test_invalid_timetable_values_are_rejected(tmp_path: Path) -> None:
    timetable = make_repo(tmp_path)
    with pytest.raises(ValueError, match="Weekday"):
        timetable.save_slot(weekday=7, start_time="07:00", title="Invalid day")
    with pytest.raises(ValueError, match="task or activity"):
        timetable.save_slot(weekday=0, start_time="07:00", title="  ")
    with pytest.raises(ValueError):
        timetable.save_slot(weekday=0, start_time="25:00", title="Invalid time")
    with pytest.raises(ValueError, match="120 characters"):
        timetable.save_slot(weekday=0, start_time="07:00", title="x" * 121)


def test_weekday_and_time_are_normalised(tmp_path: Path) -> None:
    from datetime import time

    timetable = make_repo(tmp_path)
    timetable.save_slot(weekday=6, start_time=time(19, 0), title="Wind down")
    assert timetable.get_slot(6, "19:00")["start_time"] == "19:00"
