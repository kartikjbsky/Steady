from pathlib import Path

from steady.database import Database


def test_fresh_install_starts_without_personal_tasks_or_journal_data(tmp_path: Path):
    database = Database(tmp_path / "fresh-user" / "steady.sqlite3")
    database.initialize()

    assert database.fetch_all("SELECT id FROM tasks") == []
    assert database.fetch_all("SELECT id FROM daily_reflections") == []
    assert database.fetch_all("SELECT id FROM reminders") == []
    assert database.fetch_all("SELECT id FROM focus_sessions") == []

    # Only neutral built-in setup is seeded for a first-time user.
    assert [row["name"] for row in database.fetch_all(
        "SELECT name FROM habits ORDER BY sort_order"
    )] == ["Morning exercise", "Meditation"]


def test_live_database_and_backups_are_not_pyinstaller_bundle_inputs():
    root = Path(__file__).parents[1]
    build_script = (root / "packaging" / "build_app.py").read_text(encoding="utf-8")
    assert '"--add-data", f"{assets}{os.pathsep}steady/assets"' in build_script
    assert '"--add-data", f"{schema}{os.pathsep}steady/database"' in build_script
    assert "get_database_path" not in build_script
    assert "backups" not in build_script


def test_gitignore_excludes_personal_sqlite_and_backup_files():
    ignore = (Path(__file__).parents[1] / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("*.sqlite3", "*.db", "backups/", "Steady_Export_*/"):
        assert pattern in ignore
