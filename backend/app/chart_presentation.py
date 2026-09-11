"""Shared logic for turning calculate_chart() output into API-shaped data.

Used by both the stateless POST /chart endpoint and POST /people (which persists
the same computation), so the two never drift apart.
"""

from __future__ import annotations

from datetime import date, datetime, time

from app.aspects import Aspect, find_aspects
from app.ephemeris import DEFAULT_UNKNOWN_BIRTH_TIME, ChartResult, calculate_chart, longitude_to_sign_degree
from app.schemas import (
    AngleResponse,
    AspectResponse,
    AstrologicalSystemLiteral,
    ChartResponse,
    PlanetPositionResponse,
    ResolvedTimeResponse,
)


def compute_chart(
    birth_date: date,
    birth_time: time | None,
    lat: float,
    lon: float,
    system: AstrologicalSystemLiteral,
    utc_offset_override: float | None,
) -> tuple[ChartResult, list[Aspect]]:
    chart = calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        lat=lat,
        lon=lon,
        system=system,
        utc_offset_override=utc_offset_override,
    )
    planet_longitudes = {p.name: p.longitude for p in chart.planets}
    aspects = find_aspects(planet_longitudes)
    return chart, aspects


def chart_to_response(
    chart: ChartResult, aspects: list[Aspect], birth_date: date, birth_time: time | None
) -> ChartResponse:
    asc_sign, asc_deg = longitude_to_sign_degree(chart.ascendant)
    mc_sign, mc_deg = longitude_to_sign_degree(chart.midheaven)

    input_local_dt = datetime.combine(birth_date, birth_time or DEFAULT_UNKNOWN_BIRTH_TIME)

    return ChartResponse(
        resolved_time=ResolvedTimeResponse(
            input_local_datetime=input_local_dt,
            resolved_timezone=chart.resolved_timezone,
            utc_offset_hours=chart.utc_offset_hours,
            utc_datetime=chart.utc_datetime,
        ),
        house_system=chart.house_system,
        house_system_fallback_reason=chart.house_system_fallback_reason,
        houses_reliable=chart.houses_reliable,
        house_cusps=chart.house_cusps,
        ascendant=AngleResponse(longitude=chart.ascendant, sign=asc_sign, degree_in_sign=asc_deg),
        midheaven=AngleResponse(longitude=chart.midheaven, sign=mc_sign, degree_in_sign=mc_deg),
        planets=[
            PlanetPositionResponse(
                name=p.name,
                longitude=p.longitude,
                sign=p.sign,
                degree_in_sign=p.degree_in_sign,
                house=p.house,
                retrograde=p.retrograde,
            )
            for p in chart.planets
        ],
        aspects=[
            AspectResponse(
                planet_a=a.planet_a,
                planet_b=a.planet_b,
                aspect_type=a.aspect_type,
                exact_angle=a.exact_angle,
                orb=a.orb,
            )
            for a in aspects
        ],
    )


def planets_to_json(chart: ChartResult) -> list[dict]:
    return [
        {
            "name": p.name,
            "longitude": p.longitude,
            "sign": p.sign,
            "degree_in_sign": p.degree_in_sign,
            "house": p.house,
            "retrograde": p.retrograde,
        }
        for p in chart.planets
    ]


def aspects_to_json(aspects: list[Aspect]) -> list[dict]:
    return [
        {
            "planet_a": a.planet_a,
            "planet_b": a.planet_b,
            "aspect_type": a.aspect_type,
            "exact_angle": a.exact_angle,
            "orb": a.orb,
        }
        for a in aspects
    ]
