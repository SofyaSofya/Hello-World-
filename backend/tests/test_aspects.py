"""Pure logic tests for aspect detection -- no ephemeris involved, so these pin down
exactly the numbers in family_roles.json's planetary_thread_rules independent of
whether the astronomical computation is correct."""

from app.aspects import angular_separation, find_aspects


def test_angular_separation_handles_wraparound():
    assert angular_separation(10, 350) == 20
    assert angular_separation(350, 10) == 20
    assert angular_separation(0, 180) == 180
    assert angular_separation(45, 45) == 0


def test_exact_conjunction_detected():
    aspects = find_aspects({"Sun": 10.0, "Moon": 10.0})
    types = {a.aspect_type for a in aspects}
    assert "conjunction" in types
    conj = next(a for a in aspects if a.aspect_type == "conjunction")
    assert conj.orb == 0.0


def test_conjunction_orb_boundary_from_family_roles_json():
    # orb_degrees.conjunction == 8 in family_roles.json
    aspects_within = find_aspects({"Sun": 0.0, "Moon": 8.0})
    assert any(a.aspect_type == "conjunction" for a in aspects_within)

    aspects_outside = find_aspects({"Sun": 0.0, "Moon": 8.1})
    assert not any(a.aspect_type == "conjunction" for a in aspects_outside)


def test_square_detected_at_90_degrees():
    aspects = find_aspects({"Mars": 0.0, "Saturn": 90.0})
    assert any(a.aspect_type == "square" for a in aspects)


def test_no_aspect_when_far_from_every_configured_angle():
    # 40 degrees apart doesn't hit conjunction(0), sextile(60), square(90),
    # trine(120), or opposition(180) within any configured orb.
    aspects = find_aspects({"Venus": 0.0, "Jupiter": 40.0})
    assert aspects == []


def test_three_way_comparison_returns_one_entry_per_pair():
    aspects = find_aspects({"Sun": 0.0, "Moon": 0.0, "Mercury": 180.0})
    pairs = {frozenset((a.planet_a, a.planet_b)) for a in aspects}
    assert frozenset({"Sun", "Moon"}) in pairs
    assert frozenset({"Sun", "Mercury"}) in pairs
    assert frozenset({"Moon", "Mercury"}) in pairs
