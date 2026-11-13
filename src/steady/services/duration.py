from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_DURATION_SECONDS = 24 * 60 * 60
MIN_DURATION_SECONDS = 60


def duration_to_seconds(amount: int | float | str, unit: str) -> int:
    """Convert a user-entered minute/hour amount to whole seconds safely."""
    if unit not in {"minutes", "hours"}:
        raise ValueError("Duration unit must be 'minutes' or 'hours'.")
    try:
        number = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Duration must be a valid number.") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Duration must be greater than zero.")
    multiplier = Decimal(3600 if unit == "hours" else 60)
    seconds = int((number * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(MIN_DURATION_SECONDS, min(seconds, MAX_DURATION_SECONDS))


def seconds_to_duration_amount(seconds: int, unit: str) -> float:
    """Convert seconds to a display amount for the selected unit."""
    if unit not in {"minutes", "hours"}:
        raise ValueError("Duration unit must be 'minutes' or 'hours'.")
    safe_seconds = max(MIN_DURATION_SECONDS, min(int(seconds), MAX_DURATION_SECONDS))
    divisor = 3600 if unit == "hours" else 60
    precision = 3 if unit == "hours" else 0
    return round(safe_seconds / divisor, precision)
