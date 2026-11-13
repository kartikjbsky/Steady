from pathlib import Path


def test_delete_confirmation_uses_supported_custom_destructive_button():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "ui"
        / "pages"
        / "habits_page.py"
    ).read_text(encoding="utf-8")

    assert "QMessageBox.StandardButton.Delete" not in source
    assert '"Delete permanently", QMessageBox.ButtonRole.DestructiveRole' in source
    assert "confirmation.clickedButton() is not delete_button" in source
    assert "confirmation.setDefaultButton(cancel_button)" in source
