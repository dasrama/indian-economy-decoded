from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ObservationBase(BaseModel):
    indicator_id: int
    raw_file_id: Optional[int] = None
    observation_date: date
    value: float
    units: Optional[str] = None
    is_provisional: bool = False
    is_revised: bool = False
    revision_number: int = 0
    status: str = "ACTIVE"
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObservationCreate(ObservationBase):
    pass


class ObservationUpdate(BaseModel):
    value: Optional[float] = None
    units: Optional[str] = None
    is_provisional: Optional[bool] = None
    is_revised: Optional[bool] = None
    revision_number: Optional[int] = None
    status: Optional[str] = None
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObservationResponse(ObservationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesPoint(BaseModel):
    date: date
    value: float
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    is_provisional: bool = False
    is_revised: bool = False

    model_config = ConfigDict(from_attributes=True)


class ChartSeriesResponse(BaseModel):
    indicator_id: int
    indicator_code: str
    indicator_name: str
    units: str
    frequency: str
    data_points: List[TimeSeriesPoint]
    latest_date: Optional[date] = None
    latest_value: Optional[float] = None


class ObservationFilterParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = "ACTIVE"
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
