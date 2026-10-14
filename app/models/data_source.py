from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.raw_file import RawFile


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="EXCEL_DOWNLOAD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    indicators: Mapped[List["Indicator"]] = relationship("Indicator", back_populates="source")
    raw_files: Mapped[List["RawFile"]] = relationship("RawFile", back_populates="source")

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, code='{self.code}', name='{self.name}')>"
