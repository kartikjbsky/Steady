from pathlib import Path

from steady.database import Database


def test_database_initializes_and_seeds_defaults(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()

    habits = db.fetch_all("SELECT name, is_builtin FROM habits ORDER BY sort_order")
    reasons = db.fetch_all("SELECT code FROM miss_reasons ORDER BY sort_order")

    assert [row["name"] for row in habits] == ["Morning exercise", "Meditation"]
    assert all(row["is_builtin"] == 1 for row in habits)
    assert len(reasons) >= 6


def test_task_insert_and_foreign_key(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()
    task_id = db.execute(
        "INSERT INTO tasks(title, scheduled_date) VALUES (?, ?)",
        ("Read one research paper", "2026-11-12"),
    )
    rows = db.fetch_all("SELECT title, status FROM tasks WHERE id = ?", (task_id,))
    assert rows[0]["title"] == "Read one research paper"
    assert rows[0]["status"] == "todo"


def test_v1_database_migrates_to_current_schema_in_place(tmp_path: Path) -> None:
    import sqlite3

    database_path = tmp_path / "legacy-v1.sqlite3"
    schema_v2 = (Path(__file__).parent / "fixtures" / "schema_v2.sql").read_text(encoding="utf-8")
    schema_v1 = schema_v2.replace(
        "    session_type        TEXT NOT NULL DEFAULT 'focus'\n"
        "                        CHECK (session_type IN ('focus', 'short_break', 'long_break')),\n",
        "",
    )
    connection = sqlite3.connect(database_path)
    connection.executescript(schema_v1)
    connection.execute("PRAGMA user_version = 1")
    connection.execute(
        "INSERT INTO focus_sessions(started_at, planned_seconds, outcome) VALUES (?, ?, ?)",
        ("2026-11-12T10:00:00Z", 1500, "completed"),
    )
    connection.execute(
        "INSERT INTO habits(name, weekday_mask, is_builtin) VALUES (?, ?, 1)",
        ("Legacy habit", "1111111"),
    )
    connection.commit()
    connection.close()

    database = Database(database_path)
    database.initialize()
    session = database.fetch_all("SELECT session_type FROM focus_sessions")[0]
    habit = database.fetch_all(
        "SELECT category, start_date FROM habits WHERE name = ?", ("Legacy habit",)
    )[0]
    version = database.fetch_all("PRAGMA user_version")[0]["user_version"]

    assert session["session_type"] == "focus"
    assert habit["category"] == "other"
    assert habit["start_date"] == "1970-01-01"
    assert version == 5


def test_v2_database_migrates_habit_management_columns_in_place(tmp_path: Path) -> None:
    import sqlite3

    database_path = tmp_path / "legacy-v2.sqlite3"
    schema_v2 = (Path(__file__).parent / "fixtures" / "schema_v2.sql").read_text(encoding="utf-8")
    connection = sqlite3.connect(database_path)
    connection.executescript(schema_v2)
    connection.execute("PRAGMA user_version = 2")
    connection.execute(
        "INSERT INTO habits(name, weekday_mask, is_builtin) VALUES (?, ?, 1)",
        ("Legacy study habit", "1111100"),
    )
    connection.commit()
    connection.close()

    database = Database(database_path)
    database.initialize()
    habit = database.fetch_all(
        "SELECT name, category, start_date, reminder_enabled, archived_at FROM habits WHERE name = ?",
        ("Legacy study habit",),
    )[0]
    version = database.fetch_all("PRAGMA user_version")[0]["user_version"]

    assert habit["category"] == "other"
    assert habit["start_date"] == "1970-01-01"
    assert habit["reminder_enabled"] == 0
    assert habit["archived_at"] is None
    assert version == 5


def test_v4_database_migrates_weekly_timetable_in_place(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy-v4.sqlite3"
    database = Database(database_path)
    database.initialize()
    database.execute(
        "INSERT INTO todo_items(title, deadline_date) VALUES (?, ?)",
        ("Existing checklist item", "2026-11-20"),
    )
    database.execute("DROP TABLE timetable_entries")
    database.execute("PRAGMA user_version = 4")

    database.initialize()

    version = database.fetch_all("PRAGMA user_version")[0]["user_version"]
    todo = database.fetch_all("SELECT title FROM todo_items")
    timetable = database.fetch_all(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'timetable_entries'"
    )
    assert version == 5
    assert todo[0]["title"] == "Existing checklist item"
    assert len(timetable) == 1
