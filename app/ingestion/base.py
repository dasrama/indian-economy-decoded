from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date
from pydantic import BaseModel


class ParsedRecord(BaseModel):
    observation_date: date
    value: float
    units: Optional[str] = None
    is_provisional: bool = False
    metadata_json: Optional[Dict[str, Any]] = None


class BaseDownloader(ABC):
    """Abstract interface for downloading data files from RBI/DBIE sources."""

    @abstractmethod
    def download(self, target_dir: Path) -> Path:
        """Download raw file and return local path."""
        pass


class BaseParser(ABC):
    """Abstract interface for parsing raw RBI Excel/CSV into normalized records."""

    @abstractmethod
    def parse(self, file_path: Path) -> List[ParsedRecord]:
        """Parse raw file and return list of standardized observation records."""
        pass
