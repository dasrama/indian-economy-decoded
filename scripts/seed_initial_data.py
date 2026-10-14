import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.category import IndicatorCategory
from app.models.data_source import DataSource
from app.models.indicator import Indicator


def seed():
    db = SessionLocal()
    try:
        print("🌱 Seeding initial categories, data sources, and MVP indicators...")

        # 1. Categories
        categories_data = [
            {
                "name": "Inflation & Price Indices",
                "slug": "inflation",
                "description": "Measures of price changes affecting households and businesses, including CPI and WPI.",
                "display_order": 1,
            },
            {
                "name": "Foreign Exchange & External Sector",
                "slug": "forex",
                "description": "Exchange rates (USD/INR, EUR/INR) and foreign exchange reserves.",
                "display_order": 2,
            },
            {
                "name": "Payment & Settlement Systems",
                "slug": "payments",
                "description": "Digital payments volumes and values, including UPI, NEFT, and RTGS.",
                "display_order": 3,
            },
            {
                "name": "Monetary Policy & Interest Rates",
                "slug": "monetary-policy",
                "description": "Policy Repo Rate, Standing Deposit Facility (SDF), and Marginal Standing Facility (MSF).",
                "display_order": 4,
            },
        ]

        category_map = {}
        for cat_info in categories_data:
            cat = db.query(IndicatorCategory).filter_by(slug=cat_info["slug"]).first()
            if not cat:
                cat = IndicatorCategory(**cat_info)
                db.add(cat)
                db.flush()
                print(f"  + Added category: {cat.name}")
            category_map[cat.slug] = cat

        # 2. Data Sources
        sources_data = [
            {
                "name": "RBI DBIE - Database on Indian Economy",
                "code": "RBI_DBIE",
                "base_url": "https://dbie.rbi.org.in",
                "source_type": "EXCEL_DOWNLOAD",
                "description": "Official statistical database of the Reserve Bank of India.",
            },
            {
                "name": "RBI Monthly Bulletin",
                "code": "RBI_BULLETIN",
                "base_url": "https://www.rbi.org.in/scripts/BS_ViewBulletin.aspx",
                "source_type": "EXCEL_DOWNLOAD",
                "description": "Monthly economic and financial data releases published by the RBI.",
            },
            {
                "name": "National Payments Corporation of India (NPCI) / RBI",
                "code": "NPCI_RBI",
                "base_url": "https://www.npci.org.in",
                "source_type": "EXCEL_DOWNLOAD",
                "description": "Payment system indicators and metrics published jointly with RBI.",
            },
        ]

        source_map = {}
        for src_info in sources_data:
            src = db.query(DataSource).filter_by(code=src_info["code"]).first()
            if not src:
                src = DataSource(**src_info)
                db.add(src)
                db.flush()
                print(f"  + Added data source: {src.name}")
            source_map[src.code] = src

        # 3. MVP Indicators (Ready for Phase 2)
        indicators_data = [
            {
                "category_id": category_map["inflation"].id,
                "source_id": source_map["RBI_BULLETIN"].id,
                "code": "CPI_COMBINED_GENERAL",
                "name": "CPI (Combined) - General Index",
                "slug": "cpi-combined-general",
                "description": "All India Consumer Price Index (Base 2012=100) measuring retail inflation across rural and urban India.",
                "frequency": "MONTHLY",
                "units": "Index (2012=100)",
            },
            {
                "category_id": category_map["forex"].id,
                "source_id": source_map["RBI_DBIE"].id,
                "code": "USD_INR_REF_RATE",
                "name": "USD / INR Reference Exchange Rate",
                "slug": "usd-inr-reference-rate",
                "description": "Daily official reference rate for the US Dollar against Indian Rupee.",
                "frequency": "DAILY",
                "units": "INR per USD",
            },
            {
                "category_id": category_map["payments"].id,
                "source_id": source_map["NPCI_RBI"].id,
                "code": "UPI_MONTHLY_VOLUME",
                "name": "UPI Monthly Transaction Volume",
                "slug": "upi-monthly-volume",
                "description": "Total monthly volume of Unified Payments Interface transactions in millions.",
                "frequency": "MONTHLY",
                "units": "Million Transactions",
            },
        ]

        for ind_info in indicators_data:
            ind = db.query(Indicator).filter_by(code=ind_info["code"]).first()
            if not ind:
                ind = Indicator(**ind_info)
                db.add(ind)
                db.flush()
                print(f"  + Added indicator: {ind.name} ({ind.code})")

        db.commit()
        print("✅ Seeding complete!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
