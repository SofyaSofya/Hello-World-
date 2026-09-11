"""Birth chart calculation via the Swiss Ephemeris (pyswisseph).

Uses the Moshier semi-analytical model (SEFLG_MOSEPH) rather than the
high-precision JPL/Swiss ephemeris files, since Moshier needs no external data
files and is accurate to ~1 arcsecond over years -3000..3000 -- plenty for
astrology use.

House system: Placidus by default, auto-fallback to Whole Sign above ~66 degrees
latitude (Placidus is mathematically undefined near the poles -- some dates/times
fail even slightly below that, so a Placidus calculation error also triggers the
same fallback). Vedic mode always uses Whole Sign, matching Jyotish convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Literal

import swisseph as swe

from app.timezone_utils import resolve_utc_datetime

PLANETS: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

AstrologicalSystem = Literal["western_tropical", "vedic"]

HIGH_LATITUDE_THRESHOLD = 66.0  # degrees; Placidus is undefined near the poles
DEFAULT_UNKNOWN_BIRTH_TIME = time(12, 0, 0)  # noon convention when time is unknown

_CALC_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


class ChartCalculationError(ValueError):
    pass


def longitude_to_sign_degree(longitude: float) -> tuple[str, float]:
    longitude = longitude % 360
    sign_index = int(longitude // 30)
    degree_in_sign = longitude - sign_index * 30
    return SIGNS[sign_index], degree_in_sign


def house_of_longitude(longitude: float, cusps: tuple[float, ...]) -> int:
    """cusps is 12 values, index 0 = house 1 cusp ... index 11 = house 12 cusp."""
    longitude = longitude % 360
    for house_num in range(1, 13):
        start = cusps[house_num - 1] % 360
        end = cusps[house_num % 12] % 360
        if start <= end:
            if start <= longitude < end:
                return house_num
        else:  # house wraps past 0 degrees Aries
            if longitude >= start or longitude < end:
                return house_num
    raise ChartCalculationError(f"Could not place longitude {longitude} into any house")


def _compute_houses(
    jd_ut: float, lat: float, lon: float, system: AstrologicalSystem
) -> tuple[tuple[float, ...], tuple[float, ...], str, str | None]:
    """Returns (cusps, ascmc, house_system_label, fallback_reason)."""
    if system == "vedic":
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b"W")
        return cusps, ascmc, "Whole Sign", None

    if abs(lat) > HIGH_LATITUDE_THRESHOLD:
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b"W")
        return (
            cusps,
            ascmc,
            "Whole Sign",
            f"Placidus is undefined above ~{HIGH_LATITUDE_THRESHOLD:g} degrees "
            "latitude; used Whole Sign instead.",
        )

    try:
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b"P")
        return cusps, ascmc, "Placidus", None
    except swe.Error:
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b"W")
        return (
            cusps,
            ascmc,
            "Whole Sign",
            "Placidus calculation failed for this date/location (near-polar "
            "sidereal geometry); used Whole Sign instead.",
        )


@dataclass
class PlanetPosition:
    name: str
    longitude: float
    sign: str
    degree_in_sign: float
    house: int
    retrograde: bool


@dataclass
class ChartResult:
    utc_datetime: datetime
    resolved_timezone: str | None
    utc_offset_hours: float
    julian_day_ut: float
    house_system: str
    house_system_fallback_reason: str | None
    house_cusps: list[float]
    ascendant: float
    midheaven: float
    houses_reliable: bool
    planets: list[PlanetPosition] = field(default_factory=list)


def calculate_chart(
    birth_date: date,
    birth_time: time | None,
    lat: float,
    lon: float,
    system: AstrologicalSystem = "western_tropical",
    utc_offset_override: float | None = None,
) -> ChartResult:
    if not (-90 <= lat <= 90):
        raise ChartCalculationError("Latitude must be between -90 and 90 degrees")
    if not (-180 <= lon <= 180):
        raise ChartCalculationError("Longitude must be between -180 and 180 degrees")

    houses_reliable = birth_time is not None
    effective_birth_time = birth_time if birth_time is not None else DEFAULT_UNKNOWN_BIRTH_TIME

    utc_dt, tz_name, offset_hours = resolve_utc_datetime(
        birth_date, effective_birth_time, lat, lon, utc_offset_override
    )

    hour_decimal = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal)

    cusps, ascmc, house_system_label, fallback_reason = _compute_houses(jd_ut, lat, lon, system)

    planets: list[PlanetPosition] = []
    for name, body_code in PLANETS.items():
        (lon_deg, _lat_deg, _dist, lon_speed, _lat_speed, _dist_speed), _flags = (
            swe.calc_ut(jd_ut, body_code, _CALC_FLAGS)
        )
        sign, degree_in_sign = longitude_to_sign_degree(lon_deg)
        planets.append(
            PlanetPosition(
                name=name,
                longitude=lon_deg,
                sign=sign,
                degree_in_sign=degree_in_sign,
                house=house_of_longitude(lon_deg, cusps) if houses_reliable else 0,
                retrograde=lon_speed < 0,
            )
        )

    return ChartResult(
        utc_datetime=utc_dt,
        resolved_timezone=tz_name,
        utc_offset_hours=offset_hours,
        julian_day_ut=jd_ut,
        house_system=house_system_label,
        house_system_fallback_reason=fallback_reason,
        house_cusps=list(cusps),
        ascendant=ascmc[0],
        midheaven=ascmc[1],
        houses_reliable=houses_reliable,
        planets=planets,
    )
