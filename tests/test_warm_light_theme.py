from pathlib import Path
import re


ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_warm_paper_asset_is_packaged():
    asset = ROOT / "assets" / "warm_paper.png"
    assert asset.is_file()
    assert asset.stat().st_size > 20_000
    package = (ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert '"steady.assets" = ["*.wav", "*.png"]' in package


def test_light_theme_uses_muted_parchment_not_white_surfaces():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "def _light_stylesheet()" in source
    assert "background-color: #D1C3A5;" in source
    assert "stop:0 #E4D8BF" in source and "stop:1 #DDD0B4" in source
    light = source[source.index("def _light_stylesheet"):source.index("def apply_theme")]
    assert "#FBFAF6" not in light
    assert "#FFFFFF" not in light
    assert "PAPER_ASSET.as_uri()" in source
    assert "QStackedWidget#pageStack" in source
    assert "QScrollArea::viewport" in source


def test_light_theme_has_restrained_red_actions_and_olive_progress():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "stop:0 #A84D47, stop:1 #873A36" in source
    assert "background-color: #89936D;" in source


def test_habit_matrix_checkbox_uses_shared_theme():
    source = (ROOT / "ui" / "pages" / "habits_page.py").read_text(encoding="utf-8")
    assert "check.setStyleSheet(" not in source
    assert "check.setMinimumSize(38, 36)" in source
    assert "QCheckBox::indicator" in (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")


def test_light_analytics_uses_matching_parchment_palette():
    source = (ROOT / "ui" / "pages" / "analytics_page.py").read_text(encoding="utf-8")
    assert 'bg, fg, muted = "#E6DBC4", "#38291F", "#6E5B48"' in source
    assert '"#CDBE9F", "#718FA2", "#89936D", "#A84D47", "#D2C3A5"' in source


def test_database_schema_uses_version_five_for_weekly_timetable():
    source = (ROOT / "database" / "db.py").read_text(encoding="utf-8")
    assert "SCHEMA_VERSION = 5" in source
