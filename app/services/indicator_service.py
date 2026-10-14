from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.models.indicator import Indicator
from app.schemas.indicator import IndicatorCreate, IndicatorUpdate


class IndicatorService:
    @staticmethod
    def get_by_id(db: Session, indicator_id: int) -> Optional[Indicator]:
        return db.get(Indicator, indicator_id)

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[Indicator]:
        stmt = select(Indicator).where(Indicator.code == code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Indicator]:
        stmt = select(Indicator).where(Indicator.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_with_details(db: Session, indicator_id: int) -> Optional[Indicator]:
        stmt = (
            select(Indicator)
            .options(joinedload(Indicator.category), joinedload(Indicator.source))
            .where(Indicator.id == indicator_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Indicator], int]:
        filters = []
        if category_id is not None:
            filters.append(Indicator.category_id == category_id)
        if is_active is not None:
            filters.append(Indicator.is_active == is_active)
        if search:
            search_pattern = f"%{search.strip()}%"
            filters.append(
                (Indicator.name.ilike(search_pattern))
                | (Indicator.code.ilike(search_pattern))
                | (Indicator.description.ilike(search_pattern))
            )

        total_stmt = select(func.count(Indicator.id))
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        stmt = select(Indicator)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Indicator.name.asc()).offset(skip).limit(limit)

        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def create(db: Session, obj_in: IndicatorCreate) -> Indicator:
        indicator = Indicator(
            category_id=obj_in.category_id,
            source_id=obj_in.source_id,
            code=obj_in.code,
            name=obj_in.name,
            slug=obj_in.slug,
            description=obj_in.description,
            frequency=obj_in.frequency,
            units=obj_in.units,
            is_active=obj_in.is_active,
        )
        db.add(indicator)
        db.commit()
        db.refresh(indicator)
        return indicator

    @staticmethod
    def update(
        db: Session, db_obj: Indicator, obj_in: IndicatorUpdate
    ) -> Indicator:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
