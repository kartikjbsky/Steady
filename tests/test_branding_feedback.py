from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLSe_Cbsx-IOLbVw8Yd8RrK_ZdqPmG7C_C7G6KZoBWvQbm7lhWA/viewform?usp=publish-editor"
)


def test_supplied_logo_assets_are_bundled():
    assets = ROOT / "src/steady/assets"
    assert (assets / "steady_wordmark.png").is_file()
    assert (assets / "steady_icon.png").is_file()
    assert (assets / "feedback_form_button.png").is_file()
    assert (assets / "warm_paper.png").is_file()


def test_sidebar_uses_full_wordmark_and_copyright():
    source = (ROOT / "src/steady/ui/main_window.py").read_text(encoding="utf-8")
    assert '"steady_wordmark.png"' in source
    assert "Kartikkumar Bagilavaidya" in source
    assert "All rights reserved." in source
    assert 'QLabel("STEADY")' not in source


def test_application_and_installer_use_icon_only_mark():
    app_source = (ROOT / "src/steady/app.py").read_text(encoding="utf-8")
    assert '"steady_icon.png"' in app_source
    for name in ("steady.png", "steady.ico", "steady.icns"):
        assert (ROOT / "packaging" / name).is_file()


def test_settings_feedback_button_opens_the_supplied_form():
    source = (ROOT / "src/steady/ui/pages/settings_page.py").read_text(encoding="utf-8")
    assert FEEDBACK_URL in source
    assert 'QDesktopServices.openUrl(QUrl(FEEDBACK_FORM_URL))' in source
    assert '"feedback_form_button.png"' in source
    assert 'self.feedback_button.setIcon(QIcon(str(feedback_image_path)))' in source
    assert 'self.feedback_button.setIconSize(QSize(570, 190))' in source
    assert 'feedback_button_row.addWidget(self.feedback_button)' in source
    assert 'QPushButton("Open feedback form")' not in source
