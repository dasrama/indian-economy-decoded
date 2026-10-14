from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TimestampMixin:
    """Adds created_at and updated_at timestamps to models."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


# ---------------------------------------------------------------------------
# Catalog Entities (Categories, Sources, Indicators)
# ---------------------------------------------------------------------------

class IndicatorCategory(Base, TimestampMixin):
    __tablename__ = "indicator_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    indicators: Mapped[List["Indicator"]] = relationship(
        "Indicator", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<IndicatorCategory(id={self.id}, slug='{self.slug}')>"


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="EXCEL_DOWNLOAD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    indicators: Mapped[List["Indicator"]] = relationship("Indicator", back_populates="source")
    raw_files: Mapped[List["RawFile"]] = relationship("RawFile", back_populates="source")

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, code='{self.code}')>"


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

    latest_observation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    latest_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    category: Mapped[Optional["IndicatorCategory"]] = relationship("IndicatorCategory", back_populates="indicators")
    source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="indicators")
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="indicator",
        cascade="all, delete-orphan",
        order_by="Observation.observation_date.desc()",
    )
    raw_files: Mapped[List["RawFile"]] = relationship("RawFile", back_populates="indicator")
    ingestion_jobs: Mapped[List["IngestionJob"]] = relationship("IngestionJob", back_populates="indicator")
    revisions: Mapped[List["DataRevision"]] = relationship("DataRevision", back_populates="indicator")

    def __repr__(self) -> str:
        return f"<Indicator(id={self.id}, code='{self.code}')>"


# ---------------------------------------------------------------------------
# Ingestion & Raw Files (FR-4, FR-5, FR-6, FR-7)
# ---------------------------------------------------------------------------

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DOWNLOADED")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="raw_files")
    indicator: Mapped[Optional["Indicator"]] = relationship("Indicator", back_populates="raw_files")
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="raw_file")
    ingestion_jobs: Mapped[List["IngestionJob"]] = relationship("IngestionJob", back_populates="raw_file")
    revisions: Mapped[List["DataRevision"]] = relationship("DataRevision", back_populates="raw_file")

    def __repr__(self) -> str:
        return f"<RawFile(id={self.id}, file_name='{self.file_name}', status='{self.status}')>"


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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    records_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    indicator: Mapped[Optional["Indicator"]] = relationship("Indicator", back_populates="ingestion_jobs")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="ingestion_jobs")

    def __repr__(self) -> str:
        return f"<IngestionJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"


# ---------------------------------------------------------------------------
# Observations & Historical Revisions (FR-8, FR-9, FR-11, FR-13)
# ---------------------------------------------------------------------------

class Observation(Base, TimestampMixin):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    indicator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("raw_files.id", ondelete="SET NULL"), nullable=True, index=True
    )

    observation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    units: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_revised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    yoy_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mom_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_avg_3m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_avg_12m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="observations")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="observations")
    revisions: Mapped[List["DataRevision"]] = relationship(
        "DataRevision",
        back_populates="observation",
        cascade="all, delete-orphan",
        order_by="DataRevision.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_obs_indicator_date", "indicator_id", "observation_date"),
        Index("ix_obs_indicator_status_date", "indicator_id", "status", "observation_date"),
    )

    def __repr__(self) -> str:
        return f"<Observation(id={self.id}, ind={self.indicator_id}, date={self.observation_date}, val={self.value})>"


class DataRevision(Base, TimestampMixin):
    __tablename__ = "data_revisions"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    indicator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    observation_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("observations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("raw_files.id", ondelete="SET NULL"), nullable=True
    )

    observation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    previous_value: Mapped[float] = mapped_column(Float, nullable=False)
    new_value: Mapped[float] = mapped_column(Float, nullable=False)
    difference: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentage_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    revision_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    revision_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="revisions")
    observation: Mapped[Optional["Observation"]] = relationship("Observation", back_populates="revisions")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="revisions")

    def __repr__(self) -> str:
        return f"<DataRevision(id={self.id}, ind={self.indicator_id}, old={self.previous_value}, new={self.new_value})>"


__all__ = [
    "Base",
    "TimestampMixin",
    "IndicatorCategory",
    "DataSource",
    "Indicator",
    "RawFile",
    "IngestionJob",
    "Observation",
    "DataRevision",
]
