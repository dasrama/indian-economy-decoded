from datetime import date
from app.utils import normalize_to_month_start, parse_flexible_date




def test_date_utilities():
    d1 = parse_flexible_date("2026-09-15")
    assert d1 == date(2026, 9, 15)

    d2 = normalize_to_month_start(d1)
    assert d2 == date(2026, 9, 1)

    d3 = parse_flexible_date("15-08-2026")
    assert d3 == date(2026, 8, 15)
