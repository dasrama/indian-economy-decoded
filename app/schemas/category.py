from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100, description="Display name of category")
    slug: str = Field(..., max_length=100, description="URL-friendly slug (e.g. inflation, forex)")
    description: Optional[str] = Field(None, description="Plain-English summary of category")
    display_order: int = Field(default=0, description="Sorting order in navigation")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
