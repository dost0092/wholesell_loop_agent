"""API integration tests."""

from app.db.models import Lead
from app.services.lead_ingestion import ingest_raw_leads


def test_list_leads_paginated(client, db_session, sample_raw_lead):
    ingest_raw_leads(db_session, [sample_raw_lead])
    res = client.get("/api/leads?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["property_address"] == sample_raw_lead.property_address


def test_get_lead_by_id(client, db_session, sample_raw_lead):
    ingest_raw_leads(db_session, [sample_raw_lead])
    lead_id = db_session.query(Lead).one().id
    res = client.get(f"/api/leads/{lead_id}")
    assert res.status_code == 200
    assert res.json()["id"] == lead_id


def test_get_lead_not_found(client):
    res = client.get("/api/leads/99999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_stats_endpoint(client, db_session, sample_raw_lead):
    ingest_raw_leads(db_session, [sample_raw_lead])
    res = client.get("/api/stats/leads")
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_list_sources_includes_fl():
    from fastapi.testclient import TestClient
    from app.main import create_app

    client = TestClient(create_app())
    res = client.get("/api/sources?state=FL")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    counties = {item["county"] for item in data}
    assert counties == {"Miami-Dade", "Broward", "Hillsborough"}


def test_fetch_fl_endpoint(client, db_session):
    res = client.post("/api/sources/fetch-fl", json={"persist": True})
    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 3
    assert body["total_leads_in_db"] >= 1


def test_health_includes_database(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["database"] in ("ok", "unavailable")
    assert data["phase"] == 5
