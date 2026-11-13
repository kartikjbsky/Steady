from pathlib import Path


def test_habit_matrix_uses_real_line_breaks_in_day_headers():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "ui"
        / "pages"
        / "habits_page.py"
    ).read_text(encoding="utf-8")
    assert 'headers.append(f"{day_number:02d}\\n{self.DAY_SHORT[cell_day.weekday()]}")' in source
    theme = (Path(__file__).parents[1] / "src" / "steady" / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "QCheckBox::indicator" in theme
    assert "width: 22px;" in theme
    assert "check.setMinimumSize(38, 36)" in source
    assert "Select the square to toggle this check-in." in source
