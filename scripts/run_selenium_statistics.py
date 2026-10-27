import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from app.config.database import SessionLocal
from app.ingestion.selenium_scraper import RbiStatisticsScraper

def main():
    parser = argparse.ArgumentParser(
        description="RBI Statistics Selenium Data Collector — Automates downloading and storing official data."
    )
    parser.add_argument(
        "--indicator",
        choices=["all", "cpi", "forex", "payments"],
        default="all",
        help="Indicator to scrape and ingest (default: all)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Download and store in data/ only without updating the database",
    )
    args = parser.parse_args()

    db = None if args.no_db else SessionLocal()
    scraper = RbiStatisticsScraper()

    print(f"\nRunning Selenium Statistics Collection (Target: {args.indicator.upper()})...\n")

    try:
        if args.indicator == "cpi":
            res = scraper.collect_cpi_inflation(db)
            print(f"CPI Result: {res}")
        elif args.indicator == "forex":
            res = scraper.collect_forex_reference_rates(db)
            print(f"Forex Result: {res}")
        elif args.indicator == "payments":
            res = scraper.collect_payment_systems(db)
            print(f"Payment Systems Result: {res}")
        # else:
        #     res = scraper.collect_all(db)
        #     print("\n Aggregated Collection Results:")
        #     for module, details in res.get("results", {}).items():
        #         print(f"  • {module.upper()}: status={details.get('status')}")
        #         if "raw_file" in details:
        #             print(f"    Raw file: {details['raw_file']}")
        #         if "processed_file" in details:
        #             print(f"    Processed file: {details['processed_file']}")
        #     print(f"\nOverall Status: {res.get('status')}")

    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
