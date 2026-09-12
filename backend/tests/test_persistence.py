"""Tests for the persisted family tree (Step 3): POST /people computes and stores a
chart, POST /relationships links people, and POST /threads runs the same
detect_threads() pure function against stored charts instead of raw birth data."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

GRANDPARENT = {
    "name": "Grandparent",
    "birth_date": "1955-06-10",
    "birth_time": "08:30:00",
    "latitude": 55.7558,
    "longitude": 37.6173,
}
PARENT = {
    "name": "Parent",
    "birth_date": "1987-02-21",
    "birth_time": "17:00:00",
    "latitude": 55.7558,
    "longitude": 37.6173,
}


def _create_person(payload: dict) -> dict:
    resp = client.post("/people", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_person_computes_and_persists_chart(db_session):
    body = _create_person(PARENT)
    assert body["name"] == "Parent"
    assert body["id"] is not None
    assert body["chart"]["house_system"] == "Placidus"
    sun = next(p for p in body["chart"]["planets"] if p["name"] == "Sun")
    assert sun["sign"] == "Pisces"


def test_get_person_returns_the_same_chart(db_session):
    created = _create_person(PARENT)
    resp = client.get(f"/people/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == created


def test_get_person_404_for_unknown_id(db_session):
    resp = client.get("/people/999999")
    assert resp.status_code == 404


def test_list_people_includes_created_people(db_session):
    _create_person(GRANDPARENT)
    _create_person(PARENT)
    resp = client.get("/people")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {"Grandparent", "Parent"}


def test_create_relationship_defaults_generation_offset_by_type(db_session):
    grandparent = _create_person(GRANDPARENT)
    parent = _create_person(PARENT)

    resp = client.post(
        "/relationships",
        json={
            "person_a_id": grandparent["id"],
            "person_b_id": parent["id"],
            "relationship_type": "parent",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["generation_offset"] == 1

    listed = client.get("/relationships").json()
    assert len(listed) == 1
    assert listed[0]["relationship_type"] == "parent"


def test_create_relationship_rejects_self_relationship(db_session):
    person = _create_person(PARENT)
    resp = client.post(
        "/relationships",
        json={
            "person_a_id": person["id"],
            "person_b_id": person["id"],
            "relationship_type": "sibling",
        },
    )
    assert resp.status_code == 422


def test_create_relationship_rejects_unknown_person(db_session):
    person = _create_person(PARENT)
    resp = client.post(
        "/relationships",
        json={
            "person_a_id": person["id"],
            "person_b_id": 999999,
            "relationship_type": "spouse",
        },
    )
    assert resp.status_code == 422


def test_persisted_threads_excludes_generational_by_default(db_session):
    _create_person(GRANDPARENT)
    _create_person(PARENT)

    resp = client.post("/threads", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["people"] == ["Grandparent", "Parent"]
    # These two charts' only shared aspect is a generational-planet (Neptune-Pluto)
    # thread, verified via direct detect_threads() computation -- excluded by default.
    assert body["threads"] == []


def test_persisted_threads_includes_generational_when_requested(db_session):
    _create_person(GRANDPARENT)
    _create_person(PARENT)

    resp = client.post("/threads", json={"include_generational_planets": True})
    assert resp.status_code == 200
    threads = resp.json()["threads"]
    assert len(threads) == 1
    assert {threads[0]["planet_a"], threads[0]["planet_b"]} == {"Neptune", "Pluto"}
    assert threads[0]["category"] == "generational"


def test_persisted_threads_requires_at_least_two_people(db_session):
    _create_person(PARENT)
    resp = client.post("/threads", json={})
    assert resp.status_code == 422


def test_family_elements_requires_at_least_one_person(db_session):
    resp = client.get("/family/elements")
    assert resp.status_code == 422


def test_family_elements_aggregates_persisted_people(db_session):
    _create_person(GRANDPARENT)
    _create_person(PARENT)

    resp = client.get("/family/elements")
    assert resp.status_code == 200
    body = resp.json()

    assert set(body["family_percentages"]) == {"Fire", "Earth", "Air", "Water"}
    assert sum(body["family_percentages"].values()) == pytest.approx(100.0)
    assert body["dominant_element"] in {"Fire", "Earth", "Air", "Water"}
    assert body["archetype_summary"]

    per_person_names = {p["person"] for p in body["per_person"]}
    assert per_person_names == {"Grandparent", "Parent"}
    for p in body["per_person"]:
        assert sum(p["percentages"].values()) == pytest.approx(100.0)
