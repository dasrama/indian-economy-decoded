from datetime import date
from sqlalchemy.orm import Session
from app.models.category import IndicatorCategory
from app.models.data_source import DataSource
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate
from app.schemas.indicator import IndicatorCreate
from app.schemas.observation import ObservationCreate
from app.services.category_service import CategoryService
from app.services.data_source_service import DataSourceService
from app.services.indicator_service import IndicatorService
from app.services.observation_service import ObservationService
from app.services.ingestion_service import IngestionService


def test_category_service(db_session: Session):
    cat_in = CategoryCreate(name="Monetary Policy", slug="monetary-policy", description="Rates and liquidity")
    category = CategoryService.create(db_session, cat_in)
    assert category.id is not None
    assert category.slug == "monetary-policy"

    fetched = CategoryService.get_by_slug(db_session, "monetary-policy")
    assert fetched.id == category.id

    CategoryService.update(db_session, fetched, CategoryUpdate(name="Monetary Policy & Liquidity"))
    assert fetched.name == "Monetary Policy & Liquidity"

    items, total = CategoryService.list(db_session)
    assert total == 1


def test_data_source_service(db_session: Session):
    src_in = DataSourceCreate(
        name="Reserve Bank of India DBIE",
        code="RBI_DBIE",
        base_url="https://dbie.rbi.org.in",
        source_type="EXCEL_DOWNLOAD"
    )
    source = DataSourceService.create(db_session, src_in)
    assert source.id is not None

    by_code = DataSourceService.get_by_code(db_session, "RBI_DBIE")
    assert by_code.name == "Reserve Bank of India DBIE"

    items, total = DataSourceService.list(db_session)
    assert total == 1


def test_observation_service_range_and_metrics(db_session: Session):
    ind = IndicatorService.create(
        db_session,
        IndicatorCreate(
            code="REPO_RATE",
            name="Policy Repo Rate",
            slug="repo-rate",
            frequency="MONTHLY",
            units="Percent",
        ),
    )

    # Insert 3 observations across dates
    dates_values = [
        (date(2026, 1, 1), 6.50),
        (date(2026, 2, 1), 6.50),
        (date(2026, 3, 1), 6.25),
    ]
    for d, val in dates_values:
        ObservationService.upsert_observation(
            db_session,
            ObservationCreate(indicator_id=ind.id, observation_date=d, value=val)
        )

    # Filter with date range
    obs_list, count = ObservationService.get_for_indicator(
        db_session,
        indicator_id=ind.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 3, 1),
    )
    assert count == 2
    assert obs_list[0].observation_date == date(2026, 2, 1)

    # Verify latest value denormalization
    refreshed_ind = IndicatorService.get_by_id(db_session, ind.id)
    assert refreshed_ind.latest_value == 6.25
    assert refreshed_ind.latest_observation_date == date(2026, 3, 1)
