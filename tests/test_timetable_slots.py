import pytest

from steady.services.timetable_slots import normalise_time_slots


def test_custom_periods_can_have_different_lengths_and_are_sorted():
    assert normalise_time_slots([("09:00", "10:15"), ("07:00", "08:30"), ("10:30", "11:00")]) == [
        ("07:00", "08:30"), ("09:00", "10:15"), ("10:30", "11:00")
    ]


def test_adjacent_periods_are_allowed():
    assert normalise_time_slots([("08:00", "09:00"), ("07:00", "08:00")]) == [
        ("07:00", "08:00"), ("08:00", "09:00")
    ]


def test_overlapping_periods_are_rejected():
    with pytest.raises(ValueError, match="cannot overlap"):
        normalise_time_slots([("07:00", "09:00"), ("08:30", "10:00")])


def test_end_time_must_follow_start_time():
    with pytest.raises(ValueError, match="later than start"):
        normalise_time_slots([("10:00", "09:00")])


def test_empty_and_excessive_period_lists_are_rejected():
    with pytest.raises(ValueError, match="at least one"):
        normalise_time_slots([])
    with pytest.raises(ValueError, match="up to 36"):
        normalise_time_slots([(f"{(minute // 60):02d}:{(minute % 60):02d}", f"{((minute + 5) // 60):02d}:{((minute + 5) % 60):02d}") for minute in range(0, 185, 5)])
