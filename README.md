# RBI India Economic Indicators Dashboard — Backend API

An enterprise-ready backend designed to ingest, normalize, track revisions, and serve official Reserve Bank of India (RBI) economic indicators (such as CPI Inflation, USD/INR Forex Rates, UPI Volumes, and Monetary Policy metrics) to power public-facing dashboards and reports.

---

## Streamlined Architecture

The backend adopts a maintainable, clean layout designed to avoid micro-file sprawl and circular import boilerplate:

```
rbi-india-explained/
├── app/
│   ├── api/
│   │   ├── deps.py               # DB session and pagination dependencies
│   │   └── v1/                   # Clean v1 routers (no redundant nested folders)
│   │       ├── health.py         # System & database health check (FR-19)
│   │       ├── catalog.py        # Categories, Sources & Indicators (FR-15, FR-20)
│   │       ├── observations.py   # Observations, Series (FR-16), Revisions (FR-13)
│   │       ├── ingestion.py      # Ingestion Jobs & Raw Files (FR-5, FR-7)
│   │       └── router.py         # Consolidated API router
│   ├── core/
│   │   ├── config.py             # Dual-engine settings (SQLite & PostgreSQL)
│   │   ├── database.py           # Engine & SessionLocal setup
│   │   └── logging.py            # Structured console logging
│   ├── ingestion/
│   │   ├── base.py               # Downloader & Parser abstract interfaces
│   │   └── pipeline.py           # Ingestion pipeline with deduplication (FR-6)
│   ├── models.py                 # Core SQLAlchemy models (all 7 tables in one place)
│   ├── schemas.py                # Pydantic v2 schemas with PaginatedResponse helper
│   ├── services.py               # CatalogService, ObservationService, IngestionService
│   ├── utils.py                  # SHA-256 hashing & date normalization
│   └── main.py                   # FastAPI app entrypoint with CORS & lifespan hooks
├── alembic/                      # Dual-engine migrations (SQLite & PostgreSQL)
│   └── versions/
├── scripts/
│   └── seed_initial_data.py      # Idempotent seeder for categories, sources & MVP metrics
├── tests/                        # Fast, isolated test suite (11 passing tests)
├── .env.example                  # Environment configuration template
├── requirements.txt              # Project dependencies
└── pytest.ini                    # Pytest test configuration
```

---

## Core Database Schema

| Table | Purpose | Key Columns |
| :--- | :--- | :--- |
| `indicator_categories` | Groups indicators (Inflation, Forex, Payments, etc.) | `id`, `name`, `slug`, `display_order` |
| `data_sources` | Official sources (RBI DBIE, RBI Bulletin, NPCI) | `id`, `code`, `name`, `base_url`, `source_type` |
| `indicators` | Metadata for each tracked metric | `id`, `category_id`, `source_id`, `code`, `slug`, `frequency`, `units`, `latest_value` |
| `raw_files` | Downloaded file audit log with hash deduplication (FR-4, FR-5, FR-6) | `id`, `indicator_id`, `source_url`, `file_path`, `file_hash`, `download_timestamp` |
| `observations` | Cleaned, normalized time-series data points (FR-8, FR-9, FR-11) | `id`, `indicator_id`, `observation_date`, `value`, `yoy_change`, `mom_change`, `status` |
| `data_revisions` | Historical revision preservation (FR-13) | `id`, `indicator_id`, `observation_date`, `previous_value`, `new_value`, `difference` |
| `ingestion_jobs` | Lifecycle tracking of scheduled/manual runs (FR-7) | `id`, `indicator_id`, `job_type`, `status`, `records_extracted`, `records_inserted` |

---

## Quickstart

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Database
By default, `.env` is configured for **SQLite** for zero-dependency local development:
```env
DATABASE_URL="sqlite:///./rbi_data.db"
```
To switch to **PostgreSQL**, update `.env`:
```env
DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/rbi_explained"
```

### 3. Run Alembic Migrations
```bash
alembic upgrade head
```

### 4. Seed Initial Data
```bash
python scripts/seed_initial_data.py
```

### 5. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 6. Run Test Suite
```bash
pytest -v
```
