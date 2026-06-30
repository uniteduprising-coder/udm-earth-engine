from fastapi.testclient import TestClient

from earth.main import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "udm-earth-engine"