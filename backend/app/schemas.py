from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

AstrologicalSystemLiteral = Literal["western_tropical", "vedic"]


class BirthDataInput(BaseModel):
    birth_date: date = Field(..., description="Local civil birth date")
    birth_time: time | None = Field(
        default=None,
        description=(
            "Local civil birth time (24h). If unknown, omit it: the chart falls "
            "back to a noon convention and `houses_reliable` is set to false in "
            "the response, since house placements depend on exact time."
        ),
    )
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    system: AstrologicalSystemLiteral = Field(
        default="western_tropical",
        description="western_tropical (Placidus, auto-fallback to Whole Sign above "
        "~66 deg latitude) or vedic (always Whole Sign).",
    )
    utc_offset_override: float | None = Field(
        default=None,
        description=(
            "Manually specify the UTC offset in hours instead of auto-resolving "
            "one from latitude/longitude. For edge cases: pre-1970s dates outside "
            "tzdata's coverage, or disputed/renamed timezone regions."
        ),
    )


class ChartRequest(BirthDataInput):
    model_config = {
        "json_schema_extra": {
            "example": {
                "birth_date": "1987-02-21",
                "birth_time": "17:00:00",
                "latitude": 55.7558,
                "longitude": 37.6173,
            }
        }
    }


class PlanetPositionResponse(BaseModel):
    name: str
    longitude: float
    sign: str
    degree_in_sign: float
    house: int
    retrograde: bool


class AspectResponse(BaseModel):
    planet_a: str
    planet_b: str
    aspect_type: str
    exact_angle: float
    orb: float


class ResolvedTimeResponse(BaseModel):
    """Exposes how the local birth time was converted, so callers can confirm it
    without having to compute a UTC offset themselves."""

    input_local_datetime: datetime
    resolved_timezone: str | None = Field(
        default=None, description="None when utc_offset_override was used instead."
    )
    utc_offset_hours: float
    utc_datetime: datetime


class AngleResponse(BaseModel):
    longitude: float
    sign: str
    degree_in_sign: float


class ChartResponse(BaseModel):
    resolved_time: ResolvedTimeResponse
    house_system: str
    house_system_fallback_reason: str | None
    houses_reliable: bool
    house_cusps: list[float]
    ascendant: AngleResponse
    midheaven: AngleResponse
    planets: list[PlanetPositionResponse]
    aspects: list[AspectResponse]


class FamilyMemberInput(BirthDataInput):
    name: str = Field(..., min_length=1, description="Used to label detected threads")


class FamilyThreadsRequest(BaseModel):
    people: list[FamilyMemberInput] = Field(..., min_length=2)
    include_generational_planets: bool = Field(
        default=False,
        description=(
            "Uranus/Neptune/Pluto move slowly enough that any two people of the "
            "same astrological generation share them almost regardless of family, "
            "so they're excluded from thread detection by default. Set true to "
            "include them (returned threads are labeled category='generational')."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "people": [
                    {
                        "name": "Grandparent",
                        "birth_date": "1955-06-10",
                        "birth_time": "08:30:00",
                        "latitude": 55.7558,
                        "longitude": 37.6173,
                    },
                    {
                        "name": "Parent",
                        "birth_date": "1987-02-21",
                        "birth_time": "17:00:00",
                        "latitude": 55.7558,
                        "longitude": 37.6173,
                    },
                ]
            }
        }
    }


class ThreadResponse(BaseModel):
    planet_a: str
    planet_b: str
    aspect_type: str
    category: str
    people: list[str]
    occurrence_count: int


class FamilyThreadsResponse(BaseModel):
    people: list[str]
    threads: list[ThreadResponse]
