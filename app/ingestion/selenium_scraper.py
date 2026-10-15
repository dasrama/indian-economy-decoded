import csv
import io
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterable
import httpx
import openpyxl
from selenium.webdriver.common.by import By
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.ingestion.selenium_driver import create_chrome_driver
from app.models import Indicator
from app.schemas import IngestionJobCreate, ObservationCreate, RawFileCreate
from app.services import CatalogService, IngestionService, ObservationService
from app.utils import calculate_file_hash, parse_flexible_date


class RbiStatisticsScraper:
    """
    Automated collector that navigates RBI Statistics pages using Selenium,
    downloads official statistical files and dynamic tables, and stores them in data/ (FR-2, FR-4).
    """

    STATISTICS_URL = "https://www.rbi.org.in/scripts/statistics.aspx"
    BULLETIN_URL = "https://www.rbi.org.in/scripts/BS_ViewBulletin.aspx"
    REF_RATE_URL = "https://www.rbi.org.in/scripts/BS_DisplayReferenceRate.aspx"
    PAYMENT_DATA_URL = "https://rbidocs.rbi.org.in/rdocs/content/docs/PSDDP04062020.xlsx"

    def __init__(
        self,
        raw_data_dir: Optional[Path] = None,
        processed_data_dir: Optional[Path] = None,
    ):
        self.raw_base_dir = Path(raw_data_dir or settings.RAW_DATA_DIR)
        self.processed_base_dir = Path(processed_data_dir or settings.PROCESSED_DATA_DIR)


    def prepare_directories(self, indicator_slug: str, today: str) -> tuple[Path, Path]:
        raw_dir = self.raw_base_dir / indicator_slug / today
        processed_dir = self.processed_base_dir / indicator_slug

        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        return raw_dir, processed_dir


    @staticmethod
    def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Dict[str, Any]]) -> None:
        """Write CSV records consistently with a header."""
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="raise",)
            writer.writeheader()
            writer.writerows(rows)

    
    # 1. CPI Inflation Statistics

    def collect_cpi_inflation(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Navigates to RBI Statistics -> Bulletin, finds the Consumer Price Index Combined
        publication, downloads the official XLSX file into data/raw/cpi-combined-general/,
        and extracts CPI observations.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        indicator_slug = "cpi-combined-general"
    
        raw_dir, processed_dir = self.prepare_directories(indicator_slug, today)

        logger.info(f"Starting Selenium collection for CPI Inflation into {raw_dir}")
        xlsx_url = None
        page_title = ""

        try:
            with create_chrome_driver(download_dir=raw_dir) as driver:
                driver.get(self.BULLETIN_URL)
                page_title = driver.title

                # Locate CPI Combined link on the bulletin page
                cpi_links = driver.find_elements(
                    By.XPATH, '//a[contains(., "Consumer Price Index") and contains(., "Combined")]'
                )
                if not cpi_links:
                    # Fallback to any CPI link
                    cpi_links = driver.find_elements(By.XPATH, '//a[contains(., "Consumer Price Index")]')

                cpi_page_url = None
                if cpi_links:
                    cpi_page_url = cpi_links[0].get_attribute("href")
                    logger.info(f"Found CPI table page URL: {cpi_page_url}")

                if cpi_page_url:
                    driver.get(cpi_page_url)
                    # Find XLSX download link on the table page
                    excel_elements = driver.find_elements(
                        By.XPATH, '//table[contains(., "Consumer Price Index")]//a[contains(@href, ".XLSX") or contains(@href, ".xls")]'
                    )
                    if not excel_elements:
                        excel_elements = driver.find_elements(By.XPATH, '//a[contains(@href, ".XLSX") or contains(@href, ".xls")]')

                    if excel_elements:
                        xlsx_url = excel_elements[0].get_attribute("href")
                        logger.info(f"Located official CPI XLSX download URL: {xlsx_url}")

            # If Selenium identified the URL, download directly to ensure complete file integrity
            raw_file_path = raw_dir / f"cpi_combined_{today}.xlsx"
            if xlsx_url:
                resp = httpx.get(xlsx_url, timeout=30.0, verify=False, follow_redirects=True)
                raw_file_path.write_bytes(resp.content)
            else:
                # Check if downloaded via browser
                downloaded = list(raw_dir.glob("*.xlsx")) + list(raw_dir.glob("*.xls"))
                if downloaded:
                    raw_file_path = downloaded[0]
                else:
                    raise RuntimeError("Could not locate or download CPI XLSX file from RBI Bulletin")

            file_hash = calculate_file_hash(raw_file_path)
            file_size = raw_file_path.stat().st_size
            logger.info(f"Stored raw CPI file: {raw_file_path} (size={file_size}B, hash={file_hash[:8]})")

            # Parse Excel sheet
            parsed_records = self._parse_cpi_excel(raw_file_path)
            logger.info(f"Extracted {len(parsed_records)} CPI observation records")

            # Save processed CSV in data/processed/cpi-combined-general/
            processed_csv_path = processed_dir / "cpi_series.csv"

            self.write_csv(
                path=processed_csv_path,
                fieldnames=[
                    "date",
                    "value",
                    "yoy_change",
                    "is_provisional",
                ],
                rows=parsed_records
            )

            # Ingest into Database if session provided
            db_stats = {"inserted": 0, "revised": 0, "skipped": 0}
            if db:
                indicator = CatalogService.get_indicator_by_code(db, "CPI_COMBINED_GENERAL")
                if indicator:
                    raw_file = IngestionService.create_raw_file(
                        db,
                        RawFileCreate(
                            source_id=indicator.source_id,
                            indicator_id=indicator.id,
                            source_url=xlsx_url or self.BULLETIN_URL,
                            file_path=str(raw_file_path),
                            file_name=raw_file_path.name,
                            file_format="XLSX",
                            file_size_bytes=file_size,
                            file_hash=file_hash,
                            status="PROCESSED",
                        ),
                    )
                    for rec in parsed_records:
                        obs_in = ObservationCreate(
                            indicator_id=indicator.id,
                            raw_file_id=raw_file.id,
                            observation_date=rec["date"],
                            value=rec["value"],
                            units="Index (2024=100)",
                            yoy_change=rec.get("yoy_change"),
                            is_provisional=rec.get("is_provisional", False),
                        )
                        _, created, revision = ObservationService.upsert_observation(
                            db, obs_in, revision_reason="RBI Bulletin CPI ingestion"
                        )
                        if created:
                            db_stats["inserted"] += 1
                        elif revision:
                            db_stats["revised"] += 1
                        else:
                            db_stats["skipped"] += 1

            return {
                "status": "SUCCESS",
                "indicator": "CPI_COMBINED_GENERAL",
                "raw_file": str(raw_file_path),
                "processed_file": str(processed_csv_path),
                "file_hash": file_hash,
                "records_extracted": len(parsed_records),
                "db_stats": db_stats,
                "latest_record": parsed_records[-1] if parsed_records else None,
            }

        except Exception as exc:
            logger.exception(f"Error during CPI inflation collection: {exc}")
            return {"status": "FAILED", "indicator": "CPI_COMBINED_GENERAL", "error": str(exc)}

    def _parse_cpi_excel(self, file_path: Path) -> List[Dict[str, Any]]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        # Look for the date row (typically row with datetime or month objects)
        date_cols = {}
        for row in rows[:6]:
            for col_idx, cell in enumerate(row):
                if isinstance(cell, datetime):
                    date_cols[col_idx] = cell.date()
                elif isinstance(cell, date):
                    date_cols[col_idx] = cell
                elif isinstance(cell, str) and re.match(r"^[A-Za-z]{3}-\d{2,4}$", cell.strip()):
                    try:
                        date_cols[col_idx] = parse_flexible_date(cell)
                    except Exception:
                        pass

        # Look for General CPI row
        general_row = None
        for row in rows:
            label = str(row[1] or row[0] or "").strip().lower()
            if "general" in label or "all india" in label or "all groups" in label:
                general_row = row
                break

        records = []
        if general_row and date_cols:
            for col_idx, obs_date in sorted(date_cols.items(), key=lambda x: x[1]):
                val = general_row[col_idx]
                if isinstance(val, (int, float)):
                    records.append({
                        "date": obs_date,
                        "value": float(val),
                        "yoy_change": None,
                        "is_provisional": False,
                    })
        return records


    # 2. Forex Reference Rates Statistics 

    def collect_forex_reference_rates(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Navigates to RBI Statistics -> Reference Rates (BS_DisplayReferenceRate.aspx),
        extracts the dynamic ASP.NET table rates for USD, EUR, GBP, JPY,
        and saves raw data into data/raw/usd-inr-reference-rate/.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        indicator_slug = "usd-inr-reference-rate"

        raw_dir, processed_dir = self.prepare_directories(indicator_slug, today)

        logger.info(f"Starting Selenium collection for Forex Reference Rates into {raw_dir}")

        try:
            rates_data = []
            raw_html = ""
            with create_chrome_driver() as driver:
                driver.get(self.REF_RATE_URL)
                raw_html = driver.page_source

                # Find rates in tables
                tables = driver.find_elements(By.TAG_NAME, "table")
                for t in tables:
                    txt = t.text.strip()
                    if "USD" in txt or "US Dollar" in txt or "EUR" in txt:
                        # Extract USD rate pattern: e.g. "US Dollar is ₹ 68.6573 on July 09, 2018" or "83.50"
                        usd_match = re.search(
                            r"US Dollar is ₹\s*([0-9.]+)\s*on\s*([A-Za-z]+ \d{1,2}, \d{4})", txt
                        )
                        if usd_match:
                            val = float(usd_match.group(1))
                            d_str = usd_match.group(2)
                            obs_date = parse_flexible_date(d_str)
                            rates_data.append({"currency": "USD", "date": obs_date, "rate": val})

                        # Extract cross currency quotes
                        for line in txt.split("\n"):
                            parts = line.split()
                            if "EUR" in parts and len(parts) >= 3:
                                try:
                                    rates_data.append({
                                        "currency": "EUR",
                                        "date": rates_data[0]["date"] if rates_data else date.today(),
                                        "rate": float(parts[-1]),
                                    })
                                except Exception:
                                    pass

            # Save raw HTML
            raw_html_path = raw_dir / f"reference_rates_{today}.html"
            raw_html_path.write_text(raw_html, encoding="utf-8")

            # Save raw extracted CSV
            raw_csv_path = raw_dir / f"reference_rates_{today}.csv"

            self.write_csv(
                path=raw_csv_path,
                fieldnames=["currency", "date", "rate"],
                rows=rates_data
            )

            file_hash = calculate_file_hash(raw_csv_path)

            # Save processed CSV for USD/INR
            usd_rates = [r for r in rates_data if r["currency"] == "USD"]

            processed_csv_path = processed_dir / "usd_inr_series.csv"
            self.write_csv(
                path=processed_csv_path,
                fieldnames=["date", "value"],
                rows=[
                    {
                        "date": record["date"],
                        "value": record["rate"],
                    }
                    for record in usd_rates
                ]
            )

            db_stats = {"inserted": 0, "revised": 0, "skipped": 0}
            if db and usd_rates:
                indicator = CatalogService.get_indicator_by_code(db, "USD_INR_REF_RATE")
                if indicator:
                    raw_file = IngestionService.create_raw_file(
                        db,
                        RawFileCreate(
                            source_id=indicator.source_id,
                            indicator_id=indicator.id,
                            source_url=self.REF_RATE_URL,
                            file_path=str(raw_csv_path),
                            file_name=raw_csv_path.name,
                            file_format="CSV",
                            file_size_bytes=raw_csv_path.stat().st_size,
                            file_hash=file_hash,
                            status="PROCESSED",
                        ),
                    )
                    for r in usd_rates:
                        obs_in = ObservationCreate(
                            indicator_id=indicator.id,
                            raw_file_id=raw_file.id,
                            observation_date=r["date"],
                            value=r["rate"],
                            units="INR per USD",
                        )
                        _, created, revision = ObservationService.upsert_observation(
                            db, obs_in, revision_reason="RBI Reference Rate scraping"
                        )
                        if created:
                            db_stats["inserted"] += 1
                        elif revision:
                            db_stats["revised"] += 1
                        else:
                            db_stats["skipped"] += 1

            return {
                "status": "SUCCESS",
                "indicator": "USD_INR_REF_RATE",
                "raw_file": str(raw_csv_path),
                "processed_file": str(processed_csv_path),
                "file_hash": file_hash,
                "rates_found": rates_data,
                "db_stats": db_stats,
            }

        except Exception as exc:
            logger.exception(f"Error during Reference Rate collection: {exc}")
            return {"status": "FAILED", "indicator": "USD_INR_REF_RATE", "error": str(exc)}

    # 3. Payment Systems Statistics 

    def collect_payment_systems(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Navigates to RBI Statistics, downloads payment systems settlement data,
        stores raw file in data/raw/upi-monthly-volume/, and parses transaction figures.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        indicator_slug = "upi-monthly-volume"
    
        raw_dir, processed_dir = self.prepare_directories(indicator_slug, today)


        logger.info(f"Starting Selenium collection for Payment Systems Data into {raw_dir}")

        try:
            # Download settlement data publication
            resp = httpx.get(self.PAYMENT_DATA_URL, timeout=30.0, verify=False, follow_redirects=True)
            raw_file_path = raw_dir / f"payment_settlement_{today}.xlsx"
            raw_file_path.write_bytes(resp.content)

            file_hash = calculate_file_hash(raw_file_path)
            file_size = raw_file_path.stat().st_size
            logger.info(f"Stored raw payment settlement file: {raw_file_path} (size={file_size}B)")

            # Parse payment transactions sheet
            wb = openpyxl.load_workbook(raw_file_path, read_only=True)
            first_sheet = wb[wb.sheetnames[0]]
            records = []
            for i, row in enumerate(first_sheet.iter_rows(values_only=True)):
                if i >= 6 and row[0] and isinstance(row[0], str):
                    try:
                        d = parse_flexible_date(row[0])
                        rtgs_vol = float(row[1]) if isinstance(row[1], (int, float)) else 0.0
                        neft_vol = float(row[3]) if isinstance(row[3], (int, float)) else 0.0
                        records.append({
                            "date": d,
                            "rtgs_volume_lakhs": rtgs_vol,
                            "neft_volume_lakhs": neft_vol,
                            "total_volume_lakhs": rtgs_vol + neft_vol,
                        })
                    except Exception:
                        continue

            # Save processed series
            processed_csv_path = (processed_dir / "payment_systems_series.csv")

            self.write_csv(
                path=processed_csv_path,
                fieldnames=[
                    "date",
                    "rtgs_volume_lakhs",
                    "neft_volume_lakhs",
                    "total_volume_lakhs",
                ],
                rows=records,
            )

            db_stats = {"inserted": 0, "revised": 0, "skipped": 0}
            if db and records:
                indicator = CatalogService.get_indicator_by_code(db, "UPI_MONTHLY_VOLUME")
                if indicator:
                    raw_file = IngestionService.create_raw_file(
                        db,
                        RawFileCreate(
                            source_id=indicator.source_id,
                            indicator_id=indicator.id,
                            source_url=self.PAYMENT_DATA_URL,
                            file_path=str(raw_file_path),
                            file_name=raw_file_path.name,
                            file_format="XLSX",
                            file_size_bytes=file_size,
                            file_hash=file_hash,
                            status="PROCESSED",
                        ),
                    )
                    # Aggregate sample monthly record
                    latest_rec = records[-1]
                    obs_in = ObservationCreate(
                        indicator_id=indicator.id,
                        raw_file_id=raw_file.id,
                        observation_date=latest_rec["date"],
                        value=latest_rec["total_volume_lakhs"],
                        units="Lakh Transactions",
                    )
                    _, created, revision = ObservationService.upsert_observation(
                        db, obs_in, revision_reason="RBI Payment settlement ingestion"
                    )
                    if created:
                        db_stats["inserted"] += 1
                    elif revision:
                        db_stats["revised"] += 1
                    else:
                        db_stats["skipped"] += 1

            return {
                "status": "SUCCESS",
                "indicator": "UPI_MONTHLY_VOLUME",
                "raw_file": str(raw_file_path),
                "processed_file": str(processed_csv_path),
                "file_hash": file_hash,
                "records_extracted": len(records),
                "db_stats": db_stats,
            }

        except Exception as exc:
            logger.exception(f"Error during payment systems collection: {exc}")
            return {"status": "FAILED", "indicator": "UPI_MONTHLY_VOLUME", "error": str(exc)}


    # Orchestrator (FR-3, FR-7)

    # def collect_all(self, db: Optional[Session] = None) -> Dict[str, Any]:
    #     """Run complete Selenium collection for all RBI Statistics modules."""
    #     logger.info("Triggering comprehensive RBI Statistics collection via Selenium")
    #     job = None
    #     if db:
    #         job = IngestionService.create_job(
    #             db,
    #             IngestionJobCreate(
    #                 job_type="SELENIUM_STATISTICS",
    #                 status="RUNNING",
    #                 log_summary="Collecting data through RBI Statistics using Selenium automation",
    #             ),
    #         )

    #     results = {
    #         "cpi": self.collect_cpi_inflation(db),
    #         "forex": self.collect_forex_reference_rates(db),
    #         "payments": self.collect_payment_systems(db),
    #     }

    #     success = all(r.get("status") == "SUCCESS" for r in results.values())
    #     summary_status = "COMPLETED" if success else "PARTIAL"

    #     if db and job:
    #         total_extracted = sum(r.get("records_extracted", 0) for r in results.values())
    #         total_inserted = sum(r.get("db_stats", {}).get("inserted", 0) for r in results.values())
    #         total_updated = sum(r.get("db_stats", {}).get("revised", 0) for r in results.values())
    #         total_skipped = sum(r.get("db_stats", {}).get("skipped", 0) for r in results.values())

    #         IngestionService.finish_job(
    #             db,
    #             job_id=job.id,
    #             status=summary_status,
    #             records_extracted=total_extracted,
    #             records_inserted=total_inserted,
    #             records_updated=total_updated,
    #             records_skipped=total_skipped,
    #             log_summary=f"Selenium statistics collection: {summary_status}",
    #         )

    #     return {
    #         "status": summary_status,
    #         "timestamp": datetime.now(timezone.utc).isoformat(),
    #         "results": results,
    #     }
