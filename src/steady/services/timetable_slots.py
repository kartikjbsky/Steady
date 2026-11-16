from __future__ import annotations

from datetime import time
from typing import Iterable


def normalise_time_slots(slots: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """Validate and sort custom daily time periods.

    Periods use local 24-hour HH:MM values. Periods may have different lengths,
    must stay within one calendar day, and may touch but must not overlap.
    """
    normalised: list[tuple[str, str]] = []
    for raw_start, raw_end in slots:
        start = time.fromisoformat(str(raw_start)).replace(second=0, microsecond=0)
        end = time.fromisoformat(str(raw_end)).replace(second=0, microsecond=0)
        start_text = start.strftime("%H:%M")
        end_text = end.strftime("%H:%M")
        if end <= start:
            raise ValueError(f"End time must be later than start time ({start_text}–{end_text}).")
        normalised.append((start_text, end_text))

    if not normalised:
        raise ValueError("Add at least one time period to the timetable.")
    if len(normalised) > 36:
        raise ValueError("The timetable supports up to 36 custom time periods.")

    normalised.sort(key=lambda period: period[0])
    previous_end: str | None = None
    for start, end in normalised:
        if previous_end is not None and start < previous_end:
            raise ValueError("Time periods cannot overlap. Adjust the start or end time.")
        previous_end = end
    return normalised
