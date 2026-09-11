"""Resolve a birth location + local date/time into UTC.

Birth times for astrology are recorded in local civil time, but Swiss Ephemeris
needs UTC. We auto-resolve the IANA timezone from lat/lon (handling historical
DST/offset rules, e.g. the Soviet Union's decree time) so callers never have to
compute a UTC offset themselves. The resolved timezone name and offset are
returned alongside the UTC time so the API response can expose them for
confirmation.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()


class TimezoneResolutionError(ValueError):
    pass


def resolve_timezone_name(lat: float, lon: float) -> str:
    tz_name = _tf.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        tz_name = _tf.closest_timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        raise TimezoneResolutionError(
            f"Could not resolve a timezone for coordinates ({lat}, {lon})"
        )
    return tz_name


def local_to_utc(
    birth_date: date, birth_time: time, lat: float, lon: float
) -> tuple[datetime, str, float]:
    """Returns (utc_datetime, resolved_tz_name, utc_offset_hours)."""
    tz_name = resolve_timezone_name(lat, lon)
    local_dt = datetime.combine(birth_date, birth_time, tzinfo=ZoneInfo(tz_name))
    utc_dt = local_dt.astimezone(timezone.utc)
    offset_hours = local_dt.utcoffset().total_seconds() / 3600
    return utc_dt, tz_name, offset_hours
