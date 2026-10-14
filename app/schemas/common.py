from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    database_status: str = "connected"
    environment: str
    app_name: str
    version: str = "1.0.0"


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number starting from 1")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
