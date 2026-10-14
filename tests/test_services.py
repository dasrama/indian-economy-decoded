from datetime import date
from sqlalchemy.orm import Session
from app.schemas import CategoryCreate, CategoryUpdate, DataSourceCreate, IndicatorCreate, ObservationCreate
from app.services import CatalogService, ObservationService


def test_catalog_service_categories(db_session: Session):
    cat_in = CategoryCreate(name="Monetary Policy", slug="monetary-policy", description="Rates and liquidity")
    category = CatalogService.create_category(db_session, cat_in)
    assert category.id is not None
    assert category.slug == "monetary-policy"

    fetched = CatalogService.get_category_by_slug(db_session, "monetary-policy")
    assert fetched.id == category.id

    CatalogService.update_category(db_session, fetched, CategoryUpdate(name="Monetary Policy & Liquidity"))
    assert fetched.name == "Monetary Policy & Liquidity"

    items, total = CatalogService.list_categories(db_session)
    assert total == 1


def test_catalog_service_sources(db_session: Session):
    src_in = DataSourceCreate(
        name="Reserve Bank of India DBIE",
        code="RBI_DBIE",
        base_url="https://dbie.rbi.org.in",
        source_type="EXCEL_DOWNLOAD",
    )
    source = CatalogService.create_source(db_session, src_in)
    assert source.id is not None

    by_code = CatalogService.get_source_by_code(db_session, "RBI_DBIE")
    assert by_code.name == "Reserve Bank of India DBIE"

    items, total = CatalogService.list_sources(db_session)
    assert total == 1


def test_observation_service_and_metrics(db_session: Session):
    ind = CatalogService.create_indicator(
        db_session,
        IndicatorCreate(
            code="REPO_RATE",
            name="Policy Repo Rate",
            slug="repo-rate",
            frequency="MONTHLY",
            units="Percent",
        ),
    )

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

    obs_list, count = ObservationService.get_for_indicator(
        db_session,
        indicator_id=ind.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 3, 1),
    )
    assert count == 2
    assert obs_list[0].observation_date == date(2026, 2, 1)

    refreshed_ind = CatalogService.get_indicator_by_id(db_session, ind.id)
    assert refreshed_ind.latest_value == 6.25
    assert refreshed_ind.latest_observation_date == date(2026, 3, 1)
