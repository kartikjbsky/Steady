from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from steady.database import Database
from steady.repositories.analytics_repository import AnalyticsRepository


def make_repository(tmp_path: Path) -> tuple[Database, AnalyticsRepository]:
    database = Database(tmp_path / "steady-analytics-test.sqlite3")
    database.initialize()
    return database, AnalyticsRepository(database)


def test_period_summary_counts_tasks_habits_and_focus_time(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    day = date(2026, 11, 12)  # Thursday

    done_task = database.execute(
        "INSERT INTO tasks(title, scheduled_date, status) VALUES (?, ?, 'done')",
        ("Qiskit circuit", day.isoformat()),
    )
    database.execute(
        "INSERT INTO tasks(title, scheduled_date, status) VALUES (?, ?, 'todo')",
        ("Read paper", day.isoformat()),
    )
    database.execute(
        "INSERT INTO tasks(title, scheduled_date, status) VALUES (?, ?, 'cancelled')",
        ("Cancelled", day.isoformat()),
    )
    habits = database.fetch_all(
        "SELECT id, name FROM habits WHERE is_active = 1 ORDER BY sort_order"
    )
    database.execute(
        """INSERT INTO habit_entries(habit_id, entry_date, status)
           VALUES (?, ?, 'done')""",
        (int(habits[0]["id"]), day.isoformat()),
    )

    local_midday = datetime.combine(day, time(12), tzinfo=datetime.now().astimezone().tzinfo)
    started_utc = local_midday.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    database.execute(
        """INSERT INTO focus_sessions
           (started_at, ended_at, planned_seconds, actual_seconds, outcome, session_type)
           VALUES (?, ?, 1800, 1500, 'stopped', 'focus')""",
        (started_utc, started_utc),
    )

    summary = repository.get_period_summary(1, end_date=day)
    assert summary["task_total"] == 2
    assert summary["task_done"] == 1
    assert summary["habit_total"] == 2
    assert summary["habit_done"] == 1
    assert summary["focus_seconds"] == 1500
    assert summary["focus_sessions"] == 1
    assert summary["task_percent"] == 50
    assert summary["habit_percent"] == 50
    assert done_task > 0


def test_period_summary_includes_empty_days_and_validates_window(tmp_path: Path) -> None:
    _database, repository = make_repository(tmp_path)
    summary = repository.get_period_summary(7, end_date=date(2026, 11, 12))
    assert len(summary["days"]) == 7
    assert summary["days"][-1]["date"] == "2026-11-12"
    assert summary["task_total"] == 0
    try:
        repository.get_period_summary(0)
    except ValueError as exc:
        assert "between 1 and 366" in str(exc)
    else:
        raise AssertionError("Expected invalid period to be rejected")


def test_missed_reason_breakdown_combines_tasks_and_habits(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    day = date(2026, 11, 12)
    reason_rows = database.fetch_all(
        "SELECT id FROM miss_reasons WHERE code = 'low_energy'"
    )
    reason_id = int(reason_rows[0]["id"])
    database.execute(
        """INSERT INTO tasks(title, scheduled_date, status, miss_reason_id)
           VALUES (?, ?, 'missed', ?)""",
        ("Exercise", day.isoformat(), reason_id),
    )
    habit = database.fetch_all("SELECT id FROM habits ORDER BY sort_order LIMIT 1")[0]
    database.execute(
        """INSERT INTO habit_entries(habit_id, entry_date, status, miss_reason_id)
           VALUES (?, ?, 'missed', ?)""",
        (int(habit["id"]), day.isoformat(), reason_id),
    )
    breakdown = repository.get_missed_reason_breakdown(1, end_date=day)
    assert breakdown == [{"label": "Low energy", "total": 2}]


def test_archived_habit_contributes_only_to_days_before_archive(tmp_path: Path) -> None:
    database, repository = make_repository(tmp_path)
    habit_id = database.execute(
        "INSERT INTO habits(name, weekday_mask, category, start_date) VALUES (?, ?, ?, ?)",
        ("Archived study habit", "1111111", "study", "2026-11-01"),
    )
    database.execute(
        "INSERT INTO habit_entries(habit_id, entry_date, status) VALUES (?, ?, 'done')",
        (habit_id, "2026-11-10"),
    )
    # Use a fixed archive date so the test remains deterministic on every machine.
    database.execute(
        "UPDATE habits SET is_active = 0, archived_at = ? WHERE id = ?",
        ("2026-11-11T18:00:00+05:30", habit_id),
    )

    summary = repository.get_period_summary(3, end_date=date(2026, 11, 12))
    by_day = {row["date"]: row for row in summary["days"]}

    # Two seeded habits remain scheduled daily. The archived habit is included
    # on Nov 10 and on its archive date, but not on Nov 12.
    assert by_day["2026-11-10"]["habit_total"] == 3
    assert by_day["2026-11-10"]["habit_done"] == 1
    assert by_day["2026-11-11"]["habit_total"] == 3
    assert by_day["2026-11-12"]["habit_total"] == 2


def test_habit_manager_checkin_is_counted_in_progress(tmp_path: Path) -> None:
    from steady.repositories.planner_repository import PlannerRepository

    database, analytics = make_repository(tmp_path)
    planner = PlannerRepository(database)
    today = date.today()
    habits = planner.list_habits(today)
    assert habits, "The database should seed at least one daily habit."

    selected = habits[0]
    planner.set_habit_status(int(selected["id"]), today, "done")

    summary = analytics.get_period_summary(1, end_date=today)
    assert summary["habit_done"] == 1
    assert summary["habit_total"] >= 1
    assert summary["habit_percent"] > 0

    # Unchecking from the Habits page writes pending to the same entry.
    planner.set_habit_status(int(selected["id"]), today, "pending")
    summary = analytics.get_period_summary(1, end_date=today)
    assert summary["habit_done"] == 0
