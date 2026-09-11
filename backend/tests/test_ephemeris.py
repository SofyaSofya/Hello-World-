"""Pure math tests for sign/house placement -- verifiable by hand, independent of the
Swiss Ephemeris call itself."""

import pytest

from app.ephemeris import ChartCalculationError, house_of_longitude, longitude_to_sign_degree


@pytest.mark.parametrize(
    "longitude, expected_sign, expected_degree",
    [
        (0.0, "Aries", 0.0),
        (29.9, "Aries", 29.9),
        (30.0, "Taurus", 0.0),
        (2.4, "Aries", 2.4),
        (332.4, "Pisces", 2.4),
        (359.99, "Pisces", 29.99),
        (360.0, "Aries", 0.0),  # wraps
    ],
)
def test_longitude_to_sign_degree(longitude, expected_sign, expected_degree):
    sign, degree = longitude_to_sign_degree(longitude)
    assert sign == expected_sign
    assert degree == pytest.approx(expected_degree, abs=1e-6)


def _evenly_spaced_cusps():
    # A simplified "equal house" cusp set for testing house_of_longitude in isolation:
    # house 1 starts at 0 deg, house 2 at 30 deg, ... house 12 at 330 deg.
    return tuple(i * 30.0 for i in range(12))


def test_house_of_longitude_basic_placement():
    cusps = _evenly_spaced_cusps()
    assert house_of_longitude(0.0, cusps) == 1
    assert house_of_longitude(15.0, cusps) == 1
    assert house_of_longitude(30.0, cusps) == 2
    assert house_of_longitude(345.0, cusps) == 12


def test_house_of_longitude_wraps_past_zero_aries():
    # house 12 cusp at 350, house 1 cusp at 20 -- house 12 wraps through 0 deg Aries
    cusps = (20.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 350.0)
    assert house_of_longitude(0.0, cusps) == 12
    assert house_of_longitude(355.0, cusps) == 12
    assert house_of_longitude(10.0, cusps) == 12
    assert house_of_longitude(20.0, cusps) == 1
