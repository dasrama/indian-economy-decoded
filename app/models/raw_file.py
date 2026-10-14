from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.indicator import Indicator
    from app.models.observation import Observation
    from app.models.ingestion_job import IngestionJob
    from app.models.data_revision import DataRevision


class RawFile(Base, TimestampMixin):
    __tablename__ = "raw_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    indicator_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("indicators.id", ondelete="SET NULL"), nullable=True, index=True
    )

    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False, default="XLSX")
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    download_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DOWNLOADED")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="raw_files")
    indicator: Mapped[Optional["Indicator"]] = relationship("Indicator", back_populates="raw_files")
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="raw_file")
    ingestion_jobs: Mapped[List["IngestionJob"]] = relationship("IngestionJob", back_populates="raw_file")
    revisions: Mapped[List["DataRevision"]] = relationship("DataRevision", back_populates="raw_file")

    def __repr__(self) -> str:
        return f"<RawFile(id={self.id}, file_name='{self.file_name}', hash='{self.file_hash[:8]}...', status='{self.status}')>"
