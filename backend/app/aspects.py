"""Aspect detection between planet pairs, using the orb rules in family_roles.json."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_aspect_orb_rules

# angle -> aspect name, degrees apart on the ecliptic
ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}


@dataclass
class Aspect:
    planet_a: str
    planet_b: str
    aspect_type: str
    exact_angle: float
    orb: float  # how many degrees off from exact


def angular_separation(lon_a: float, lon_b: float) -> float:
    """Shortest angular distance between two ecliptic longitudes, in [0, 180]."""
    diff = abs(lon_a - lon_b) % 360
    return min(diff, 360 - diff)


def find_aspects(planet_longitudes: dict[str, float]) -> list[Aspect]:
    """Given {planet_name: longitude}, return every aspect within the configured orb.

    Orb rules and which aspect types to check come from family_roles.json's
    planetary_thread_rules, so this stays a single source of truth shared with the
    (future) planetary thread detector.
    """
    rules = get_aspect_orb_rules()
    checked_types = rules["aspect_types_checked"]
    orb_degrees = rules["orb_degrees"]

    names = list(planet_longitudes.keys())
    aspects: list[Aspect] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a, name_b = names[i], names[j]
            separation = angular_separation(
                planet_longitudes[name_a], planet_longitudes[name_b]
            )
            for aspect_type in checked_types:
                exact_angle = ASPECT_ANGLES[aspect_type]
                orb = abs(separation - exact_angle)
                if orb <= orb_degrees[aspect_type]:
                    aspects.append(
                        Aspect(
                            planet_a=name_a,
                            planet_b=name_b,
                            aspect_type=aspect_type,
                            exact_angle=exact_angle,
                            orb=round(orb, 4),
                        )
                    )
    return aspects
