from datetime import date
from pathlib import Path

from steady.database import Database
from steady.repositories.planner_repository import PlannerRepository


def make_repository(tmp_path: Path) -> PlannerRepository:
    database = Database(tmp_path / "steady-test.sqlite3")
    database.initialize()
    return PlannerRepository(database)


def test_add_and_update_dated_task(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    day = date.today()

    task_id = repository.add_task(
        title="Read a quantum computing paper",
        day=day,
        description="Start with the abstract and figures",
        priority=3,
        estimate_minutes=30,
    )

    tasks = repository.list_tasks(day)
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id
    assert tasks[0]["priority"] == 3
    assert tasks[0]["estimate_minutes"] == 30
    assert tasks[0]["status"] == "todo"

    repository.update_task(task_id, status="done")
    updated = repository.list_tasks(day)[0]
    assert updated["status"] == "done"
    assert updated["completed_at"] is not None


def test_habit_entries_are_per_day(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    monday = date.today()
    tuesday = date.today() + __import__("datetime").timedelta(days=1)
    habits = repository.list_habits(monday)
    exercise = next(habit for habit in habits if habit["name"] == "Morning exercise")

    repository.set_habit_status(exercise["id"], monday, "done")

    monday_habit = next(
        habit for habit in repository.list_habits(monday)
        if habit["id"] == exercise["id"]
    )
    tuesday_habit = next(
        habit for habit in repository.list_habits(tuesday)
        if habit["id"] == exercise["id"]
    )

    assert monday_habit["status"] == "done"
    assert tuesday_habit["status"] == "pending"


def test_weekday_mask_hides_unscheduled_habit(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    repository.database.execute(
        "INSERT INTO habits(name, weekday_mask, is_active, sort_order) VALUES (?, ?, 1, 30)",
        ("Weekday review", "1111100"),
    )

    monday_habits = repository.list_habits(date(2026, 11, 9))
    saturday_habits = repository.list_habits(date(2026, 11, 14))

    assert any(habit["name"] == "Weekday review" for habit in monday_habits)
    assert not any(habit["name"] == "Weekday review" for habit in saturday_habits)


def test_month_summary_counts_tasks_and_scheduled_habits(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    day = date.today()

    done_task = repository.add_task(title="Qiskit practice", day=day)
    repository.update_task(done_task, status="done")
    repository.add_task(title="Read a paper", day=day)
    cancelled_task = repository.add_task(title="Optional task", day=day)
    repository.update_task(cancelled_task, status="cancelled")

    habits = repository.list_habits(day)
    exercise = next(habit for habit in habits if habit["name"] == "Morning exercise")
    repository.set_habit_status(exercise["id"], day, "done")

    summary = repository.get_month_summary(2026, 11)

    assert len(summary) == 30
    assert summary[day.isoformat()] == {
        "task_total": 2,
        "task_done": 1,
        "habit_total": 2,
        "habit_done": 1,
    }
    assert summary[day.isoformat()]["task_total"] == 2


def test_month_summary_respects_habit_weekday_mask(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    repository.database.execute(
        "INSERT INTO habits(name, weekday_mask, is_active, sort_order) VALUES (?, ?, 1, 30)",
        ("Weekday review", "1111100"),
    )

    summary = repository.get_month_summary(2026, 11)

    # 12 Nov 2026 is Thursday; 14 Nov 2026 is Saturday.
    assert summary["2026-11-12"]["habit_total"] == 3
    assert summary["2026-11-14"]["habit_total"] == 2


def test_month_summary_rejects_invalid_month(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    try:
        repository.get_month_summary(2026, 13)
    except ValueError as exc:
        assert "Month" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid month")


def test_calendar_keeps_archived_habit_history_before_archive_date(tmp_path: Path) -> None:
    database = Database(tmp_path / "steady-archived-calendar.sqlite3")
    database.initialize()
    repository = PlannerRepository(database)
    habit_id = database.execute(
        "INSERT INTO habits(name, weekday_mask, category, start_date) VALUES (?, ?, ?, ?)",
        ("Archived reading habit", "1111111", "research", "2026-11-01"),
    )
    database.execute(
        "INSERT INTO habit_entries(habit_id, entry_date, status) VALUES (?, ?, 'done')",
        (habit_id, "2026-11-10"),
    )
    database.execute(
        "UPDATE habits SET is_active = 0, archived_at = ? WHERE id = ?",
        ("2026-11-11T18:00:00+05:30", habit_id),
    )

    summary = repository.get_month_summary(2026, 11)
    assert summary["2026-11-10"]["habit_total"] == 3
    assert summary["2026-11-10"]["habit_done"] == 1
    assert summary["2026-11-11"]["habit_total"] == 3
    assert summary["2026-11-12"]["habit_total"] == 2


def test_past_tasks_are_read_only(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    yesterday = date.today() - __import__("datetime").timedelta(days=1)
    task_id = repository.database.execute(
        "INSERT INTO tasks(title, scheduled_date) VALUES (?, ?)",
        ("Historical task", yesterday.isoformat()),
    )
    try:
        repository.update_task(task_id, title="Changed history")
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("Expected past task editing to be rejected")
    try:
        repository.delete_task(task_id)
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("Expected past task deletion to be rejected")


def test_tasks_can_be_rescheduled_to_future_but_not_past(tmp_path: Path) -> None:
    from datetime import timedelta
    repository = make_repository(tmp_path)
    task_id = repository.add_task(title="Plan research", day=date.today())
    tomorrow = date.today() + timedelta(days=1)
    repository.update_task(task_id, scheduled_date=tomorrow)
    assert repository.list_tasks(tomorrow)[0]["id"] == task_id
    try:
        repository.update_task(task_id, scheduled_date=date.today() - timedelta(days=1))
    except ValueError as exc:
        assert "today or a future" in str(exc)
    else:
        raise AssertionError("Expected scheduling into the past to be rejected")
