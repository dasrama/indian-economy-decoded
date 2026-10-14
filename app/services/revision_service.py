from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.data_revision import DataRevision


class RevisionService:
    @staticmethod
    def list_for_indicator(
        db: Session,
        indicator_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DataRevision], int]:
        filters = [DataRevision.indicator_id == indicator_id]
        total_stmt = select(func.count(DataRevision.id)).where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        stmt = (
            select(DataRevision)
            .where(*filters)
            .order_by(DataRevision.revision_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total
