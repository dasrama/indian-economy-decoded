from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.category import IndicatorCategory
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    @staticmethod
    def get_by_id(db: Session, category_id: int) -> Optional[IndicatorCategory]:
        return db.get(IndicatorCategory, category_id)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[IndicatorCategory]:
        stmt = select(IndicatorCategory).where(IndicatorCategory.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session, skip: int = 0, limit: int = 50
    ) -> Tuple[List[IndicatorCategory], int]:
        total_stmt = select(func.count(IndicatorCategory.id))
        total = db.execute(total_stmt).scalar() or 0

        stmt = (
            select(IndicatorCategory)
            .order_by(IndicatorCategory.display_order.asc(), IndicatorCategory.name.asc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def create(db: Session, obj_in: CategoryCreate) -> IndicatorCategory:
        category = IndicatorCategory(
            name=obj_in.name,
            slug=obj_in.slug,
            description=obj_in.description,
            display_order=obj_in.display_order,
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def update(
        db: Session, db_obj: IndicatorCategory, obj_in: CategoryUpdate
    ) -> IndicatorCategory:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, db_obj: IndicatorCategory) -> None:
        db.delete(db_obj)
        db.commit()
