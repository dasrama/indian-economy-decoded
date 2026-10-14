from datetime import date
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.ingestion.base import BaseDownloader, BaseParser, ParsedRecord
from app.ingestion.pipeline import IngestionPipeline
from app.schemas import IndicatorCreate
from app.services import CatalogService


class DummyDownloader(BaseDownloader):
    def __init__(self, content: bytes, file_name: str = "sample.xlsx"):
        self.content = content
        self.file_name = file_name
        self.source_url = "https://rbi.org.in/mock_cpi.xlsx"

    def download(self, target_dir: Path) -> Path:
        target_path = target_dir / self.file_name
        target_path.write_bytes(self.content)
        return target_path


class DummyParser(BaseParser):
    def __init__(self, records: List[ParsedRecord]):
        self.records = records

    def parse(self, file_path: Path) -> List[ParsedRecord]:
        return self.records


def test_ingestion_pipeline_and_deduplication(db_session: Session, tmp_path: Path):
    indicator = CatalogService.create_indicator(
        db_session,
        IndicatorCreate(
            code="UPI_VOL_MONTHLY",
            name="UPI Monthly Volume",
            slug="upi-monthly-volume",
            frequency="MONTHLY",
            units="Million Transactions",
        ),
    )

    file_bytes = b"RBI_SAMPLE_DATA_CONTENT_VERSION_1"
    downloader = DummyDownloader(file_bytes, "upi_sample.csv")
    parser = DummyParser([
        ParsedRecord(observation_date=date(2026, 7, 1), value=14500.2),
        ParsedRecord(observation_date=date(2026, 8, 1), value=15100.8),
    ])

    pipeline = IngestionPipeline(
        db=db_session,
        indicator=indicator,
        downloader=downloader,
        parser=parser,
        storage_base_dir=tmp_path / "data" / "raw",
    )

    # First run: should extract 2, insert 2
    res_1 = pipeline.run(job_type="MANUAL")
    assert res_1.status == "COMPLETED"
    assert res_1.records_extracted == 2
    assert res_1.records_inserted == 2

    # Second run with identical file content: duplicate hash detected -> SKIPPED (FR-6)
    res_2 = pipeline.run(job_type="SCHEDULED")
    assert res_2.status == "SKIPPED"
    assert "Unchanged file detected" in res_2.log_summary
