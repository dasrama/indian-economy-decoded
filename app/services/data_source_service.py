from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate


class DataSourceService:
    @staticmethod
    def get_by_id(db: Session, source_id: int) -> Optional[DataSource]:
        return db.get(DataSource, source_id)

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[DataSource]:
        stmt = select(DataSource).where(DataSource.code == code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session, is_active: Optional[bool] = None, skip: int = 0, limit: int = 50
    ) -> Tuple[List[DataSource], int]:
        filters = []
        if is_active is not None:
            filters.append(DataSource.is_active == is_active)

        total_stmt = select(func.count(DataSource.id))
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        stmt = select(DataSource)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(DataSource.name.asc()).offset(skip).limit(limit)

        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def create(db: Session, obj_in: DataSourceCreate) -> DataSource:
        source = DataSource(
            name=obj_in.name,
            code=obj_in.code,
            base_url=obj_in.base_url,
            description=obj_in.description,
            source_type=obj_in.source_type,
            is_active=obj_in.is_active,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def update(
        db: Session, db_obj: DataSource, obj_in: DataSourceUpdate
    ) -> DataSource:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
