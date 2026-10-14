from datetime import date, datetime
from typing import Optional, Union
import dateutil.parser


def parse_flexible_date(date_input: Union[str, date, datetime]) -> date:
    """
    Parse a date from diverse RBI date formats such as:
    - '2026-09-01'
    - 'September 2026' or 'Sep-26' or 'Sep-2026'
    - '01-09-2026' or '01/09/2026'
    - '2026-Q2'
    """
    if isinstance(date_input, date) and not isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, datetime):
        return date_input.date()

    date_str = str(date_input).strip()
    parsed = dateutil.parser.parse(date_str, dayfirst=True)
    return parsed.date()


def normalize_to_month_start(d: date) -> date:
    """Normalize any date within a month to the 1st of that month."""
    return date(d.year, d.month, 1)
