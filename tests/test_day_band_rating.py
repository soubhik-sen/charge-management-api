from decimal import Decimal

from app.domain.day_band_rating import progressive_day_amount


def test_progressive_day_band_amount_and_next_rate():
    bands = [(1, 3, Decimal(50)), (4, None, Decimal(100))]
    assert progressive_day_amount(bands, 4) == (
        Decimal(250), Decimal(100), Decimal(100))
    assert progressive_day_amount(bands, 3) == (
        Decimal(150), Decimal(50), Decimal(100))


def test_closed_interval_does_not_require_future_band():
    bands = [(1, 3, Decimal(50))]
    assert progressive_day_amount(bands, 3, require_next=False) == (
        Decimal(150), Decimal(50), None)
    assert progressive_day_amount(bands, 3) is None


def test_gap_overlap_and_negative_days_fail_closed():
    assert progressive_day_amount([(1, 3, Decimal(50)), (5, None, Decimal(100))], 5) is None
    assert progressive_day_amount([(1, 3, Decimal(50)), (3, None, Decimal(100))], 3) is None
    assert progressive_day_amount([(1, None, Decimal(50))], -1) is None
