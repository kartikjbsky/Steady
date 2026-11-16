from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_timetable_is_a_separate_workspace_page():
    main = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "from steady.ui.pages.timetable_page import TimetablePage" in main
    assert '("Timetable", "Alt+4")' in main
    assert "TimetablePage(database)" in main


def test_weekly_matrix_is_empty_and_cells_are_clickable():
    page = (ROOT / "ui" / "pages" / "timetable_page.py").read_text(encoding="utf-8")
    assert 'self.table = QTableWidget(0, 8)' in page
    assert 'self.table.cellClicked.connect(self._cell_clicked)' in page
    assert '"Click to add an activity for' in page
    assert "self.repository.save_slot(" in page
    assert "self.repository.clear_slot(" in page


def test_each_time_period_has_independent_editable_start_and_end_times():
    page = (ROOT / "ui" / "pages" / "timetable_page.py").read_text(encoding="utf-8")
    assert 'QPushButton("Edit individual time periods")' in page
    assert 'self.slots_table = QTableWidget(0, 2)' in page
    assert 'self.slots_table.setCellWidget(row, 0, self._make_time_input(start_time))' in page
    assert 'self.slots_table.setCellWidget(row, 1, self._make_time_input(end_time))' in page
    assert 'self.settings.set("timetable_custom_slots", json.dumps(self.slots))' in page
    assert 'self.settings.get("timetable_custom_slots", "")' in page


def test_time_column_keeps_complete_labels_visible():
    page = (ROOT / "ui" / "pages" / "timetable_page.py").read_text(encoding="utf-8")
    assert "self.table.setColumnWidth(0, 245)" in page
    assert "self.table.setTextElideMode(Qt.TextElideMode.ElideNone)" in page
    assert "self.table.setWordWrap(False)" in page
    assert "self.table.setMinimumWidth(1320)" in page


def test_custom_period_validation_is_used():
    page = (ROOT / "ui" / "pages" / "timetable_page.py").read_text(encoding="utf-8")
    assert "normalise_time_slots" in page
    assert '"Time periods cannot overlap' in (ROOT / "services" / "timetable_slots.py").read_text(encoding="utf-8")
