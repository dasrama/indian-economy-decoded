from fastapi.testclient import TestClient


def test_create_and_query_indicator(client: TestClient):
    # Setup source and category first
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
        json={
            "name": "Forex",
            "slug": "forex",
            "description": "Foreign exchange rates",
        },
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["id"]

    # Create Indicator
    ind_payload = {
        "category_id": category_id,
        "source_id": source_id,
        "code": "USD_INR_REF",
        "name": "USD to INR Reference Rate",
        "slug": "usd-inr-reference-rate",
        "description": "Daily reference exchange rate for USD/INR published by FBIL/RBI",
        "frequency": "DAILY",
        "units": "INR per USD",
        "is_active": True,
    }
    ind_res = client.post("/api/v1/indicators", json=ind_payload)
    assert ind_res.status_code == 201
    indicator = ind_res.json()
    assert indicator["code"] == "USD_INR_REF"
    indicator_id = indicator["id"]

    # Get Indicator Details
    detail_res = client.get(f"/api/v1/indicators/{indicator_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["category"]["slug"] == "forex"
    assert detail_data["source"]["code"] == "RBI_DBIE"

    # Search Indicator
    search_res = client.get("/api/v1/indicators?search=Reference")
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1

    # Filter by category
    filter_res = client.get(f"/api/v1/indicators?category_id={category_id}")
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] == 1
