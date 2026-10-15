from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.ingestion.selenium_driver import find_chrome_binary
from app.ingestion.selenium_scraper import RbiStatisticsScraper


def test_find_chrome_binary():
    bin_path = find_chrome_binary()
    assert bin_path is not None
    assert "Chrome" in bin_path or "chromium" in bin_path


def test_selenium_scraper_dirs(tmp_path: Path):
    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    scraper = RbiStatisticsScraper(raw_data_dir=raw_dir, processed_data_dir=proc_dir)
    assert scraper.raw_base_dir == raw_dir
    assert scraper.processed_base_dir == proc_dir


def test_trigger_selenium_endpoint_validation(client: TestClient):
    # Invalid indicator should be rejected by regex validator
    res = client.post("/api/v1/ingestion/trigger-selenium?indicator=invalid_metric")
    assert res.status_code == 422


def test_trigger_selenium_endpoint_mocked(client: TestClient):
    with patch.object(
        RbiStatisticsScraper,
        "collect_all",
        return_value={"status": "COMPLETED", "results": {"cpi": {"status": "SUCCESS"}}},
    ):
        res = client.post("/api/v1/ingestion/trigger-selenium?indicator=all")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
