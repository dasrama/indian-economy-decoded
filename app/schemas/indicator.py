from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.category import CategoryResponse
from app.schemas.data_source import DataSourceResponse


class IndicatorBase(BaseModel):
    category_id: Optional[int] = Field(None, description="Associated category ID")
    source_id: Optional[int] = Field(None, description="Associated data source ID")
    code: str = Field(..., max_length=50, description="Unique code e.g. CPI_COMBINED_GENERAL")
    name: str = Field(..., max_length=255, description="Full human-readable name")
    slug: str = Field(..., max_length=100, description="URL slug")
    description: Optional[str] = Field(None, description="Plain-English explanation of indicator")
    frequency: str = Field(default="MONTHLY", max_length=20, description="DAILY, WEEKLY, MONTHLY, QUARTERLY, etc.")
    units: str = Field(..., max_length=50, description="Measurement units")
    is_active: bool = True


class IndicatorCreate(IndicatorBase):
    pass


class IndicatorUpdate(BaseModel):
    category_id: Optional[int] = None
    source_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    frequency: Optional[str] = Field(None, max_length=20)
    units: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    latest_observation_date: Optional[date] = None
    latest_value: Optional[float] = None


class IndicatorResponse(IndicatorBase):
    id: int
    latest_observation_date: Optional[date] = None
    latest_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndicatorDetailResponse(IndicatorResponse):
    category: Optional[CategoryResponse] = None
    source: Optional[DataSourceResponse] = None
