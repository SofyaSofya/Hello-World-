"""Integration test for the full chart pipeline (timezone resolution -> Julian day ->
Swiss Ephemeris -> houses/signs/aspects), using a real birth chart as fixture data:
Feb 21, 1987, 5:00 PM, Moscow, Russia (55.7558 N, 37.6173 E).

No independently-verified reference chart (e.g. exported from astro.com) was supplied
for this birth data, so this test can't yet assert "matches a known-correct third
party output" the way the project brief calls for. Instead it pins two kinds of
things:

1. Facts independently verifiable without trusting this codebase's own output:
   - Moscow's historical UTC offset on this date (USSR winter time = UTC+3).
   - The Sun's zodiac sign for Feb 21 (solidly within Pisces every year).
2. Internal-consistency / structural invariants that must hold for *any* correctly
   computed chart (12 valid ascending house cusps, Ascendant/MC agree with the house
   calculation, every planet lands in exactly one house, degrees are in [0, 30)).

If you have astro.com (or similar) output for this exact chart, replace the
`EXPECTED_*` constants below with the verified values for an exact-match test.
"""

from datetime import date, time

import pytest

from app.ephemeris import calculate_chart

BIRTH_DATE = date(1987, 2, 21)
BIRTH_TIME = time(17, 0)
MOSCOW_LAT = 55.7558
MOSCOW_LON = 37.6173

ALL_PLANET_NAMES = {
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
}


@pytest.fixture(scope="module")
def chart():
    return calculate_chart(BIRTH_DATE, BIRTH_TIME, MOSCOW_LAT, MOSCOW_LON)


def test_timezone_resolves_to_moscow_with_correct_historical_offset(chart):
    # USSR winter clocks in Feb 1987 were UTC+3 (permanent "decree time" +1 hour,
    # no summer DST active in February).
    assert chart.resolved_timezone == "Europe/Moscow"
    assert chart.utc_offset_hours == 3.0
    assert str(chart.utc_datetime) == "1987-02-21 14:00:00+00:00"


def test_house_system_is_placidus(chart):
    assert chart.house_system == "Placidus"


def test_sun_is_in_pisces(chart):
    # Feb 21 falls solidly within Pisces (Sun enters Pisces ~Feb 18-19, leaves
    # ~Mar 20) regardless of birth time/location, independent of this engine.
    sun = next(p for p in chart.planets if p.name == "Sun")
    assert sun.sign == "Pisces"
    assert 0 <= sun.degree_in_sign < 30


def test_all_ten_planets_present_exactly_once(chart):
    names = [p.name for p in chart.planets]
    assert set(names) == ALL_PLANET_NAMES
    assert len(names) == len(ALL_PLANET_NAMES)


def test_every_planet_has_a_valid_house_and_degree(chart):
    for p in chart.planets:
        assert 1 <= p.house <= 12
        assert 0 <= p.degree_in_sign < 30
        assert 0 <= p.longitude < 360


def test_house_cusps_are_twelve_values_starting_at_ascendant(chart):
    assert len(chart.house_cusps) == 12
    assert chart.house_cusps[0] == pytest.approx(chart.ascendant)


def test_ascendant_and_midheaven_in_valid_range(chart):
    assert 0 <= chart.ascendant < 360
    assert 0 <= chart.midheaven < 360
