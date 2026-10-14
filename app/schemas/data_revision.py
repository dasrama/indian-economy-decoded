from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DataRevisionBase(BaseModel):
    indicator_id: int
    observation_id: Optional[int] = None
    raw_file_id: Optional[int] = None
    observation_date: date
    previous_value: float
    new_value: float
    difference: Optional[float] = None
    percentage_change: Optional[float] = None
    revision_reason: Optional[str] = Field(None, max_length=255)
    metadata_json: Optional[Dict[str, Any]] = None


class DataRevisionCreate(DataRevisionBase):
    pass


class DataRevisionResponse(DataRevisionBase):
    id: int
    revision_timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
