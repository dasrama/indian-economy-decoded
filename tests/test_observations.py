from fastapi.testclient import TestClient


def test_observation_upsert_and_revisions(client: TestClient):
    # Setup indicator
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
    assert ind_res.status_code == 201
    indicator_id = ind_res.json()["id"]

    # 1. Insert initial provisional observation
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
    obs_data = obs_res_1.json()
    assert obs_data["value"] == 182.4
    assert obs_data["is_provisional"] is True

    # Check indicator latest value updated
    ind_check = client.get(f"/api/v1/indicators/{indicator_id}")
    assert ind_check.json()["latest_value"] == 182.4

    # 2. Update with revised final value (FR-13: Preserve historical revisions)
    obs_res_2 = client.post(
        f"/api/v1/indicators/{indicator_id}/observations?revision_reason=MOSPI_Final_Release",
        json={
            "indicator_id": indicator_id,
            "observation_date": "2026-08-01",
            "value": 182.9,
            "is_provisional": False,
            "yoy_change": 4.38,
        },
    )
    assert obs_res_2.status_code == 201
    revised_data = obs_res_2.json()
    assert revised_data["value"] == 182.9
    assert revised_data["is_revised"] is True
    assert revised_data["revision_number"] == 1

    # 3. Verify revision audit log has the old value and difference
    rev_res = client.get(f"/api/v1/indicators/{indicator_id}/revisions")
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["total"] == 1
    revision_item = rev_data["items"][0]
    assert revision_item["previous_value"] == 182.4
    assert revision_item["new_value"] == 182.9
    assert revision_item["revision_reason"] == "MOSPI_Final_Release"
    assert round(revision_item["difference"], 2) == 0.50

    # 4. Insert another month for chart series
    client.post(
        f"/api/v1/indicators/{indicator_id}/observations",
        json={
            "indicator_id": indicator_id,
            "observation_date": "2026-09-01",
            "value": 183.5,
            "yoy_change": 4.45,
        },
    )

    # 5. Query Chart Series endpoint (FR-16)
    series_res = client.get(f"/api/v1/indicators/{indicator_id}/series")
    assert series_res.status_code == 200
    series = series_res.json()
    assert series["indicator_code"] == "CPI_HEADLINE"
    assert len(series["data_points"]) == 2
    assert series["data_points"][0]["date"] == "2026-08-01"
    assert series["data_points"][1]["date"] == "2026-09-01"
    assert series["latest_value"] == 183.5
