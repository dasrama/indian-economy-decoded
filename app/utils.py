import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Union
import dateutil.parser


# --- Hashing Utilities (FR-5, FR-6) ---

def calculate_file_hash(file_path: Union[str, Path]) -> str:
    """Calculate the SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    path = Path(file_path)
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# --- Date Utilities (FR-9, FR-11) ---

def parse_flexible_date(date_input: Union[str, date, datetime]) -> date:
    """
    Parse a date from diverse RBI date formats such as:
    - '2026-09-01'
    - 'September 2026' or 'Sep-26' or 'Sep-2026'
    - '01-09-2026' or '01/09/2026'
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
