from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    DataSource,
    DataRevision,
    Indicator,
    IndicatorCategory,
    IngestionJob,
    Observation,
    RawFile,
)
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ChartSeriesResponse,
    DataSourceCreate,
    DataSourceUpdate,
    IndicatorCreate,
    IndicatorUpdate,
    IngestionJobCreate,
    ObservationCreate,
    RawFileCreate,
    TimeSeriesPoint,
)


# ===========================================================================
# 1. Catalog Service (Categories, Data Sources, Indicators)
# ===========================================================================

class CatalogService:
    # --- Categories ---
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Optional[IndicatorCategory]:
        return db.get(IndicatorCategory, category_id)

    @staticmethod
    def get_category_by_slug(db: Session, slug: str) -> Optional[IndicatorCategory]:
        stmt = select(IndicatorCategory).where(IndicatorCategory.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_categories(
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
    def create_category(db: Session, obj_in: CategoryCreate) -> IndicatorCategory:
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
    def update_category(
        db: Session, db_obj: IndicatorCategory, obj_in: CategoryUpdate
    ) -> IndicatorCategory:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # --- Data Sources ---
    @staticmethod
    def get_source_by_id(db: Session, source_id: int) -> Optional[DataSource]:
        return db.get(DataSource, source_id)

    @staticmethod
    def get_source_by_code(db: Session, code: str) -> Optional[DataSource]:
        stmt = select(DataSource).where(DataSource.code == code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_sources(
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
    def create_source(db: Session, obj_in: DataSourceCreate) -> DataSource:
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
    def update_source(
        db: Session, db_obj: DataSource, obj_in: DataSourceUpdate
    ) -> DataSource:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # --- Indicators ---
    @staticmethod
    def get_indicator_by_id(db: Session, indicator_id: int) -> Optional[Indicator]:
        return db.get(Indicator, indicator_id)

    @staticmethod
    def get_indicator_by_code(db: Session, code: str) -> Optional[Indicator]:
        stmt = select(Indicator).where(Indicator.code == code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_indicator_by_slug(db: Session, slug: str) -> Optional[Indicator]:
        stmt = select(Indicator).where(Indicator.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_indicator_with_details(db: Session, indicator_id: int) -> Optional[Indicator]:
        stmt = (
            select(Indicator)
            .options(joinedload(Indicator.category), joinedload(Indicator.source))
            .where(Indicator.id == indicator_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_indicators(
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
            pattern = f"%{search.strip()}%"
            filters.append(
                (Indicator.name.ilike(pattern))
                | (Indicator.code.ilike(pattern))
                | (Indicator.description.ilike(pattern))
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
    def create_indicator(db: Session, obj_in: IndicatorCreate) -> Indicator:
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
    def update_indicator(
        db: Session, db_obj: Indicator, obj_in: IndicatorUpdate
    ) -> Indicator:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj


# Backward compatibility aliases
class CategoryService:
    get_by_id = staticmethod(CatalogService.get_category_by_id)
    get_by_slug = staticmethod(CatalogService.get_category_by_slug)
    list = staticmethod(CatalogService.list_categories)
    create = staticmethod(CatalogService.create_category)
    update = staticmethod(CatalogService.update_category)


class DataSourceService:
    get_by_id = staticmethod(CatalogService.get_source_by_id)
    get_by_code = staticmethod(CatalogService.get_source_by_code)
    list = staticmethod(CatalogService.list_sources)
    create = staticmethod(CatalogService.create_source)
    update = staticmethod(CatalogService.update_source)


class IndicatorService:
    get_by_id = staticmethod(CatalogService.get_indicator_by_id)
    get_by_code = staticmethod(CatalogService.get_indicator_by_code)
    get_by_slug = staticmethod(CatalogService.get_indicator_by_slug)
    get_with_details = staticmethod(CatalogService.get_indicator_with_details)
    list = staticmethod(CatalogService.list_indicators)
    create = staticmethod(CatalogService.create_indicator)
    update = staticmethod(CatalogService.update_indicator)


# ===========================================================================
# 2. Observation & Time Series Service (FR-11, FR-13, FR-16)
# ===========================================================================

class ObservationService:
    @staticmethod
    def get_by_id(db: Session, observation_id: int) -> Optional[Observation]:
        return db.get(Observation, observation_id)

    @staticmethod
    def get_for_indicator(
        db: Session,
        indicator_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: str = "ACTIVE",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Observation], int]:
        filters = [Observation.indicator_id == indicator_id]
        if status:
            filters.append(Observation.status == status)
        if start_date:
            filters.append(Observation.observation_date >= start_date)
        if end_date:
            filters.append(Observation.observation_date <= end_date)

        total_stmt = select(func.count(Observation.id)).where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        order_col = (
            Observation.observation_date.asc()
            if sort_order == "asc"
            else Observation.observation_date.desc()
        )
        stmt = (
            select(Observation)
            .where(*filters)
            .order_by(order_col)
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def get_chart_series(
        db: Session,
        indicator_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[ChartSeriesResponse]:
        indicator = db.get(Indicator, indicator_id)
        if not indicator:
            return None

        filters = [
            Observation.indicator_id == indicator_id,
            Observation.status == "ACTIVE",
        ]
        if start_date:
            filters.append(Observation.observation_date >= start_date)
        if end_date:
            filters.append(Observation.observation_date <= end_date)

        stmt = select(Observation).where(*filters).order_by(Observation.observation_date.asc())
        observations = list(db.execute(stmt).scalars().all())

        data_points = [
            TimeSeriesPoint(
                date=obs.observation_date,
                value=obs.value,
                yoy_change=obs.yoy_change,
                mom_change=obs.mom_change,
                moving_avg_3m=obs.moving_avg_3m,
                moving_avg_12m=obs.moving_avg_12m,
                is_provisional=obs.is_provisional,
                is_revised=obs.is_revised,
            )
            for obs in observations
        ]

        return ChartSeriesResponse(
            indicator_id=indicator.id,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            units=indicator.units,
            frequency=indicator.frequency,
            data_points=data_points,
            latest_date=indicator.latest_observation_date,
            latest_value=indicator.latest_value,
        )

    @staticmethod
    def upsert_observation(
        db: Session,
        obj_in: ObservationCreate,
        revision_reason: Optional[str] = None,
    ) -> Tuple[Observation, bool, Optional[DataRevision]]:
        """Upsert observation preserving revision history (FR-13)."""
        stmt = select(Observation).where(
            Observation.indicator_id == obj_in.indicator_id,
            Observation.observation_date == obj_in.observation_date,
            Observation.status == "ACTIVE",
        )
        existing = db.execute(stmt).scalar_one_or_none()

        if existing is None:
            new_obs = Observation(
                indicator_id=obj_in.indicator_id,
                raw_file_id=obj_in.raw_file_id,
                observation_date=obj_in.observation_date,
                value=obj_in.value,
                units=obj_in.units,
                is_provisional=obj_in.is_provisional,
                is_revised=False,
                revision_number=0,
                status="ACTIVE",
                yoy_change=obj_in.yoy_change,
                mom_change=obj_in.mom_change,
                moving_avg_3m=obj_in.moving_avg_3m,
                moving_avg_12m=obj_in.moving_avg_12m,
                metadata_json=obj_in.metadata_json,
            )
            db.add(new_obs)
            db.flush()
            ObservationService._update_indicator_latest(db, obj_in.indicator_id, new_obs)
            db.commit()
            db.refresh(new_obs)
            return new_obs, True, None

        revision = None
        if abs(existing.value - obj_in.value) > 1e-6:
            diff = obj_in.value - existing.value
            pct_change = (diff / existing.value * 100.0) if existing.value != 0 else None

            revision = DataRevision(
                indicator_id=existing.indicator_id,
                observation_id=existing.id,
                raw_file_id=obj_in.raw_file_id,
                observation_date=existing.observation_date,
                previous_value=existing.value,
                new_value=obj_in.value,
                difference=diff,
                percentage_change=pct_change,
                revision_reason=revision_reason or "Updated value from source file",
            )
            db.add(revision)

            existing.value = obj_in.value
            existing.raw_file_id = obj_in.raw_file_id
            existing.is_revised = True
            existing.is_provisional = obj_in.is_provisional
            existing.revision_number += 1
            if obj_in.units:
                existing.units = obj_in.units
            if obj_in.metadata_json:
                existing.metadata_json = obj_in.metadata_json

            ObservationService._update_indicator_latest(db, existing.indicator_id, existing)
            db.commit()
            db.refresh(existing)
            return existing, False, revision

        return existing, False, None

    @staticmethod
    def _update_indicator_latest(db: Session, indicator_id: int, obs: Observation) -> None:
        indicator = db.get(Indicator, indicator_id)
        if indicator:
            if (
                indicator.latest_observation_date is None
                or obs.observation_date >= indicator.latest_observation_date
            ):
                indicator.latest_observation_date = obs.observation_date
                indicator.latest_value = obs.value

    # Integrated revision history query (replaces separate revision_service)
    @staticmethod
    def list_revisions(
        db: Session, indicator_id: int, skip: int = 0, limit: int = 50
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


class RevisionService:
    list_for_indicator = staticmethod(ObservationService.list_revisions)


# ===========================================================================
# 3. Ingestion & Raw Files Service (FR-5, FR-6, FR-7)
# ===========================================================================

class IngestionService:
    @staticmethod
    def get_raw_file_by_hash(db: Session, file_hash: str) -> Optional[RawFile]:
        stmt = select(RawFile).where(RawFile.file_hash == file_hash)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_raw_file(db: Session, obj_in: RawFileCreate) -> RawFile:
        raw_file = RawFile(
            source_id=obj_in.source_id,
            indicator_id=obj_in.indicator_id,
            source_url=obj_in.source_url,
            file_path=obj_in.file_path,
            file_name=obj_in.file_name,
            file_format=obj_in.file_format,
            file_size_bytes=obj_in.file_size_bytes,
            file_hash=obj_in.file_hash,
            status=obj_in.status,
            error_message=obj_in.error_message,
            metadata_json=obj_in.metadata_json,
        )
        db.add(raw_file)
        db.commit()
        db.refresh(raw_file)
        return raw_file

    @staticmethod
    def list_raw_files(
        db: Session, indicator_id: Optional[int] = None, skip: int = 0, limit: int = 50
    ) -> Tuple[List[RawFile], int]:
        filters = []
        if indicator_id is not None:
            filters.append(RawFile.indicator_id == indicator_id)

        total_stmt = select(func.count(RawFile.id))
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        stmt = select(RawFile)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(RawFile.download_timestamp.desc()).offset(skip).limit(limit)

        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def create_job(db: Session, obj_in: IngestionJobCreate) -> IngestionJob:
        job = IngestionJob(
            indicator_id=obj_in.indicator_id,
            raw_file_id=obj_in.raw_file_id,
            job_type=obj_in.job_type,
            status="RUNNING",
            records_extracted=obj_in.records_extracted,
            records_inserted=obj_in.records_inserted,
            records_updated=obj_in.records_updated,
            records_skipped=obj_in.records_skipped,
            error_message=obj_in.error_message,
            log_summary=obj_in.log_summary,
            metadata_json=obj_in.metadata_json,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def finish_job(
        db: Session,
        job_id: int,
        status: str,
        records_extracted: int = 0,
        records_inserted: int = 0,
        records_updated: int = 0,
        records_skipped: int = 0,
        error_message: Optional[str] = None,
        log_summary: Optional[str] = None,
    ) -> Optional[IngestionJob]:
        job = db.get(IngestionJob, job_id)
        if not job:
            return None

        job.status = status
        job.completed_at = datetime.now(timezone.utc)
        job.records_extracted = records_extracted
        job.records_inserted = records_inserted
        job.records_updated = records_updated
        job.records_skipped = records_skipped
        job.error_message = error_message
        job.log_summary = log_summary

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def list_jobs(
        db: Session,
        indicator_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[IngestionJob], int]:
        filters = []
        if indicator_id is not None:
            filters.append(IngestionJob.indicator_id == indicator_id)
        if status is not None:
            filters.append(IngestionJob.status == status)

        total_stmt = select(func.count(IngestionJob.id))
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        stmt = select(IngestionJob)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(IngestionJob.started_at.desc()).offset(skip).limit(limit)

        items = list(db.execute(stmt).scalars().all())
        return items, total


__all__ = [
    "CatalogService",
    "CategoryService",
    "DataSourceService",
    "IndicatorService",
    "ObservationService",
    "RevisionService",
    "IngestionService",
]
