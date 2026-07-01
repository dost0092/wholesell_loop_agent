def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["require_human_approval"] is True
    assert "TX" in data["target_states"]
    assert "FL" in data["target_states"]
    assert "Harris" in data["tx_counties"]
    assert "Miami-Dade" in data["fl_counties"]
    assert data["database"] == "ok"
    assert data["phase"] == 5


def test_root_endpoint():
    from fastapi.testclient import TestClient
    from app.main import create_app

    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    if "application/json" in res.headers.get("content-type", ""):
        assert res.json()["phase"] == 5
    else:
        assert "LeadGen" in res.text or "root" in res.text
