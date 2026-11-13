from datetime import datetime, timedelta, timezone
from pathlib import Path

from steady.database import Database
from steady.repositories.focus_repository import FocusRepository


def make_repository(tmp_path: Path) -> FocusRepository:
    database = Database(tmp_path / "steady-focus-test.sqlite3")
    database.initialize()
    return FocusRepository(database)


def test_focus_session_start_finish_and_linked_task(tmp_path: Path) -> None:
    database = Database(tmp_path / "steady-focus-test.sqlite3")
    database.initialize()
    repository = FocusRepository(database)
    task_id = database.execute(
        "INSERT INTO tasks(title, scheduled_date) VALUES (?, ?)",
        ("Read a paper", "2026-11-12"),
    )

    session_id = repository.start_session(
        planned_seconds=1500,
        session_type="focus",
        linked_task_id=task_id,
    )
    repository.finish_session(session_id, outcome="completed", actual_seconds=1500)

    rows = repository.list_sessions()
    assert len(rows) == 1
    assert rows[0]["id"] == session_id
    assert rows[0]["session_type"] == "focus"
    assert rows[0]["outcome"] == "completed"
    assert rows[0]["actual_seconds"] == 1500
    assert rows[0]["task_title"] == "Read a paper"
    assert repository.get_focus_totals(7) == {"sessions": 1, "seconds": 1500}


def test_recover_open_sessions_marks_interrupted(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    session_id = repository.start_session(planned_seconds=600, session_type="short_break")

    assert repository.recover_open_sessions() == 1
    session = repository.list_sessions()[0]
    assert session["id"] == session_id
    assert session["outcome"] == "interrupted"
    assert session["session_type"] == "short_break"


def test_one_off_reminder_fires_once_and_disables(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    due = datetime.now(timezone.utc) - timedelta(minutes=2)
    reminder_id = repository.create_reminder(
        title="Take a short break", due_at=due, message="Stretch and drink water."
    )

    due_rows = repository.due_reminders()
    assert [row["id"] for row in due_rows] == [reminder_id]

    fired = repository.mark_reminder_fired(reminder_id)
    assert fired is not None
    assert fired["title"] == "Take a short break"
    assert repository.due_reminders() == []
    assert repository.list_reminders()[0]["is_enabled"] == 0


def test_daily_reminder_advances_past_missed_occurrences(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    due = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
    fired_at = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
    reminder_id = repository.create_reminder(
        title="Daily planning", due_at=due, repeat_rule="daily"
    )

    repository.mark_reminder_fired(reminder_id, fired_at=fired_at)
    stored = repository.list_reminders()[0]
    next_due = datetime.fromisoformat(stored["due_at"].replace("Z", "+00:00"))
    assert next_due == datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)
    assert stored["is_enabled"] == 1


def test_weekday_reminder_skips_weekend(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    due = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)  # Friday
    fired_at = datetime(2026, 11, 13, 9, 1, tzinfo=timezone.utc)
    reminder_id = repository.create_reminder(
        title="Weekly workday check-in", due_at=due, repeat_rule="weekdays"
    )

    repository.mark_reminder_fired(reminder_id, fired_at=fired_at)
    stored = repository.list_reminders()[0]
    next_due = datetime.fromisoformat(stored["due_at"].replace("Z", "+00:00"))
    assert next_due == datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)


def test_reminder_snooze_reactivates_one_off(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    due = datetime.now(timezone.utc) - timedelta(minutes=1)
    reminder_id = repository.create_reminder(title="Water", due_at=due)
    repository.mark_reminder_fired(reminder_id)
    repository.snooze_reminder(reminder_id, 10)

    stored = repository.list_reminders()[0]
    next_due = datetime.fromisoformat(stored["due_at"].replace("Z", "+00:00"))
    assert stored["is_enabled"] == 1
    assert next_due > datetime.now(timezone.utc)
    assert next_due <= datetime.now(timezone.utc) + timedelta(minutes=11)
