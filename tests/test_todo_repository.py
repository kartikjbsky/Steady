from datetime import date, datetime
from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.todo_repository import TodoRepository


def make_repo(tmp_path: Path) -> TodoRepository:
    database = Database(tmp_path / "steady.sqlite3")
    database.initialize()
    return TodoRepository(database)


def test_create_list_update_and_delete_todo_item(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    item_id = todos.create(
        title="Submit book",
        deadline_date="2026-11-15",
        notification_enabled=True,
        notification_time="09:00",
    )

    row = todos.list_items()[0]
    assert row["id"] == item_id
    assert row["title"] == "Submit book"
    assert row["deadline_date"] == "2026-11-15"
    assert row["notification_enabled"] == 1
    assert row["notification_time"] == "09:00"
    assert row["is_completed"] == 0

    todos.update(item_id, title="Submit final book", deadline_date=date(2026, 11, 16))
    updated = todos.list_items()[0]
    assert updated["title"] == "Submit final book"
    assert updated["deadline_date"] == "2026-11-16"

    todos.set_completed(item_id, True)
    assert todos.list_items(include_completed=False) == []
    assert todos.list_items()[0]["is_completed"] == 1

    todos.delete(item_id)
    assert todos.list_items() == []


def test_notification_is_due_at_selected_local_time_and_only_once(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    item_id = todos.create(
        title="Book ticket",
        deadline_date="2026-11-17",
        notification_enabled=True,
        notification_time="09:00",
    )

    before = datetime(2026, 11, 17, 8, 59)
    at_time = datetime(2026, 11, 17, 9, 0)
    assert todos.due_notifications(before) == []
    due = todos.due_notifications(at_time)
    assert [item["id"] for item in due] == [item_id]

    assert todos.mark_notified(item_id) is True
    assert todos.mark_notified(item_id) is False
    assert todos.due_notifications(at_time) == []


def test_completed_or_muted_items_do_not_notify(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    completed_id = todos.create(
        title="Already done", deadline_date="2026-11-15", notification_time="08:00"
    )
    muted_id = todos.create(
        title="No alert", deadline_date="2026-11-15", notification_enabled=False
    )
    todos.set_completed(completed_id, True)

    due = todos.due_notifications(datetime(2026, 11, 15, 10, 0))
    assert {item["id"] for item in due} == set()
    assert todos.mark_notified(muted_id) is False


def test_editing_deadline_or_reenabling_notification_resets_delivery(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    item_id = todos.create(
        title="Renew ID", deadline_date="2026-11-15", notification_time="09:00"
    )
    assert todos.mark_notified(item_id)
    assert todos.due_notifications(datetime(2026, 11, 15, 10, 0)) == []

    todos.update(item_id, deadline_date="2026-11-16")
    row = todos.list_items()[0]
    assert row["notified_at"] is None
    assert len(todos.due_notifications(datetime(2026, 11, 16, 10, 0))) == 1

    assert todos.mark_notified(item_id)
    todos.set_notification_enabled(item_id, False)
    todos.set_notification_enabled(item_id, True)
    assert todos.list_items()[0]["notified_at"] is None


def test_reopening_completed_item_resets_its_notification(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    item_id = todos.create(title="Submit form", deadline_date="2026-11-15")
    todos.mark_notified(item_id)
    todos.set_completed(item_id, True)
    todos.set_completed(item_id, False)
    row = todos.list_items()[0]
    assert row["notified_at"] is None
    assert row["is_completed"] == 0


def test_invalid_todo_values_are_rejected(tmp_path: Path) -> None:
    todos = make_repo(tmp_path)
    with pytest.raises(ValueError, match="title"):
        todos.create(title="  ", deadline_date="2026-11-15")
    with pytest.raises(ValueError):
        todos.create(title="Bad date", deadline_date="15/11/2026")
    with pytest.raises(ValueError):
        todos.create(title="Bad time", deadline_date="2026-11-15", notification_time="29:90")


def test_v3_database_migrates_to_todo_schema_without_losing_existing_data(tmp_path: Path) -> None:
    database = Database(tmp_path / "legacy-v3.sqlite3")
    database.initialize()
    database.execute(
        "INSERT INTO tasks(title, scheduled_date) VALUES (?, ?)",
        ("Existing daily task", "2026-11-15"),
    )
    database.execute("DROP TABLE todo_items")
    database.execute("DROP TABLE timetable_entries")
    database.execute("PRAGMA user_version = 3")

    database.initialize()

    version = database.fetch_all("PRAGMA user_version")[0]["user_version"]
    tables = database.fetch_all(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'todo_items'"
    )
    existing_tasks = database.fetch_all("SELECT title FROM tasks")
    assert version == 5
    assert len(tables) == 1
    assert existing_tasks[0]["title"] == "Existing daily task"
