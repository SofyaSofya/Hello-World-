"""Planetary thread detector (flagship feature): pairwise comparison of aspects
across family members' charts, flagging planet-pair + aspect-type combinations that
recur across 2+ people -- per Lynn Bell's genogram "planetary thread" method
(see PROJECT_BRIEF.md / family_roles.json's planetary_thread_rules).

Deliberately in-memory and stateless for now: takes each person's planet longitudes
directly, no family tree or persistence required. This lets the detector's logic be
proven out before investing in a data model for people/relationships.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.aspects import find_aspects
from app.config import get_aspect_orb_rules


@dataclass
class Thread:
    planet_a: str
    planet_b: str
    aspect_type: str
    people: list[str]
    occurrence_count: int


def detect_threads(people_planet_longitudes: dict[str, dict[str, float]]) -> list[Thread]:
    """people_planet_longitudes: {person_name: {planet_name: longitude}}.

    A thread is flagged when the same planet-pair + aspect-type combination appears
    in minimum_occurrences_to_flag (family_roles.json, currently 2) or more people's
    charts, independent of house placement.
    """
    min_occurrences = get_aspect_orb_rules()["minimum_occurrences_to_flag"]

    carriers: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for person, longitudes in people_planet_longitudes.items():
        for aspect in find_aspects(longitudes):
            key = (aspect.planet_a, aspect.planet_b, aspect.aspect_type)
            carriers[key].append(person)

    threads = [
        Thread(
            planet_a=planet_a,
            planet_b=planet_b,
            aspect_type=aspect_type,
            people=people,
            occurrence_count=len(people),
        )
        for (planet_a, planet_b, aspect_type), people in carriers.items()
        if len(people) >= min_occurrences
    ]
    threads.sort(key=lambda t: (-t.occurrence_count, t.planet_a, t.planet_b, t.aspect_type))
    return threads
