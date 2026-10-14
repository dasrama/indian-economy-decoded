# RBI India Economic Indicators Dashboard — Backend API

An enterprise-ready backend designed to ingest, normalize, track revisions, and serve official Reserve Bank of India (RBI) economic indicators (such as CPI Inflation, USD/INR Forex Rates, UPI Volumes, and Monetary Policy metrics) to power public-facing dashboards and reports.

---

## Architecture Overview (Phase 1: Foundation)

```
rbi-india-explained/
├── app/
│   ├── api/                      # API routing and HTTP dependencies
│   │   ├── deps.py               # Database session & pagination dependencies
│   │   └── v1/
│   │       ├── router.py         # Consolidated v1 router
│   │       └── endpoints/
│   │           ├── health.py     # System & database health check (FR-19)
│   │           ├── categories.py # Indicator categories CRUD & listing
│   │           ├── sources.py    # Official RBI data sources registry
│   │           ├── indicators.py # Indicator catalog with search & filters (FR-15, FR-20)
│   │           ├── observations.py # Time series data (FR-16), audit revisions (FR-13)
│   │           └── ingestion.py  # Ingestion jobs & raw file tracking (FR-5, FR-7)
│   ├── core/
│   │   ├── config.py             # Pydantic Settings (SQLite / PostgreSQL dual mode)
│   │   ├── database.py           # Engine & SessionLocal configuration
│   │   └── logging.py            # Structured logging configuration
│   ├── ingestion/
│   │   ├── base.py               # Abstract Base Classes (BaseDownloader, BaseParser)
│   │   └── pipeline.py           # Ingestion pipeline with SHA-256 deduplication (FR-6)
│   ├── models/                   # SQLAlchemy ORM models (Declarative 2.0 style)
│   │   ├── base.py               # Base class & TimestampMixin
│   │   ├── category.py           # indicator_categories table
│   │   ├── data_source.py        # data_sources table
│   │   ├── indicator.py          # indicators table
│   │   ├── raw_file.py           # raw_files table (FR-4, FR-5, FR-6)
│   │   ├── observation.py        # observations table (FR-8, FR-9, FR-11)
│   │   ├── ingestion_job.py      # ingestion_jobs table (FR-3, FR-7)
│   │   └── data_revision.py      # data_revisions table (FR-13)
│   ├── schemas/                  # Pydantic v2 validation models
│   │   ├── category.py           # Category request & response schemas
│   │   ├── common.py             # Pagination, health check, message schemas
│   │   ├── data_revision.py      # Revision tracking schemas
│   │   ├── data_source.py        # Data source schemas
│   │   ├── indicator.py          # Indicator request & response schemas
│   │   ├── ingestion_job.py      # Job tracking schemas
│   │   ├── observation.py        # Observation & chart-ready time series schemas (FR-16)
│   │   └── raw_file.py           # Raw file metadata schemas
│   ├── services/                 # Business logic layer
│   │   ├── category_service.py
│   │   ├── data_source_service.py
│   │   ├── indicator_service.py
│   │   ├── observation_service.py # Revision detection & chart series formatting
│   │   ├── revision_service.py
│   │   └── ingestion_service.py
│   ├── utils/
│   │   ├── hashing.py            # SHA-256 file & content hashing
│   │   └── dates.py              # Flexible date parsing & normalization
│   └── main.py                   # FastAPI application entrypoint & middleware
├── alembic/                      # Database migrations
│   ├── env.py                    # Dual SQLite/Postgres migration configuration
│   └── versions/                 # Version scripts
├── scripts/
│   └── seed_initial_data.py      # Idempotent database seeder
├── tests/                        # Pytest suite with isolated test DB fixtures
├── .env.example                  # Environment configuration template
├── requirements.txt              # Production and development dependencies
└── pytest.ini                    # Pytest test configuration
```

---

## Core Database Schema

The database model is designed to support high-throughput analytical queries and historical revision audits:

| Table | Purpose | Key Columns |
| :--- | :--- | :--- |
| `indicator_categories` | Groups indicators (Inflation, Forex, Payments, etc.) | `id`, `name`, `slug`, `display_order` |
| `data_sources` | Official sources (RBI DBIE, RBI Bulletin, NPCI) | `id`, `code`, `name`, `base_url`, `source_type` |
| `indicators` | Metadata for each tracked metric | `id`, `category_id`, `source_id`, `code`, `slug`, `frequency`, `units`, `latest_value` |
| `raw_files` | Audit log of downloaded files with deduplication (FR-4, FR-5, FR-6) | `id`, `indicator_id`, `source_url`, `file_path`, `file_hash`, `download_timestamp` |
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
By default, `.env` is configured for **SQLite** for instant zero-dependency local development:
```env
DATABASE_URL="sqlite:///./rbi_data.db"
```

To switch to **PostgreSQL** in staging or production, simply set:
```env
DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/rbi_explained"
```

### 3. Run Alembic Migrations
```bash
alembic upgrade head
```

### 4. Seed Initial Data
Populate categories, sources, and MVP indicators (CPI, USD/INR, UPI):
```bash
python scripts/seed_initial_data.py
```

### 5. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** in your browser for the Swagger UI.

### 6. Run Test Suite
```bash
pytest -v
```

---

## Key Functional Requirements Addressed in Foundation

- **FR-4 & FR-5**: Separated raw file storage and metadata tracking in `raw_files` with SHA-256 hashing.
- **FR-6**: Automatic duplicate file detection (`IngestionService.get_raw_file_by_hash`) prevents re-downloading/re-processing unchanged files.
- **FR-7**: Granular job status tracking in `ingestion_jobs` recording extracted, inserted, revised, and skipped counts.
- **FR-11**: Pre-configured schema support for derived metrics (`yoy_change`, `mom_change`, `moving_avg_3m`, `moving_avg_12m`).
- **FR-13**: Revision audit trail in `data_revisions` preserves all previous figures instead of silently overwriting historical data.
- **FR-15 & FR-20**: Standardized filtering and offset pagination across all endpoints.
- **FR-16**: `/indicators/{id}/series` endpoint returns clean chart-ready JSON.
- **FR-19**: `/api/v1/health` verifies API status and active database connectivity.
