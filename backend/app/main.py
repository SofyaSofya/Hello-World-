from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException

from app.aspects import find_aspects
from app.ephemeris import (
    DEFAULT_UNKNOWN_BIRTH_TIME,
    ChartCalculationError,
    calculate_chart,
    longitude_to_sign_degree,
)
from app.schemas import (
    AngleResponse,
    AspectResponse,
    ChartRequest,
    ChartResponse,
    FamilyThreadsRequest,
    FamilyThreadsResponse,
    PlanetPositionResponse,
    ResolvedTimeResponse,
    ThreadResponse,
)
from app.threads import default_included_categories, detect_threads
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
            system=request.system,
            utc_offset_override=request.utc_offset_override,
        )
    except (ChartCalculationError, TimezoneResolutionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    planet_longitudes = {p.name: p.longitude for p in chart.planets}
    aspects = find_aspects(planet_longitudes)

    asc_sign, asc_deg = longitude_to_sign_degree(chart.ascendant)
    mc_sign, mc_deg = longitude_to_sign_degree(chart.midheaven)

    input_local_dt = datetime.combine(
        request.birth_date, request.birth_time or DEFAULT_UNKNOWN_BIRTH_TIME
    )

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


@app.post("/family/threads", response_model=FamilyThreadsResponse)
def post_family_threads(request: FamilyThreadsRequest) -> FamilyThreadsResponse:
    names = [person.name for person in request.people]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Person names must be unique")

    people_planet_longitudes: dict[str, dict[str, float]] = {}
    for person in request.people:
        try:
            chart = calculate_chart(
                birth_date=person.birth_date,
                birth_time=person.birth_time,
                lat=person.latitude,
                lon=person.longitude,
                system=person.system,
                utc_offset_override=person.utc_offset_override,
            )
        except (ChartCalculationError, TimezoneResolutionError) as exc:
            raise HTTPException(status_code=422, detail=f"{person.name}: {exc}") from exc
        people_planet_longitudes[person.name] = {p.name: p.longitude for p in chart.planets}

    include_categories = default_included_categories()
    if request.include_generational_planets:
        include_categories.add("generational")
    threads = detect_threads(people_planet_longitudes, include_categories=include_categories)

    return FamilyThreadsResponse(
        people=names,
        threads=[
            ThreadResponse(
                planet_a=t.planet_a,
                planet_b=t.planet_b,
                aspect_type=t.aspect_type,
                category=t.category,
                people=t.people,
                occurrence_count=t.occurrence_count,
            )
            for t in threads
        ],
    )
