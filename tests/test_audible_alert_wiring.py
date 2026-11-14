from pathlib import Path


def test_focus_page_uses_bundled_chime_for_reminders_and_timer_completion() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "ui"
        / "pages"
        / "focus_page.py"
    ).read_text(encoding="utf-8")

    assert "from steady.services.alarm_sound import AlarmSound" in source
    assert "self.alarm_sound = AlarmSound(self)" in source
    assert "self._play_alarm_if_enabled()" in source
    assert "self.alarm_sound.play" in source
    assert 'self.settings.get("focus_sound", "1")' in source
    assert 'QPushButton("Test sound")' in source


def test_alarm_sound_has_audible_fallback_and_two_pass_chime() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "services"
        / "alarm_sound.py"
    ).read_text(encoding="utf-8")

    assert "setLoopCount(2)" in source
    assert "QApplication.beep()" in source
    assert "steady_alarm.wav" in source
