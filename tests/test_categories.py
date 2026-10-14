from fastapi.testclient import TestClient


def test_create_and_list_categories(client: TestClient):
    # 1. Create a category
    payload = {
        "name": "Inflation & Prices",
        "slug": "inflation",
        "description": "Measures of price changes such as CPI and WPI.",
        "display_order": 1,
    }
    response = client.post("/api/v1/categories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Inflation & Prices"
    assert data["slug"] == "inflation"
    category_id = data["id"]

    # 2. Get category by ID
    get_res = client.get(f"/api/v1/categories/{category_id}")
    assert get_res.status_code == 200
    assert get_res.json()["slug"] == "inflation"

    # 3. List categories
    list_res = client.get("/api/v1/categories")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1

    # 4. Duplicate slug should be rejected
    dup_res = client.post("/api/v1/categories", json=payload)
    assert dup_res.status_code == 400
