from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ChartRequest(BaseModel):
    birth_date: date = Field(..., description="Local civil birth date")
    birth_time: time = Field(..., description="Local civil birth time (24h)")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

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
    resolved_timezone: str
    utc_offset_hours: float
    utc_datetime: datetime


class AngleResponse(BaseModel):
    longitude: float
    sign: str
    degree_in_sign: float


class ChartResponse(BaseModel):
    resolved_time: ResolvedTimeResponse
    house_system: str
    house_cusps: list[float]
    ascendant: AngleResponse
    midheaven: AngleResponse
    planets: list[PlanetPositionResponse]
    aspects: list[AspectResponse]
