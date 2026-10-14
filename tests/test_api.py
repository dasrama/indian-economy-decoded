from fastapi.testclient import TestClient


def test_health_check_and_root(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_status"] == "connected"

    redirect_res = client.get("/", follow_redirects=False)
    assert redirect_res.status_code == 307
    assert redirect_res.headers["location"] == "/docs"


def test_categories_api(client: TestClient):
    payload = {
        "name": "Inflation & Prices",
        "slug": "inflation",
        "description": "Measures of price changes such as CPI and WPI.",
        "display_order": 1,
    }
    # Create
    res = client.post("/api/v1/categories", json=payload)
    assert res.status_code == 201
    cat_id = res.json()["id"]

    # Get
    get_res = client.get(f"/api/v1/categories/{cat_id}")
    assert get_res.status_code == 200
    assert get_res.json()["slug"] == "inflation"

    # List
    list_res = client.get("/api/v1/categories")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["total_pages"] == 1

    # Conflict
    dup_res = client.post("/api/v1/categories", json=payload)
    assert dup_res.status_code == 400


def test_catalog_and_indicators_api(client: TestClient):
    # Setup source and category
    src_res = client.post(
        "/api/v1/sources",
        json={
            "name": "RBI DBIE",
            "code": "RBI_DBIE",
            "base_url": "https://dbie.rbi.org.in",
            "source_type": "EXCEL_DOWNLOAD",
        },
    )
    assert src_res.status_code == 201
    source_id = src_res.json()["id"]

    cat_res = client.post(
        "/api/v1/categories",
        json={"name": "Forex", "slug": "forex", "description": "Foreign exchange rates"},
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["id"]

    # Create indicator
    ind_payload = {
        "category_id": category_id,
        "source_id": source_id,
        "code": "USD_INR_REF",
        "name": "USD to INR Reference Rate",
        "slug": "usd-inr-reference-rate",
        "frequency": "DAILY",
        "units": "INR per USD",
    }
    ind_res = client.post("/api/v1/indicators", json=ind_payload)
    assert ind_res.status_code == 201
    indicator_id = ind_res.json()["id"]

    # Details with joined category and source
    detail_res = client.get(f"/api/v1/indicators/{indicator_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["category"]["slug"] == "forex"
    assert detail_res.json()["source"]["code"] == "RBI_DBIE"

    # Search & Filter
    search_res = client.get("/api/v1/indicators?search=Reference")
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1

    cat_filter_res = client.get(f"/api/v1/indicators?category_id={category_id}")
    assert cat_filter_res.status_code == 200
    assert cat_filter_res.json()["total"] == 1


def test_observations_revisions_and_series_api(client: TestClient):
    ind_res = client.post(
        "/api/v1/indicators",
        json={
            "code": "CPI_HEADLINE",
            "name": "Consumer Price Index (Combined)",
            "slug": "cpi-headline",
            "frequency": "MONTHLY",
            "units": "Index (2012=100)",
        },
    )
    indicator_id = ind_res.json()["id"]

    # 1. Insert initial provisional value
    obs_res_1 = client.post(
        f"/api/v1/indicators/{indicator_id}/observations",
        json={
            "indicator_id": indicator_id,
            "observation_date": "2026-08-01",
            "value": 182.4,
            "is_provisional": True,
            "yoy_change": 4.12,
        },
    )
    assert obs_res_1.status_code == 201

    # 2. Update with revised figure (FR-13)
    obs_res_2 = client.post(
        f"/api/v1/indicators/{indicator_id}/observations?revision_reason=MOSPI_Final",
        json={
            "indicator_id": indicator_id,
            "observation_date": "2026-08-01",
            "value": 182.9,
            "is_provisional": False,
            "yoy_change": 4.38,
        },
    )
    assert obs_res_2.status_code == 201
    assert obs_res_2.json()["is_revised"] is True

    # 3. Check revision audit trail (FR-13)
    rev_res = client.get(f"/api/v1/indicators/{indicator_id}/revisions")
    assert rev_res.status_code == 200
    rev_items = rev_res.json()["items"]
    assert len(rev_items) == 1
    assert rev_items[0]["previous_value"] == 182.4
    assert rev_items[0]["new_value"] == 182.9

    # 4. Insert 2nd month
    client.post(
        f"/api/v1/indicators/{indicator_id}/observations",
        json={
            "indicator_id": indicator_id,
            "observation_date": "2026-09-01",
            "value": 183.5,
        },
    )

    # 5. Chart series endpoint (FR-16)
    series_res = client.get(f"/api/v1/indicators/{indicator_id}/series")
    assert series_res.status_code == 200
    data = series_res.json()
    assert len(data["data_points"]) == 2
    assert data["latest_value"] == 183.5


def test_ingestion_api(client: TestClient):
    jobs_res = client.get("/api/v1/ingestion/jobs")
    assert jobs_res.status_code == 200
    assert "items" in jobs_res.json()

    files_res = client.get("/api/v1/ingestion/raw-files")
    assert files_res.status_code == 200
    assert "items" in files_res.json()
