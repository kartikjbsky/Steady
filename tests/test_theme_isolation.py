from pathlib import Path


ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_dark_theme_explicitly_clears_light_scroll_backgrounds():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    dark = source[source.index("def _dark_stylesheet"):source.index("def _light_stylesheet")]
    assert "QScrollArea {" in dark
    assert "QScrollArea::viewport {" in dark
    assert "QWidget#scrollContent {" in dark
    assert "background-color: #070A0E;" in dark
    assert "background-image: none;" in dark


def test_light_theme_applies_parchment_only_to_scroll_content():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    light = source[source.index("def _light_stylesheet"):source.index("def apply_theme")]
    assert "QWidget#scrollContent {" in light
    assert "PAPER_ASSET.as_uri()" in source
    assert "background-color: #D1C3A5;" in light


def test_all_scrollable_pages_mark_their_content_widgets():
    for name in ("habits_page.py", "reflection_page.py", "analytics_page.py", "focus_page.py"):
        source = (ROOT / "ui" / "pages" / name).read_text(encoding="utf-8")
        assert 'inner.setObjectName("scrollContent")' in source, name
        assert "WA_StyledBackground" in source, name


def test_dark_mode_does_not_select_the_paper_asset():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    dark = source[source.index("def _dark_stylesheet"):source.index("def _light_stylesheet")]
    assert "PAPER_ASSET" not in dark
    assert "THREADS_ASSET" in dark


def test_database_schema_version_includes_weekly_timetable():
    source = (ROOT / "database" / "db.py").read_text(encoding="utf-8")
    assert "SCHEMA_VERSION = 5" in source
