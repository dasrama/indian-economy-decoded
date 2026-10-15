import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from app.core.config import settings
from app.core.logging import logger


def find_chrome_binary() -> Optional[str]:
    """Auto-detect Google Chrome or Chromium executable across OS locations."""
    configured = getattr(settings, "CHROME_BINARY_PATH", None)
    if configured and os.path.exists(configured):
        return configured

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    which_chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if which_chrome:
        return which_chrome

    return None


@contextmanager
def create_chrome_driver(
    download_dir: Optional[Path] = None,
    headless: Optional[bool] = None,
    timeout: Optional[int] = None,
) -> Generator[webdriver.Chrome, None, None]:
    """
    Context manager providing a configured headless Selenium Chrome instance.
    Guarantees browser termination and sets custom download directories.
    """
    is_headless = headless if headless is not None else settings.SELENIUM_HEADLESS
    wait_timeout = timeout if timeout is not None else settings.SELENIUM_TIMEOUT

    options = Options()
    if is_headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    chrome_bin = find_chrome_binary()
    if chrome_bin:
        options.binary_location = chrome_bin

    if download_dir:
        download_path = Path(download_dir).resolve()
        download_path.mkdir(parents=True, exist_ok=True)
        prefs = {
            "download.default_directory": str(download_path),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

    logger.info(f"Initializing Selenium Chrome (headless={is_headless}, download_dir={download_dir})")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(wait_timeout)
    driver.implicitly_wait(10)

    # Enable downloads in headless mode via CDP
    if download_dir:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_path)},
        )

    try:
        yield driver
    finally:
        try:
            driver.quit()
            logger.info("Selenium Chrome driver successfully terminated")
        except Exception as e:
            logger.warning(f"Error while quitting driver: {e}")
