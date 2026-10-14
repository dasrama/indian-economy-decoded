from datetime import date
from pathlib import Path
from app.utils.hashing import calculate_bytes_hash, calculate_file_hash
from app.utils.dates import normalize_to_month_start, parse_flexible_date


def test_hashing_utilities(tmp_path: Path):
    sample_bytes = b"Hello RBI Indicators"
    computed_hash = calculate_bytes_hash(sample_bytes)
    assert len(computed_hash) == 64

    test_file = tmp_path / "test.txt"
    test_file.write_bytes(sample_bytes)
    file_hash = calculate_file_hash(test_file)
    assert file_hash == computed_hash


def test_date_utilities():
    d1 = parse_flexible_date("2026-09-15")
    assert d1 == date(2026, 9, 15)

    d2 = normalize_to_month_start(d1)
    assert d2 == date(2026, 9, 1)

    d3 = parse_flexible_date("15-08-2026")
    assert d3 == date(2026, 8, 15)
