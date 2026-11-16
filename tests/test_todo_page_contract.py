from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_todo_page_keeps_task_deadline_done_and_notification_in_table_row():
    source = (ROOT / "ui" / "pages" / "todo_page.py").read_text(encoding="utf-8")
    assert 'QTableWidget(0, 5)' in source
    assert '["Task", "Deadline", "Done", "Notification", "Actions"]' in source
    assert "QDateEdit" in source
    assert "QCheckBox(\"Done\")" in source
    assert "QCheckBox(\"Yes\")" in source
    assert "QTimeEdit" in source


def test_todo_page_uses_saved_alarm_preference_and_due_notification_service():
    source = (ROOT / "ui" / "pages" / "todo_page.py").read_text(encoding="utf-8")
    assert "self.alarm_sound.play()" in source
    assert 'self.settings.get("focus_sound", "1")' in source
    assert "self.repository.due_notifications()" in source
    assert "self.repository.mark_notified" in source


def test_todo_checklist_is_added_to_workspace_navigation_and_dashboard():
    main = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    dashboard = (ROOT / "ui" / "pages" / "dashboard_page.py").read_text(encoding="utf-8")
    assert '("To-do checklist", "Alt+3")' in main
    assert "TodoPage(database)" in main
    assert "open_todo_requested" in dashboard
    assert 'self._make_card("To-do deadlines")' in dashboard
