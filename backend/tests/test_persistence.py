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


def test_family_ancestral_patterns_requires_at_least_one_person(db_session):
    resp = client.get("/family/ancestral-patterns")
    assert resp.status_code == 422


def test_family_ancestral_patterns_finds_recurring_jupiter_and_saturn(db_session):
    # Verified via direct calculate_chart(): Grandparent has Jupiter(house 12) and
    # Saturn(house 4) in water houses; Parent has Jupiter(house 8) and Saturn(house
    # 4) -- both planets recur across the two, a real cross-generational theme.
    _create_person(GRANDPARENT)
    _create_person(PARENT)

    resp = client.get("/family/ancestral-patterns")
    assert resp.status_code == 200
    body = resp.json()

    assert body["ancestral_houses_by_system"] == {"western_tropical": [4, 8, 12]}
    assert body["excluded_people"] == []
    assert body["house_emphasis"] == {"4": 4, "8": 2, "12": 2}

    themes_by_planet = {t["planet"]: t for t in body["recurring_themes"]}
    assert set(themes_by_planet) == {"Jupiter", "Saturn"}
    assert themes_by_planet["Jupiter"]["houses_by_person"] == {
        "Grandparent": 12,
        "Parent": 8,
    }
    assert themes_by_planet["Saturn"]["houses_by_person"] == {
        "Grandparent": 4,
        "Parent": 4,
    }
    assert themes_by_planet["Saturn"]["occurrence_count"] == 2


def test_family_ancestral_patterns_excludes_unreliable_houses(db_session):
    _create_person(PARENT)
    _create_person(
        {
            "name": "UnknownBirthTime",
            "birth_date": "1930-01-01",
            "latitude": 55.7558,
            "longitude": 37.6173,
        }
    )

    resp = client.get("/family/ancestral-patterns")
    assert resp.status_code == 200
    body = resp.json()
    assert body["excluded_people"] == ["UnknownBirthTime"]
    assert {p["person"] for p in body["per_person"]} == {"Parent"}


def test_family_generational_cohorts_requires_at_least_one_person(db_session):
    resp = client.get("/family/generational-cohorts")
    assert resp.status_code == 422


def test_family_generational_cohorts_splits_grandparent_and_parent(db_session):
    # Verified via direct calculate_chart(): 32 years apart is enough that
    # Grandparent and Parent land in different signs for all three outer planets --
    # Uranus (Cancer vs Sagittarius), Neptune (Libra vs Capricorn), Pluto (Leo vs
    # Scorpio) -- so each planet should show 2 singleton cohorts.
    _create_person(GRANDPARENT)
    _create_person(PARENT)

    resp = client.get("/family/generational-cohorts")
    assert resp.status_code == 200
    body = resp.json()

    by_planet = {pc["planet"]: pc for pc in body["cohorts_by_planet"]}
    assert set(by_planet) == {"Uranus", "Neptune", "Pluto"}

    expected_signs = {
        "Uranus": {"Grandparent": "Cancer", "Parent": "Sagittarius"},
        "Neptune": {"Grandparent": "Libra", "Parent": "Capricorn"},
        "Pluto": {"Grandparent": "Leo", "Parent": "Scorpio"},
    }
    for planet, expected in expected_signs.items():
        pc = by_planet[planet]
        assert pc["distinct_cohort_count"] == 2
        actual = {person: c["sign"] for c in pc["cohorts"] for person in c["people"]}
        assert actual == expected


def test_create_life_event_computes_age_and_persists(db_session):
    person = _create_person(PARENT)  # born 1987-02-21

    resp = client.post(
        "/life-events",
        json={
            "person_id": person["id"],
            "event_type": "marriage",
            "event_date": "2015-06-01",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["person_name"] == "Parent"
    assert body["age_at_event"] == 28  # birthday Feb 21 already passed by June 1

    listed = client.get("/life-events").json()
    assert len(listed) == 1
    assert listed[0]["age_at_event"] == 28


def test_create_life_event_rejects_invalid_event_type(db_session):
    person = _create_person(PARENT)
    resp = client.post(
        "/life-events",
        json={"person_id": person["id"], "event_type": "not_a_real_type", "event_date": "2015-06-01"},
    )
    assert resp.status_code == 422


def test_create_life_event_rejects_date_before_birth(db_session):
    person = _create_person(PARENT)  # born 1987-02-21
    resp = client.post(
        "/life-events",
        json={"person_id": person["id"], "event_type": "other", "event_date": "1980-01-01"},
    )
    assert resp.status_code == 422


def test_create_life_event_rejects_unknown_person(db_session):
    resp = client.post(
        "/life-events",
        json={"person_id": 999999, "event_type": "other", "event_date": "2000-01-01"},
    )
    assert resp.status_code == 422


def test_family_timeline_detects_cross_generational_timing_pattern(db_session):
    grandparent = _create_person(GRANDPARENT)  # born 1955-06-10
    parent = _create_person(PARENT)  # born 1987-02-21

    # Both marry at age 24: Grandparent on/after their 24th birthday in 1979,
    # Parent on/after their 24th birthday in 2011.
    client.post(
        "/life-events",
        json={"person_id": grandparent["id"], "event_type": "marriage", "event_date": "1979-07-01"},
    )
    client.post(
        "/life-events",
        json={"person_id": parent["id"], "event_type": "marriage", "event_date": "2011-03-01"},
    )
    # A non-matching event for Parent, to confirm it doesn't get swept into the pattern.
    client.post(
        "/life-events",
        json={"person_id": parent["id"], "event_type": "career_change", "event_date": "2020-01-01"},
    )

    resp = client.get("/family/timeline")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["events"]) == 3
    assert [e["event_date"] for e in body["events"]] == ["1979-07-01", "2011-03-01", "2020-01-01"]

    assert len(body["timing_patterns"]) == 1
    pattern = body["timing_patterns"][0]
    assert pattern["event_type"] == "marriage"
    assert pattern["age_at_event"] == 24
    assert set(pattern["people"]) == {"Grandparent", "Parent"}
