"""Pure logic tests for the family element profile -- synthetic planet/sign data
chosen by hand so weighted totals are verifiable by inspection."""

import pytest

from app.elements import (
    ELEMENTS,
    PersonInput,
    aggregate_family_elements,
    dominant_element,
    element_of_sign,
    person_element_weights,
    weights_to_percentages,
)


@pytest.mark.parametrize(
    "sign, expected_element",
    [
        ("Aries", "Fire"),
        ("Leo", "Fire"),
        ("Sagittarius", "Fire"),
        ("Taurus", "Earth"),
        ("Virgo", "Earth"),
        ("Capricorn", "Earth"),
        ("Gemini", "Air"),
        ("Libra", "Air"),
        ("Aquarius", "Air"),
        ("Cancer", "Water"),
        ("Scorpio", "Water"),
        ("Pisces", "Water"),
    ],
)
def test_element_of_sign(sign, expected_element):
    assert element_of_sign(sign) == expected_element


def _planet(name: str, sign: str) -> dict:
    return {"name": name, "sign": sign}


def test_sun_moon_ascendant_weighted_double():
    # Sun+Moon+Ascendant all Fire (2+2+2=6), the other 8 planets split 4 Earth/4 Air
    # (4 each), so Fire should dominate despite fewer placements.
    planets = (
        [_planet("Sun", "Aries"), _planet("Moon", "Leo")]
        + [_planet(n, "Taurus") for n in ["Mercury", "Venus", "Mars", "Jupiter"]]
        + [_planet(n, "Gemini") for n in ["Saturn", "Uranus", "Neptune", "Pluto"]]
    )
    weights = person_element_weights(planets, ascendant_sign="Sagittarius", houses_reliable=True)
    assert weights["Fire"] == 6.0  # Sun(2) + Moon(2) + Ascendant(2)
    assert weights["Earth"] == 4.0  # 4 planets x weight 1
    assert weights["Air"] == 4.0  # 4 planets x weight 1
    assert dominant_element(weights) == "Fire"


def test_ascendant_excluded_when_houses_unreliable():
    planets = [_planet("Sun", "Cancer"), _planet("Moon", "Cancer")]
    reliable = person_element_weights(planets, ascendant_sign="Aries", houses_reliable=True)
    unreliable = person_element_weights(planets, ascendant_sign="Aries", houses_reliable=False)

    assert reliable["Fire"] == 2.0  # Ascendant (Aries) counted
    assert unreliable["Fire"] == 0.0  # Ascendant excluded entirely
    assert reliable["Water"] == unreliable["Water"] == 4.0  # Sun+Moon unaffected


def test_weights_to_percentages_sums_to_100():
    weights = {"Fire": 3.0, "Earth": 1.0, "Air": 0.0, "Water": 0.0}
    percentages = weights_to_percentages(weights)
    assert sum(percentages.values()) == pytest.approx(100.0)
    assert percentages["Fire"] == 75.0
    assert percentages["Earth"] == 25.0


def test_weights_to_percentages_handles_all_zero():
    percentages = weights_to_percentages({e: 0.0 for e in ELEMENTS})
    assert percentages == {e: 0.0 for e in ELEMENTS}


def test_aggregate_family_elements_combines_people_and_picks_dominant():
    people = [
        PersonInput(
            name="A",
            planets=[_planet("Sun", "Cancer"), _planet("Moon", "Scorpio")],
            ascendant_sign="Pisces",
            houses_reliable=True,
        ),
        PersonInput(
            name="B",
            planets=[_planet("Sun", "Cancer"), _planet("Moon", "Pisces")],
            ascendant_sign="Scorpio",
            houses_reliable=True,
        ),
    ]
    profile = aggregate_family_elements(people)
    assert profile.dominant_element == "Water"
    assert profile.family_percentages["Water"] == 100.0
    assert "Water-dominant" in profile.archetype_summary
    assert set(profile.per_person_percentages) == {"A", "B"}
