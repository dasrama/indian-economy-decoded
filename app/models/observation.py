from datetime import date
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, Date, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.raw_file import RawFile
    from app.models.data_revision import DataRevision


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

    # Revision & lifecycle tracking (FR-10, FR-13)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_revised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # Derived metrics (FR-11)
    yoy_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mom_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_avg_3m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_avg_12m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="observations")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="observations")
    revisions: Mapped[List["DataRevision"]] = relationship(
        "DataRevision",
        back_populates="observation",
        cascade="all, delete-orphan",
        order_by="DataRevision.created_at.desc()"
    )

    __table_args__ = (
        Index("ix_obs_indicator_date", "indicator_id", "observation_date"),
        Index("ix_obs_indicator_status_date", "indicator_id", "status", "observation_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Observation(id={self.id}, indicator_id={self.indicator_id}, "
            f"date={self.observation_date}, value={self.value})>"
        )
