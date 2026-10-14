from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.raw_file import RawFile


class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("indicators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("raw_files.id", ondelete="SET NULL"), nullable=True, index=True
    )

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="SCHEDULED")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    records_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    indicator: Mapped[Optional["Indicator"]] = relationship("Indicator", back_populates="ingestion_jobs")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="ingestion_jobs")

    def __repr__(self) -> str:
        return f"<IngestionJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"
