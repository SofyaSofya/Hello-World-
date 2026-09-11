from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_chart_returns_full_chart():
    resp = client.post(
        "/chart",
        json={
            "birth_date": "1987-02-21",
            "birth_time": "17:00:00",
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["resolved_time"]["resolved_timezone"] == "Europe/Moscow"
    assert body["resolved_time"]["utc_offset_hours"] == 3.0
    assert body["resolved_time"]["utc_datetime"].startswith("1987-02-21T14:00:00")

    assert body["house_system"] == "Placidus"
    assert len(body["house_cusps"]) == 12
    assert len(body["planets"]) == 10

    sun = next(p for p in body["planets"] if p["name"] == "Sun")
    assert sun["sign"] == "Pisces"

    assert isinstance(body["aspects"], list)


def test_post_chart_rejects_invalid_latitude():
    resp = client.post(
        "/chart",
        json={
            "birth_date": "1987-02-21",
            "birth_time": "17:00:00",
            "latitude": 200.0,
            "longitude": 37.6173,
        },
    )
    assert resp.status_code == 422
