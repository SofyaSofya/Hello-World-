"""Pure logic tests for the ancestral pattern report -- synthetic planet/house data
chosen by hand so recurring themes and exclusions are verifiable by inspection."""

from app.ancestral import (
    PersonInput,
    aggregate_ancestral_patterns,
    get_ancestral_pattern_houses,
    person_ancestral_placements,
)


def _planet(name: str, house: int, sign: str = "Aries") -> dict:
    return {"name": name, "house": house, "sign": sign}


def test_ancestral_pattern_houses_from_config():
    assert get_ancestral_pattern_houses("western_tropical") == [4, 8, 12]
    assert get_ancestral_pattern_houses("vedic") == [4, 8, 12]


def test_person_ancestral_placements_filters_to_water_houses():
    planets = [_planet("Sun", 1), _planet("Moon", 4), _planet("Saturn", 8), _planet("Mars", 12)]
    placements = person_ancestral_placements(planets, [4, 8, 12])
    assert {p.planet for p in placements} == {"Moon", "Saturn", "Mars"}


def test_planet_recurring_in_ancestral_house_across_people_is_a_theme():
    people = [
        PersonInput(
            name="Grandparent",
            system="western_tropical",
            planets=[_planet("Saturn", 4), _planet("Sun", 1)],
            houses_reliable=True,
        ),
        PersonInput(
            name="Parent",
            system="western_tropical",
            planets=[_planet("Saturn", 8), _planet("Moon", 2)],
            houses_reliable=True,
        ),
    ]
    report = aggregate_ancestral_patterns(people)
    assert len(report.recurring_themes) == 1
    theme = report.recurring_themes[0]
    assert theme.planet == "Saturn"
    assert theme.houses_by_person == {"Grandparent": 4, "Parent": 8}
    assert theme.occurrence_count == 2


def test_planet_in_ancestral_house_for_only_one_person_is_not_a_theme():
    people = [
        PersonInput(
            name="A", system="western_tropical", planets=[_planet("Saturn", 4)], houses_reliable=True
        ),
        PersonInput(
            name="B", system="western_tropical", planets=[_planet("Saturn", 1)], houses_reliable=True
        ),
    ]
    report = aggregate_ancestral_patterns(people)
    assert report.recurring_themes == []


def test_people_without_reliable_houses_are_excluded_not_dropped():
    people = [
        PersonInput(
            name="Known", system="western_tropical", planets=[_planet("Saturn", 4)], houses_reliable=True
        ),
        PersonInput(
            name="Unknown",
            system="western_tropical",
            planets=[_planet("Saturn", 0)],
            houses_reliable=False,
        ),
    ]
    report = aggregate_ancestral_patterns(people)
    assert report.excluded_people == ["Unknown"]
    assert "Unknown" not in report.per_person_placements
    assert "Known" in report.per_person_placements
    # Only one reliable person, so no cross-generational theme even though both
    # nominally have Saturn -- the unreliable one's house placement can't be trusted.
    assert report.recurring_themes == []


def test_house_emphasis_counts_across_family():
    people = [
        PersonInput(
            name="A",
            system="western_tropical",
            planets=[_planet("Sun", 4), _planet("Moon", 4), _planet("Mars", 8)],
            houses_reliable=True,
        ),
        PersonInput(
            name="B",
            system="western_tropical",
            planets=[_planet("Venus", 12)],
            houses_reliable=True,
        ),
    ]
    report = aggregate_ancestral_patterns(people)
    assert report.house_emphasis == {4: 2, 8: 1, 12: 1}
