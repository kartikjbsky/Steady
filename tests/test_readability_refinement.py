from pathlib import Path


ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_month_matrix_sizes_full_table_and_scroll_area_to_all_rows():
    source = (ROOT / "ui" / "pages" / "habits_page.py").read_text(encoding="utf-8")
    assert "setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)" in source
    assert "setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)" in source
    assert "row_height = 50" in source
    assert "sum(self.matrix_table.rowHeight(i) for i in range(len(habits)))" in source
    assert "self.matrix_table.setFixedHeight(table_height)" in source
    assert "self.matrix_scroll.setFixedHeight(table_height + horizontal_bar_height + 6)" in source


def test_global_typography_and_page_titles_are_larger_and_bold():
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    base_page = (ROOT / "ui" / "pages" / "base_page.py").read_text(encoding="utf-8")

    assert "font-size: 12pt;" in theme
    assert "font-size: 27pt;" in theme
    assert "font-weight: 750;" in theme
    assert "font-size: 11pt;" in theme
    assert "app_font.setPointSizeF(12.0)" in app
    assert 'font-size: 14pt; font-weight: 800;' in base_page


def test_visual_asset_and_schema_v3_are_preserved():
    asset = ROOT / "assets" / "ambient_threads.png"
    db = (ROOT / "database" / "db.py").read_text(encoding="utf-8")
    assert asset.is_file()
    assert "SCHEMA_VERSION = 3" in db
