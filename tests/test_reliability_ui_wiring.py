from pathlib import Path


ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_settings_page_exposes_reliability_actions():
    source = (ROOT / "ui" / "pages" / "settings_page.py").read_text(encoding="utf-8")
    for label in ("Back up now", "Restore backup", "Export CSV", "Check database"):
        assert label in source
    assert "data_restored = Signal()" in source


def test_application_runs_startup_backup():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "automatic_backup_if_due" in source
    assert "backup_notice=backup_notice" in source


def test_archived_habits_have_permanent_delete_action():
    source = (ROOT / "ui" / "pages" / "habits_page.py").read_text(encoding="utf-8")
    repository = (ROOT / "repositories" / "habit_repository.py").read_text(encoding="utf-8")
    assert "Delete permanently" in source
    assert "delete_archived_habit" in source
    assert "def delete_archived(" in repository
