from pathlib import Path


def test_main_window_does_not_connect_nonexistent_day_page_signal():
    root = Path(__file__).parents[1] / "src" / "steady"
    main_window = (root / "ui" / "main_window.py").read_text(encoding="utf-8")
    day_page = (root / "ui" / "pages" / "day_page.py").read_text(encoding="utf-8")
    assert "manage_habits_requested" not in main_window
    assert "class DayPage" in day_page


def test_database_still_supports_schema_v3():
    db_source = (Path(__file__).parents[1] / "src" / "steady" / "database" / "db.py").read_text(encoding="utf-8")
    assert "SCHEMA_VERSION = 3" in db_source
