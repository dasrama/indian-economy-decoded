from datetime import date
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.category import IndicatorCategory
    from app.models.data_source import DataSource
    from app.models.observation import Observation
    from app.models.raw_file import RawFile
    from app.models.ingestion_job import IngestionJob
    from app.models.data_revision import DataRevision


class Indicator(Base, TimestampMixin):
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("indicator_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="MONTHLY")
    units: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Denormalized quick-access fields for fast overview queries
    latest_observation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    latest_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    category: Mapped[Optional["IndicatorCategory"]] = relationship("IndicatorCategory", back_populates="indicators")
    source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="indicators")
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="indicator",
        cascade="all, delete-orphan",
        order_by="Observation.observation_date.desc()"
    )
    raw_files: Mapped[List["RawFile"]] = relationship("RawFile", back_populates="indicator")
    ingestion_jobs: Mapped[List["IngestionJob"]] = relationship("IngestionJob", back_populates="indicator")
    revisions: Mapped[List["DataRevision"]] = relationship("DataRevision", back_populates="indicator")

    def __repr__(self) -> str:
        return f"<Indicator(id={self.id}, code='{self.code}', name='{self.name}')>"
