"""Tests for the chart-calculation options added after the initial slice: house-system
fallback at high latitude, Vedic mode, manual UTC-offset override, and the
unknown-birth-time (noon) fallback."""

from datetime import date, time

import pytest

from app.ephemeris import DEFAULT_UNKNOWN_BIRTH_TIME, calculate_chart

MOSCOW_LAT, MOSCOW_LON = 55.7558, 37.6173
TROMSO_LAT, TROMSO_LON = 69.6492, 18.9553  # well above the Arctic Circle


def test_placidus_used_by_default_at_ordinary_latitude():
    chart = calculate_chart(date(1987, 2, 21), time(17, 0), MOSCOW_LAT, MOSCOW_LON)
    assert chart.house_system == "Placidus"
    assert chart.house_system_fallback_reason is None


def test_whole_sign_fallback_above_high_latitude_threshold():
    chart = calculate_chart(date(1987, 2, 21), time(12, 0), TROMSO_LAT, TROMSO_LON)
    assert chart.house_system == "Whole Sign"
    assert chart.house_system_fallback_reason is not None
    assert "66" in chart.house_system_fallback_reason

    # Whole Sign cusps must land exactly on 30-degree sign boundaries.
    for cusp in chart.house_cusps:
        assert cusp % 30 == pytest.approx(0.0, abs=1e-6) or cusp % 30 == pytest.approx(
            30.0, abs=1e-6
        )


def test_vedic_system_always_uses_whole_sign_even_at_ordinary_latitude():
    chart = calculate_chart(
        date(1987, 2, 21), time(17, 0), MOSCOW_LAT, MOSCOW_LON, system="vedic"
    )
    assert chart.house_system == "Whole Sign"
    # This is the chosen Vedic convention, not a fallback -- no reason should be given.
    assert chart.house_system_fallback_reason is None


def test_manual_utc_offset_override_bypasses_timezone_autoresolution():
    auto = calculate_chart(date(1987, 2, 21), time(17, 0), MOSCOW_LAT, MOSCOW_LON)
    overridden = calculate_chart(
        date(1987, 2, 21),
        time(17, 0),
        MOSCOW_LAT,
        MOSCOW_LON,
        utc_offset_override=5.0,
    )

    assert overridden.resolved_timezone is None
    assert overridden.utc_offset_hours == 5.0
    # A larger offset means the same local clock time is earlier in UTC.
    assert overridden.utc_datetime < auto.utc_datetime


def test_unknown_birth_time_falls_back_to_noon_and_flags_houses_unreliable():
    chart = calculate_chart(date(1987, 2, 21), None, MOSCOW_LAT, MOSCOW_LON)
    assert chart.houses_reliable is False
    assert all(p.house == 0 for p in chart.planets)

    noon_explicit = calculate_chart(
        date(1987, 2, 21), DEFAULT_UNKNOWN_BIRTH_TIME, MOSCOW_LAT, MOSCOW_LON
    )
    assert chart.utc_datetime == noon_explicit.utc_datetime


def test_known_birth_time_marks_houses_reliable():
    chart = calculate_chart(date(1987, 2, 21), time(17, 0), MOSCOW_LAT, MOSCOW_LON)
    assert chart.houses_reliable is True
    assert all(1 <= p.house <= 12 for p in chart.planets)
