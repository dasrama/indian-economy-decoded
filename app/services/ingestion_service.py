from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.ingestion_job import IngestionJob
from app.models.raw_file import RawFile
from app.schemas.ingestion_job import IngestionJobCreate, IngestionJobUpdate
from app.schemas.raw_file import RawFileCreate


class IngestionService:
    # --- Raw Files Management ---

    @staticmethod
    def get_raw_file_by_hash(db: Session, file_hash: str) -> Optional[RawFile]:
        """Detect whether a file with this hash was already downloaded (FR-6)."""
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
        db: Session,
        indicator_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
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

    # --- Ingestion Jobs Management (FR-5, FR-7) ---

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
