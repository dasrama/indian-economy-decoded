from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.ingestion.base import BaseDownloader, BaseParser, ParsedRecord
from app.models.indicator import Indicator
from app.schemas.ingestion_job import IngestionJobCreate
from app.schemas.observation import ObservationCreate
from app.schemas.raw_file import RawFileCreate
from app.services.ingestion_service import IngestionService
from app.services.observation_service import ObservationService
from app.utils.hashing import calculate_file_hash


@dataclass
class IngestionResult:
    status: str
    records_extracted: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: Optional[str] = None
    log_summary: Optional[str] = None


class IngestionPipeline:
    """
    Coordinates raw file download, duplicate checking via SHA-256 (FR-6),
    parsing (FR-8), and upserting into the database with revision tracking (FR-13).
    """

    def __init__(
        self,
        db: Session,
        indicator: Indicator,
        downloader: BaseDownloader,
        parser: BaseParser,
        storage_base_dir: Path,
    ):
        self.db = db
        self.indicator = indicator
        self.downloader = downloader
        self.parser = parser
        self.storage_base_dir = storage_base_dir

    def run(self, job_type: str = "SCHEDULED") -> IngestionResult:
        logger.info(f"Starting ingestion pipeline for indicator '{self.indicator.code}'")

        # 1. Start job tracking
        job_in = IngestionJobCreate(
            indicator_id=self.indicator.id,
            job_type=job_type,
            status="RUNNING",
        )
        job = IngestionService.create_job(self.db, job_in)

        try:
            # 2. Download file to raw storage
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            target_dir = self.storage_base_dir / self.indicator.slug / today_str
            target_dir.mkdir(parents=True, exist_ok=True)

            downloaded_file = self.downloader.download(target_dir)
            file_hash = calculate_file_hash(downloaded_file)
            file_size = downloaded_file.stat().st_size

            # 3. Duplicate check (FR-6)
            existing_file = IngestionService.get_raw_file_by_hash(self.db, file_hash)
            if existing_file:
                logger.info(f"File with hash {file_hash[:8]} already processed. Skipping.")
                result = IngestionResult(
                    status="SKIPPED",
                    log_summary=f"Unchanged file detected (hash: {file_hash[:8]}). Pipeline skipped duplicate.",
                )
                IngestionService.finish_job(
                    self.db,
                    job_id=job.id,
                    status=result.status,
                    log_summary=result.log_summary,
                )
                return result

            # 4. Record new raw file
            raw_file_in = RawFileCreate(
                source_id=self.indicator.source_id,
                indicator_id=self.indicator.id,
                source_url=getattr(self.downloader, "source_url", "direct_download"),
                file_path=str(downloaded_file),
                file_name=downloaded_file.name,
                file_format=downloaded_file.suffix.replace(".", "").upper(),
                file_size_bytes=file_size,
                file_hash=file_hash,
                status="DOWNLOADED",
            )
            raw_file = IngestionService.create_raw_file(self.db, raw_file_in)

            # Link raw file to job
            job.raw_file_id = raw_file.id
            self.db.commit()

            # 5. Parse file
            records: List[ParsedRecord] = self.parser.parse(downloaded_file)
            extracted_count = len(records)
            inserted_count = 0
            updated_count = 0
            skipped_count = 0

            # 6. Upsert observations with revision tracking (FR-13)
            for rec in records:
                obs_in = ObservationCreate(
                    indicator_id=self.indicator.id,
                    raw_file_id=raw_file.id,
                    observation_date=rec.observation_date,
                    value=rec.value,
                    units=rec.units or self.indicator.units,
                    is_provisional=rec.is_provisional,
                    metadata_json=rec.metadata_json,
                )
                _, is_created, revision = ObservationService.upsert_observation(
                    self.db, obs_in, revision_reason="Data ingestion pipeline refresh"
                )
                if is_created:
                    inserted_count += 1
                elif revision is not None:
                    updated_count += 1
                else:
                    skipped_count += 1

            # Mark raw file as PROCESSED
            raw_file.status = "PROCESSED"
            self.db.commit()

            result = IngestionResult(
                status="COMPLETED",
                records_extracted=extracted_count,
                records_inserted=inserted_count,
                records_updated=updated_count,
                records_skipped=skipped_count,
                log_summary=(
                    f"Successfully ingested {extracted_count} records: "
                    f"{inserted_count} new, {updated_count} revised, {skipped_count} unchanged."
                ),
            )

            IngestionService.finish_job(
                self.db,
                job_id=job.id,
                status=result.status,
                records_extracted=result.records_extracted,
                records_inserted=result.records_inserted,
                records_updated=result.records_updated,
                records_skipped=result.records_skipped,
                log_summary=result.log_summary,
            )
            return result

        except Exception as exc:
            logger.exception(f"Ingestion pipeline failed: {exc}")
            result = IngestionResult(
                status="FAILED",
                error_message=str(exc),
            )
            IngestionService.finish_job(
                self.db,
                job_id=job.id,
                status=result.status,
                error_message=result.error_message,
            )
            return result
