from pathlib import Path
import re


ROOT = Path(__file__).parents[1] / "src" / "steady"


def test_ambient_background_asset_is_present_and_nonempty():
    asset = ROOT / "assets" / "ambient_threads.png"
    assert asset.is_file()
    assert asset.stat().st_size > 10_000


def test_dark_theme_uses_reference_inspired_palette_and_background_asset():
    source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "ambient_threads.png" in source
    assert "#05070A" in source
    assert "#F2F0DF" in source
    assert "background-position: left center" in source
    assert "rgba(13, 19, 26, 226)" in source


def test_visual_asset_is_included_in_package_data():
    pyproject = (ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert '"steady.assets" = ["*.wav", "*.png"]' in pyproject


def test_app_selects_an_installed_modern_sans_font():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    for font in ("Aptos", "Noto Sans", "Inter", "Cantarell", "DejaVu Sans"):
        assert font in source
