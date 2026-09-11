"""Pure logic tests for the planetary thread detector -- synthetic longitudes chosen
by hand so each expected thread (or non-thread) is verifiable by inspection."""

from app.threads import detect_threads


def test_shared_square_across_two_people_is_flagged():
    people = {
        "Grandparent": {"Sun": 0.0, "Saturn": 90.0},
        "Parent": {"Sun": 10.0, "Saturn": 100.0},  # same ~90 deg separation
    }
    threads = detect_threads(people)
    assert len(threads) == 1
    thread = threads[0]
    assert {thread.planet_a, thread.planet_b} == {"Sun", "Saturn"}
    assert thread.aspect_type == "square"
    assert set(thread.people) == {"Grandparent", "Parent"}
    assert thread.occurrence_count == 2


def test_aspect_carried_by_only_one_person_is_not_a_thread():
    people = {
        "Grandparent": {"Sun": 0.0, "Saturn": 90.0},
        "Parent": {"Sun": 0.0, "Saturn": 40.0},  # not a configured aspect
    }
    threads = detect_threads(people)
    assert threads == []


def test_generational_planets_excluded_by_default():
    # Pluto is a generational planet -- excluded by default even though this Moon-Pluto
    # square would otherwise be flagged (see test_generational_planets_included_when_requested).
    people = {
        "Grandparent": {"Moon": 0.0, "Pluto": 90.0},
        "Parent": {"Moon": 10.0, "Pluto": 100.0},
    }
    assert detect_threads(people) == []


def test_generational_planets_included_when_requested():
    people = {
        "Grandparent": {"Moon": 0.0, "Pluto": 90.0},
        "Parent": {"Moon": 10.0, "Pluto": 100.0},
    }
    threads = detect_threads(people, include_categories={"personal", "social", "generational"})
    assert len(threads) == 1
    assert {threads[0].planet_a, threads[0].planet_b} == {"Moon", "Pluto"}
    assert threads[0].category == "generational"


def test_thread_category_reflects_slowest_planet_in_pair():
    people = {
        "A": {"Sun": 0.0, "Saturn": 0.0, "Moon": 30.0, "Mercury": 30.0},
        "B": {"Sun": 0.0, "Saturn": 0.0, "Moon": 30.0, "Mercury": 30.0},
    }
    threads = detect_threads(people)
    by_pair = {frozenset((t.planet_a, t.planet_b)): t for t in threads}
    assert by_pair[frozenset({"Sun", "Saturn"})].category == "social"
    assert by_pair[frozenset({"Moon", "Mercury"})].category == "personal"


def test_thread_requires_same_planet_pair_and_aspect_type():
    people = {
        "A": {"Sun": 0.0, "Moon": 90.0},  # Sun-Moon square
        "B": {"Sun": 0.0, "Moon": 120.0},  # Sun-Moon trine -- different aspect type
    }
    threads = detect_threads(people)
    assert threads == []


def test_thread_across_three_people_reports_full_occurrence_count():
    people = {
        "Grandparent": {"Sun": 0.0, "Saturn": 0.0},
        "Parent": {"Sun": 5.0, "Saturn": 3.0},
        "Child": {"Sun": 0.0, "Saturn": 358.0},
    }
    threads = detect_threads(people)
    conjunctions = [t for t in threads if t.aspect_type == "conjunction"]
    assert len(conjunctions) == 1
    assert conjunctions[0].occurrence_count == 3
    assert set(conjunctions[0].people) == {"Grandparent", "Parent", "Child"}


def test_single_person_never_produces_a_thread():
    people = {"OnlyPerson": {"Sun": 0.0, "Moon": 0.0}}
    assert detect_threads(people) == []


def test_multiple_independent_threads_detected_separately():
    # sextile orb is 4 degrees (family_roles.json), so Venus must stay within that
    # of the exact 60-degree sextile angle for both people.
    people = {
        "A": {"Sun": 0.0, "Moon": 0.0, "Venus": 60.0},
        "B": {"Sun": 0.0, "Moon": 0.0, "Venus": 63.0},
    }
    threads = detect_threads(people)
    types_and_pairs = {(frozenset((t.planet_a, t.planet_b)), t.aspect_type) for t in threads}
    assert (frozenset({"Sun", "Moon"}), "conjunction") in types_and_pairs
    assert (frozenset({"Sun", "Venus"}), "sextile") in types_and_pairs
    assert (frozenset({"Moon", "Venus"}), "sextile") in types_and_pairs
