import pytest

from steady.services.duration import duration_to_seconds, seconds_to_duration_amount


def test_duration_supports_minutes_and_hours() -> None:
    assert duration_to_seconds(25, "minutes") == 1500
    assert duration_to_seconds(2, "hours") == 7200
    assert duration_to_seconds(1.5, "hours") == 5400


def test_switching_unit_keeps_duration_close_to_original() -> None:
    original = duration_to_seconds(100, "minutes")
    hours_value = seconds_to_duration_amount(original, "hours")
    converted = duration_to_seconds(hours_value, "hours")
    assert abs(converted - original) <= 2


def test_duration_is_clamped_to_one_day() -> None:
    assert duration_to_seconds(30, "hours") == 86400
    assert duration_to_seconds(0.001, "hours") == 60


def test_invalid_duration_is_rejected() -> None:
    with pytest.raises(ValueError):
        duration_to_seconds(0, "minutes")
    with pytest.raises(ValueError):
        duration_to_seconds(10, "days")
