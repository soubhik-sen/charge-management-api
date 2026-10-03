"""Adapter-neutral progressive calendar-day tariff arithmetic."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal


def progressive_day_amount(
    bands: Sequence[tuple[int, int | None, Decimal]],
    days: int,
    *,
    require_next: bool = True,
) -> tuple[Decimal, Decimal, Decimal | None] | None:
    """Return accrued amount, current unit rate, and next unit rate.

    Bounds are inclusive, one-based billed days. Missing or overlapping days
    make the tariff ambiguous; a closed interval need not price another day.
    """
    if days < 0 or not bands:
        return None
    ordered = sorted(bands, key=lambda band: band[0])
    expected = 1
    for index, (start, end, rate) in enumerate(ordered):
        if start != expected or start < 1 or rate <= 0 or (end is not None and end < start):
            return None
        if end is None:
            if index != len(ordered) - 1:
                return None
            break
        expected = end + 1

    def rate_for(day: int) -> Decimal | None:
        return next((rate for start, end, rate in ordered
                     if start <= day and (end is None or day <= end)), None)

    current = rate_for(max(1, days))
    upcoming = rate_for(days + 1)
    if (days and current is None) or (require_next and upcoming is None):
        return None
    amount = Decimal(0)
    for start, end, rate in ordered:
        billed = max(0, min(days, end if end is not None else days) - start + 1)
        amount += rate * billed
    return amount, current or upcoming or Decimal(0), upcoming
