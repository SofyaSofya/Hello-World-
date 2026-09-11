"""Birth chart calculation via the Swiss Ephemeris (pyswisseph).

Uses the Moshier semi-analytical model (SEFLG_MOSEPH) rather than the
high-precision JPL/Swiss ephemeris files, since Moshier needs no external data
files and is accurate to ~1 arcsecond over years -3000..3000 -- plenty for
astrology use. House system is Placidus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time

import swisseph as swe

from app.timezone_utils import local_to_utc

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

HOUSE_SYSTEM_CODE = b"P"  # Placidus
HOUSE_SYSTEM_LABEL = "Placidus"

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
    resolved_timezone: str
    utc_offset_hours: float
    julian_day_ut: float
    house_system: str
    house_cusps: list[float]
    ascendant: float
    midheaven: float
    planets: list[PlanetPosition] = field(default_factory=list)


def calculate_chart(
    birth_date: date, birth_time: time, lat: float, lon: float
) -> ChartResult:
    if not (-90 <= lat <= 90):
        raise ChartCalculationError("Latitude must be between -90 and 90 degrees")
    if not (-180 <= lon <= 180):
        raise ChartCalculationError("Longitude must be between -180 and 180 degrees")

    utc_dt, tz_name, offset_hours = local_to_utc(birth_date, birth_time, lat, lon)

    hour_decimal = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal)

    cusps, ascmc = swe.houses(jd_ut, lat, lon, HOUSE_SYSTEM_CODE)

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
                house=house_of_longitude(lon_deg, cusps),
                retrograde=lon_speed < 0,
            )
        )

    return ChartResult(
        utc_datetime=utc_dt,
        resolved_timezone=tz_name,
        utc_offset_hours=offset_hours,
        julian_day_ut=jd_ut,
        house_system=HOUSE_SYSTEM_LABEL,
        house_cusps=list(cusps),
        ascendant=ascmc[0],
        midheaven=ascmc[1],
        planets=planets,
    )
