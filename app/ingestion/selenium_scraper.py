import csv
import io
import re
import shutil
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterable
import httpx
import openpyxl
from selenium.webdriver.common.by import By
from sqlalchemy.orm import Session

from app.config.config import settings
from app.config.logging import logger
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
    CPI_FALLBACK_URL = "https://rbidocs.rbi.org.in/rdocs/Bulletin/DOCs/19CT_BULL25092026E12A0853D84E44ED82754B6BF48796CD.XLSX"

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

    def _discover_cpi_xlsx_url(self, driver) -> Optional[str]:
        """
        Locates the official CPI Table 19(c) Excel download URL from RBI Bulletin.
        Handles both current releases and navigates the archive tree if the current month
        has only published PDF tables so far.
        """
        def find_in_rows() -> tuple[Optional[str], Optional[str]]:
            """Returns (direct_xlsx_url, table_page_url) from current page rows."""
            xpath_expr = (
                '//tr[contains(., "Consumer Price Index") and '
                '(contains(., "Combined") or contains(., "19 (c)") or contains(., "19(c)"))]'
            )
            rows = driver.find_elements(By.XPATH, xpath_expr)
            if not rows:
                rows = driver.find_elements(By.XPATH, '//tr[contains(., "Consumer Price Index")]')

            direct_xlsx = None
            page_url = None

            for row in rows:
                for a in row.find_elements(By.TAG_NAME, "a"):
                    href = a.get_attribute("href") or ""
                    href_lower = href.lower()
                    if ".xlsx" in href_lower or ".xls" in href_lower:
                        return href, None
                    if "bs_viewbulletin.aspx?id=" in href_lower and not page_url:
                        page_url = href

            return direct_xlsx, page_url

        # 1. Try finding in the default active view
        direct_url, page_url = find_in_rows()
        if direct_url:
            return direct_url

        # 2. If no direct XLSX in current view (e.g. initial PDF-only release), check archive
        now = datetime.now(timezone.utc)
        archive_months: List[tuple[int, int]] = []
        for m in range(now.month - 1, 0, -1):
            archive_months.append((now.year, m))
        for m in range(12, max(0, 12 - 3), -1):
            archive_months.append((now.year - 1, m))

        for y, m in archive_months[:4]:
            try:
                logger.info(f"Checking RBI Bulletin archive for {y}-{m:02d} for published Excel tables...")
                driver.execute_script('GetYearMonth(arguments[0], arguments[1]);', str(y), str(m))
                time.sleep(2.0)
                d_url, p_url = find_in_rows()
                if d_url:
                    logger.info(f"Located official CPI XLSX in {y}-{m:02d} bulletin: {d_url}")
                    return d_url
                if p_url and not page_url:
                    page_url = p_url
            except Exception as e:
                logger.warning(f"Error checking archive {y}-{m:02d}: {e}")

        # 3. If a table page URL was located, navigate to it and find the XLSX download link
        if page_url:
            try:
                logger.info(f"Navigating to CPI table page: {page_url}")
                driver.get(page_url)
                excel_elements = driver.find_elements(
                    By.XPATH, '//a[contains(@href, ".xlsx") or contains(@href, ".XLSX") or contains(@href, ".xls")]'
                )
                if excel_elements:
                    discovered = excel_elements[0].get_attribute("href")
                    logger.info(f"Discovered official CPI XLSX on table page: {discovered}")
                    return discovered
            except Exception as e:
                logger.warning(f"Error navigating table page {page_url}: {e}")

        return None

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

        try:
            with create_chrome_driver(download_dir=raw_dir) as driver:
                driver.get(self.BULLETIN_URL)
                xlsx_url = self._discover_cpi_xlsx_url(driver)

            raw_file_path = raw_dir / f"cpi_combined_{today}.xlsx"

            # Strategy 1: Download from Selenium-discovered official URL
            download_success = False
            if xlsx_url:
                try:
                    logger.info(f"Downloading official CPI XLSX from discovered URL: {xlsx_url}")
                    resp = httpx.get(xlsx_url, timeout=30.0, verify=False, follow_redirects=True)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        raw_file_path.write_bytes(resp.content)
                        download_success = True
                except Exception as dl_err:
                    logger.warning(f"Failed to download from discovered URL {xlsx_url}: {dl_err}")

            # Strategy 2: Check if browser downloaded any xlsx into download_dir
            if not download_success:
                downloaded = list(raw_dir.glob("*.xlsx")) + list(raw_dir.glob("*.xls"))
                if downloaded and downloaded[0].stat().st_size > 1000:
                    raw_file_path = downloaded[0]
                    download_success = True

            # Strategy 3: Use official reliable fallback publication URL
            if not download_success and self.CPI_FALLBACK_URL:
                try:
                    logger.info(f"Attempting download via official RBI fallback publication URL: {self.CPI_FALLBACK_URL}")
                    resp = httpx.get(self.CPI_FALLBACK_URL, timeout=30.0, verify=False, follow_redirects=True)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        raw_file_path.write_bytes(resp.content)
                        xlsx_url = self.CPI_FALLBACK_URL
                        download_success = True
                except Exception as fb_err:
                    logger.warning(f"Fallback download failed: {fb_err}")

            # Strategy 4: If offline or download blocked, use most recent cached raw file
            if not download_success:
                cached_files = sorted(
                    list((self.raw_base_dir / indicator_slug).glob("*/*.xlsx")),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if cached_files and cached_files[0] != raw_file_path and cached_files[0].stat().st_size > 1000:
                    logger.info(f"Reusing latest validated raw CPI file: {cached_files[0]}")
                    shutil.copy2(cached_files[0], raw_file_path)
                    download_success = True

            if not download_success or not raw_file_path.exists():
                raise RuntimeError("Could not locate or download CPI XLSX file from RBI Bulletin")

            file_hash = calculate_file_hash(raw_file_path)
            file_size = raw_file_path.stat().st_size
            logger.info(f"Stored raw CPI file: {raw_file_path} (size={file_size}B, hash={file_hash[:8]})")

            # Parse Excel sheet
            cpi_data = self._parse_cpi_full(raw_file_path)
            parsed_records = cpi_data["headline"]
            logger.info(f"Extracted {len(parsed_records)} headline CPI observation records")

            # Save headline processed CSV in data/processed/cpi-combined-general/
            processed_csv_path = processed_dir / "cpi_series.csv"
            self.write_csv(
                path=processed_csv_path,
                fieldnames=[
                    "date",
                    "value",
                    "yoy_change",
                    "is_provisional",
                ],
                rows=parsed_records,
            )

            # Save detailed component division breakdown
            if cpi_data.get("components"):
                components_csv_path = processed_dir / "cpi_components.csv"
                self.write_csv(
                    path=components_csv_path,
                    fieldnames=[
                        "Division",
                        "Weight",
                        "Date",
                        "Index Value",
                        "YoY Inflation",
                        "Provisional",
                    ],
                    rows=cpi_data["components"],
                )

            # Save full summary matrix table
            if cpi_data.get("summary"):
                summary_csv_path = processed_dir / "cpi_summary.csv"
                summary_fieldnames = list(cpi_data["summary"][0].keys())
                self.write_csv(
                    path=summary_csv_path,
                    fieldnames=summary_fieldnames,
                    rows=cpi_data["summary"],
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
        """Backwards-compatible wrapper returning headline General CPI records."""
        return self._parse_cpi_full(file_path)["headline"]

    def _parse_cpi_full(self, file_path: Path) -> Dict[str, Any]:
        """
        Parses RBI Table 19(c) Excel file:
        - Extracts headline All India General CPI time series with index values and YoY changes.
        - Extracts all individual division components (Food & beverages, Core CPI, etc.).
        - Prepares a tabular summary matrix matching RBI Bulletin layout.
        """
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        def parse_date_cell(cell_val: Any) -> tuple[Optional[date], bool]:
            if isinstance(cell_val, (datetime, date)):
                return date(cell_val.year, cell_val.month, 1), False
            if isinstance(cell_val, str):
                val = cell_val.strip()
                is_prov = "(P)" in val or "(p)" in val or "provisional" in val.lower()
                cleaned = re.sub(r"\s*\([Pp]\)\s*", "", val).strip()
                m = re.match(r"^([A-Za-z]{3})[-/](\d{2,4})$", cleaned)
                if m:
                    mon_str, yr_str = m.groups()
                    yr = int(yr_str)
                    if yr < 100:
                        yr += 2000
                    mon = datetime.strptime(mon_str, "%b").month
                    return date(yr, mon, 1), is_prov
            return None, False

        row_header_top = rows[2] if len(rows) > 2 else []
        row_header_dates = rows[3] if len(rows) > 3 else []

        index_col_start = None
        inflation_col_start = None
        for col_idx, cell in enumerate(row_header_top):
            c_str = str(cell or "").lower()
            if "index" in c_str and index_col_start is None:
                index_col_start = col_idx
            elif "inflation" in c_str and inflation_col_start is None:
                inflation_col_start = col_idx

        index_dates: Dict[int, tuple[date, bool]] = {}
        for col_idx in range(index_col_start or 3, inflation_col_start or 8):
            if col_idx < len(row_header_dates):
                d, is_prov = parse_date_cell(row_header_dates[col_idx])
                if d:
                    index_dates[col_idx] = (d, is_prov)

        inflation_dates: Dict[int, tuple[date, bool]] = {}
        for col_idx in range(inflation_col_start or 8, len(row_header_dates)):
            d, is_prov = parse_date_cell(row_header_dates[col_idx])
            if d:
                inflation_dates[col_idx] = (d, is_prov)

        inflation_date_to_col = {d: c for c, (d, _) in inflation_dates.items()}

        headline_records: List[Dict[str, Any]] = []
        components_records: List[Dict[str, Any]] = []
        summary_rows: List[Dict[str, Any]] = []
        date_col_list = sorted(index_dates.items(), key=lambda x: x[1][0])

        for row in rows[4:]:
            label_cell = row[1] if len(row) > 1 else None
            weight_cell = row[2] if len(row) > 2 else None
            if not label_cell or not isinstance(label_cell, str):
                continue
            label = label_cell.strip()
            if not isinstance(weight_cell, (int, float)):
                continue

            weight = float(weight_cell)
            fy_avg = float(row[3]) if len(row) > 3 and isinstance(row[3], (int, float)) else None

            summary_item: Dict[str, Any] = {
                "Division": label,
                "Weight": weight,
                "FY 2025-26 Avg": fy_avg,
            }

            division_series = []
            for col_idx, (obs_date, is_prov) in date_col_list:
                val = float(row[col_idx]) if col_idx < len(row) and isinstance(row[col_idx], (int, float)) else None
                inf_col = inflation_date_to_col.get(obs_date)
                inf_val = float(row[inf_col]) if inf_col is not None and inf_col < len(row) and isinstance(row[inf_col], (int, float)) else None

                date_label = obs_date.strftime("%b %Y") + (" (P)" if is_prov else "")
                summary_item[f"Index {date_label}"] = val
                if inf_val is not None:
                    summary_item[f"YoY Inflation {date_label}"] = inf_val

                rec = {
                    "Division": label,
                    "Weight": weight,
                    "Date": obs_date,
                    "Index Value": val,
                    "YoY Inflation": inf_val,
                    "Provisional": is_prov,
                }
                division_series.append(rec)
                components_records.append(rec)

            summary_rows.append(summary_item)

            if "general" in label.lower() or "all india general" in label.lower():
                for item in division_series:
                    if item["Index Value"] is not None:
                        headline_records.append({
                            "date": item["Date"],
                            "value": item["Index Value"],
                            "yoy_change": item["YoY Inflation"],
                            "is_provisional": item["Provisional"],
                        })

        # Fallback calculation if yoy_change not populated
        by_date = {r["date"]: r for r in headline_records}
        for rec in headline_records:
            if rec["yoy_change"] is None:
                try:
                    prior_date = date(rec["date"].year - 1, rec["date"].month, 1)
                    if prior_date in by_date and by_date[prior_date]["value"]:
                        rec["yoy_change"] = round(
                            (rec["value"] - by_date[prior_date]["value"]) / by_date[prior_date]["value"] * 100.0,
                            2,
                        )
                except Exception:
                    pass

        return {
            "headline": headline_records,
            "components": components_records,
            "summary": summary_rows,
        }


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

    def collect_all(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Run complete Selenium collection for all RBI Statistics modules."""
        logger.info("Triggering comprehensive RBI Statistics collection via Selenium")
        job = None
        if db:
            job = IngestionService.create_job(
                db,
                IngestionJobCreate(
                    job_type="SELENIUM_STATISTICS",
                    status="RUNNING",
                    log_summary="Collecting data through RBI Statistics using Selenium automation",
                ),
            )

        results = {
            "cpi": self.collect_cpi_inflation(db),
            "forex": self.collect_forex_reference_rates(db),
            "payments": self.collect_payment_systems(db),
        }

        success = all(r.get("status") == "SUCCESS" for r in results.values())
        summary_status = "COMPLETED" if success else "PARTIAL"

        if db and job:
            total_extracted = sum(r.get("records_extracted", 0) for r in results.values())
            total_inserted = sum(r.get("db_stats", {}).get("inserted", 0) for r in results.values())
            total_updated = sum(r.get("db_stats", {}).get("revised", 0) for r in results.values())
            total_skipped = sum(r.get("db_stats", {}).get("skipped", 0) for r in results.values())

            IngestionService.finish_job(
                db,
                job_id=job.id,
                status=summary_status,
                records_extracted=total_extracted,
                records_inserted=total_inserted,
                records_updated=total_updated,
                records_skipped=total_skipped,
                log_summary=f"Selenium statistics collection: {summary_status}",
            )

        return {
            "status": summary_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
