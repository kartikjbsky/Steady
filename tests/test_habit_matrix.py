from datetime import date

from steady.services.habit_matrix import compute_month_progress


def test_month_progress_counts_only_scheduled_days_that_have_occurred():
    habits = [
        {
            "id": 1, "name": "Meditation", "weekday_mask": "1111111",
            "start_date": "2026-12-01", "is_active": 1, "archived_at": None,
        },
        {
            "id": 2, "name": "Yoga", "weekday_mask": "1111100",
            "start_date": "2026-12-01", "is_active": 1, "archived_at": None,
        },
    ]
    entries = {
        (1, "2026-12-01"): "done",
        (1, "2026-12-02"): "done",
        (2, "2026-12-01"): "done",
        (2, "2026-12-05"): "done",  # Saturday: not scheduled for Yoga
    }

    result = compute_month_progress(
        habits, entries, 2026, 12, today=date(2026, 12, 3)
    )

    assert result["scheduled"] == 6  # 3 meditation days + 3 weekdays for yoga through Dec 3
    assert result["done"] == 3
    assert result["percent"] == 50
    assert result["habits"][1] == {"scheduled": 3, "done": 2, "percent": 67}
    assert result["habits"][2] == {"scheduled": 3, "done": 1, "percent": 33}


def test_archived_habit_counts_only_through_archive_date():
    habits = [{
        "id": 7, "name": "Yoga", "weekday_mask": "1111111",
        "start_date": "2026-12-01", "is_active": 0,
        "archived_at": "2026-12-03T12:00:00+05:30",
    }]
    entries = {(7, "2026-12-01"): "done", (7, "2026-12-05"): "done"}

    result = compute_month_progress(habits, entries, 2026, 12, today=date(2026, 12, 31))

    assert result["scheduled"] == 3
    assert result["done"] == 1


def test_paused_habits_are_excluded_from_progress_totals():
    habits = [{
        "id": 4, "name": "Paused", "weekday_mask": "1111111",
        "start_date": "2026-12-01", "is_active": 0, "archived_at": None,
    }]
    result = compute_month_progress(habits, {}, 2026, 12, today=date(2026, 12, 5))
    assert result["scheduled"] == 0
    assert result["done"] == 0


def test_future_month_does_not_add_future_checkins_to_denominator():
    habits = [{
        "id": 2, "name": "Daily", "weekday_mask": "1111111",
        "start_date": "2027-01-01", "is_active": 1, "archived_at": None,
    }]
    result = compute_month_progress(habits, {}, 2027, 1, today=date(2026, 12, 13))
    assert result["scheduled"] == 0
    assert result["percent"] == 0
