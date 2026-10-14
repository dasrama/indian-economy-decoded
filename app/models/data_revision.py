from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.observation import Observation
    from app.models.raw_file import RawFile


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
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="revisions")
    observation: Mapped[Optional["Observation"]] = relationship("Observation", back_populates="revisions")
    raw_file: Mapped[Optional["RawFile"]] = relationship("RawFile", back_populates="revisions")

    def __repr__(self) -> str:
        return (
            f"<DataRevision(id={self.id}, indicator_id={self.indicator_id}, date={self.observation_date}, "
            f"old={self.previous_value}, new={self.new_value})>"
        )
