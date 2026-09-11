from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException

from app.aspects import find_aspects
from app.ephemeris import ChartCalculationError, calculate_chart, longitude_to_sign_degree
from app.schemas import (
    AngleResponse,
    AspectResponse,
    ChartRequest,
    ChartResponse,
    PlanetPositionResponse,
    ResolvedTimeResponse,
)
from app.timezone_utils import TimezoneResolutionError

app = FastAPI(
    title="Family Astrology API",
    description="Individual birth chart calculation -- the foundation slice before "
    "family tree, thread detection, or any other feature.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chart", response_model=ChartResponse)
def post_chart(request: ChartRequest) -> ChartResponse:
    try:
        chart = calculate_chart(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            lat=request.latitude,
            lon=request.longitude,
        )
    except (ChartCalculationError, TimezoneResolutionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    planet_longitudes = {p.name: p.longitude for p in chart.planets}
    aspects = find_aspects(planet_longitudes)

    asc_sign, asc_deg = longitude_to_sign_degree(chart.ascendant)
    mc_sign, mc_deg = longitude_to_sign_degree(chart.midheaven)

    input_local_dt = datetime.combine(request.birth_date, request.birth_time)

    return ChartResponse(
        resolved_time=ResolvedTimeResponse(
            input_local_datetime=input_local_dt,
            resolved_timezone=chart.resolved_timezone,
            utc_offset_hours=chart.utc_offset_hours,
            utc_datetime=chart.utc_datetime,
        ),
        house_system=chart.house_system,
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
