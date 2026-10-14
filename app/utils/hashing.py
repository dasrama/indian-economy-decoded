import hashlib
from pathlib import Path
from typing import Union


def calculate_file_hash(file_path: Union[str, Path]) -> str:
    """Calculate the SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    path = Path(file_path)
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_bytes_hash(data: bytes) -> str:
    """Calculate the SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()
