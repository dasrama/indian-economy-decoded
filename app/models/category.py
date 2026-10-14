from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.indicator import Indicator


class IndicatorCategory(Base, TimestampMixin):
    __tablename__ = "indicator_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    indicators: Mapped[List["Indicator"]] = relationship(
        "Indicator",
        back_populates="category",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<IndicatorCategory(id={self.id}, name='{self.name}', slug='{self.slug}')>"
