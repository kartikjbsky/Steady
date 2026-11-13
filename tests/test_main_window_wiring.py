from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_main_window_connections_match_page_apis():
    main = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    day = (ROOT / "ui" / "pages" / "day_page.py").read_text(encoding="utf-8")
    focus = (ROOT / "ui" / "pages" / "focus_page.py").read_text(encoding="utf-8")

    assert "manage_habits_requested" not in main
    assert "selected_date_changed = Signal(object)" in day
    assert "def set_selected_day(" in day
    assert "open_daily_plan_requested = Signal()" in focus


def test_dashboard_and_calendar_date_navigation_helpers_exist():
    main = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    day = (ROOT / "ui" / "pages" / "day_page.py").read_text(encoding="utf-8")

    assert "self.pages[1].set_selected_day(selected_day)" in main
    assert "self.pages[1].selected_date_changed.connect" in main
    assert "self.pages[4].open_daily_plan_requested.connect" in main
