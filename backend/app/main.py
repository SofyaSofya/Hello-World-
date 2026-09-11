from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.chart_presentation import aspects_to_json, chart_to_response, compute_chart, planets_to_json
from app.db import get_db
from app.ephemeris import DEFAULT_UNKNOWN_BIRTH_TIME, ChartCalculationError, longitude_to_sign_degree
from app.schemas import (
    AngleResponse,
    ChartRequest,
    ChartResponse,
    DEFAULT_GENERATION_OFFSET,
    FamilyThreadsRequest,
    FamilyThreadsResponse,
    PersistedThreadsRequest,
    PersonCreate,
    PersonResponse,
    RelationshipCreate,
    RelationshipResponse,
    ResolvedTimeResponse,
    ThreadResponse,
)
from app.threads import default_included_categories, detect_threads
from app.timezone_utils import TimezoneResolutionError

app = FastAPI(
    title="Family Astrology API",
    description="Individual birth chart calculation, an in-memory thread detector, "
    "and (from Step 3) a persisted family tree data model.",
    version="0.2.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chart", response_model=ChartResponse)
def post_chart(request: ChartRequest) -> ChartResponse:
    try:
        chart, aspects = compute_chart(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            lat=request.latitude,
            lon=request.longitude,
            system=request.system,
            utc_offset_override=request.utc_offset_override,
        )
    except (ChartCalculationError, TimezoneResolutionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return chart_to_response(chart, aspects, request.birth_date, request.birth_time)


@app.post("/family/threads", response_model=FamilyThreadsResponse)
def post_family_threads(request: FamilyThreadsRequest) -> FamilyThreadsResponse:
    """Stateless thread detection over raw birth data -- no persistence. Useful for
    trying the detector without creating people. See POST /threads for the
    persisted-family-tree equivalent (Step 3)."""
    names = [person.name for person in request.people]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Person names must be unique")

    people_planet_longitudes: dict[str, dict[str, float]] = {}
    for person in request.people:
        try:
            chart, _aspects = compute_chart(
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


# --- Persisted family tree (Step 3) -----------------------------------------


def _person_to_response(person: models.Person, chart: models.Chart) -> PersonResponse:
    asc_sign, asc_deg = longitude_to_sign_degree(chart.ascendant)
    mc_sign, mc_deg = longitude_to_sign_degree(chart.midheaven)
    input_local_dt = datetime.combine(
        person.birth_date, person.birth_time or DEFAULT_UNKNOWN_BIRTH_TIME
    )

    return PersonResponse(
        id=person.id,
        name=person.name,
        birth_date=person.birth_date,
        birth_time=person.birth_time,
        latitude=person.latitude,
        longitude=person.longitude,
        system=person.system,
        utc_offset_override=person.utc_offset_override,
        chart=ChartResponse(
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
            planets=chart.planets,
            aspects=chart.aspects,
        ),
    )


@app.post("/people", response_model=PersonResponse, status_code=201)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> PersonResponse:
    try:
        chart_result, aspects = compute_chart(
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            lat=payload.latitude,
            lon=payload.longitude,
            system=payload.system,
            utc_offset_override=payload.utc_offset_override,
        )
    except (ChartCalculationError, TimezoneResolutionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    person = models.Person(
        name=payload.name,
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        system=payload.system,
        utc_offset_override=payload.utc_offset_override,
    )
    db.add(person)
    db.flush()

    chart = models.Chart(
        person_id=person.id,
        resolved_timezone=chart_result.resolved_timezone,
        utc_offset_hours=chart_result.utc_offset_hours,
        utc_datetime=chart_result.utc_datetime,
        julian_day_ut=chart_result.julian_day_ut,
        house_system=chart_result.house_system,
        house_system_fallback_reason=chart_result.house_system_fallback_reason,
        houses_reliable=chart_result.houses_reliable,
        house_cusps=chart_result.house_cusps,
        ascendant=chart_result.ascendant,
        midheaven=chart_result.midheaven,
        planets=planets_to_json(chart_result),
        aspects=aspects_to_json(aspects),
    )
    db.add(chart)
    db.commit()
    db.refresh(person)
    db.refresh(chart)

    return _person_to_response(person, chart)


@app.get("/people", response_model=list[PersonResponse])
def list_people(db: Session = Depends(get_db)) -> list[PersonResponse]:
    people = db.query(models.Person).order_by(models.Person.id).all()
    return [_person_to_response(p, p.chart) for p in people]


@app.get("/people/{person_id}", response_model=PersonResponse)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonResponse:
    person = db.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail=f"No person with id {person_id}")
    return _person_to_response(person, person.chart)


@app.post("/relationships", response_model=RelationshipResponse, status_code=201)
def create_relationship(
    payload: RelationshipCreate, db: Session = Depends(get_db)
) -> RelationshipResponse:
    if payload.person_a_id == payload.person_b_id:
        raise HTTPException(status_code=422, detail="person_a_id and person_b_id must differ")

    for person_id in (payload.person_a_id, payload.person_b_id):
        if db.get(models.Person, person_id) is None:
            raise HTTPException(status_code=422, detail=f"No person with id {person_id}")

    generation_offset = (
        payload.generation_offset
        if payload.generation_offset is not None
        else DEFAULT_GENERATION_OFFSET[payload.relationship_type]
    )

    relationship = models.Relationship(
        person_a_id=payload.person_a_id,
        person_b_id=payload.person_b_id,
        relationship_type=payload.relationship_type,
        generation_offset=generation_offset,
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    return RelationshipResponse(
        id=relationship.id,
        person_a_id=relationship.person_a_id,
        person_b_id=relationship.person_b_id,
        relationship_type=relationship.relationship_type,
        generation_offset=relationship.generation_offset,
    )


@app.get("/relationships", response_model=list[RelationshipResponse])
def list_relationships(db: Session = Depends(get_db)) -> list[RelationshipResponse]:
    relationships = db.query(models.Relationship).order_by(models.Relationship.id).all()
    return [
        RelationshipResponse(
            id=r.id,
            person_a_id=r.person_a_id,
            person_b_id=r.person_b_id,
            relationship_type=r.relationship_type,
            generation_offset=r.generation_offset,
        )
        for r in relationships
    ]


@app.post("/threads", response_model=FamilyThreadsResponse)
def post_persisted_threads(
    request: PersistedThreadsRequest = PersistedThreadsRequest(), db: Session = Depends(get_db)
) -> FamilyThreadsResponse:
    """Planetary thread detection over all persisted people -- reuses the same
    detect_threads() pure function as the stateless /family/threads endpoint, just
    reading planet longitudes from stored charts instead of recomputing them."""
    people = db.query(models.Person).order_by(models.Person.id).all()
    if len(people) < 2:
        raise HTTPException(
            status_code=422, detail="At least 2 persisted people are needed to detect threads"
        )

    people_planet_longitudes = {
        person.name: {p["name"]: p["longitude"] for p in person.chart.planets} for person in people
    }

    include_categories = default_included_categories()
    if request.include_generational_planets:
        include_categories.add("generational")
    threads = detect_threads(people_planet_longitudes, include_categories=include_categories)

    return FamilyThreadsResponse(
        people=[p.name for p in people],
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
