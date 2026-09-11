"""Planetary thread detector (flagship feature): pairwise comparison of aspects
across family members' charts, flagging planet-pair + aspect-type combinations that
recur across 2+ people -- per Lynn Bell's genogram "planetary thread" method
(see PROJECT_BRIEF.md / family_roles.json's planetary_thread_rules).

Deliberately in-memory and stateless for now: takes each person's planet longitudes
directly, no family tree or persistence required. This lets the detector's logic be
proven out before investing in a data model for people/relationships.

Generational planets (Uranus/Neptune/Pluto) move slowly enough that any two people
of the same astrological generation share them almost regardless of family, so
they're excluded by default -- see family_roles.json's planetary_thread_rules.
planet_filtering. That's a config toggle, not a hard rule: callers can opt back in
via `include_categories`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.aspects import find_aspects
from app.config import get_aspect_orb_rules

# category name -> family_roles.json planet_filtering key
_CATEGORY_TO_CONFIG_KEY = {
    "personal": "personal_planets",
    "social": "social_planets",
    "generational": "generational_planets",
}
_CATEGORY_PRIORITY = ["generational", "social", "personal", "unknown"]


@dataclass
class Thread:
    planet_a: str
    planet_b: str
    aspect_type: str
    category: str
    people: list[str]
    occurrence_count: int


def _planet_categories() -> dict[str, list[str]]:
    filtering = get_aspect_orb_rules()["planet_filtering"]
    return {
        category: filtering[config_key]
        for category, config_key in _CATEGORY_TO_CONFIG_KEY.items()
    }


def default_included_categories() -> set[str]:
    filtering = get_aspect_orb_rules()["planet_filtering"]
    config_key_to_category = {v: k for k, v in _CATEGORY_TO_CONFIG_KEY.items()}
    return {config_key_to_category[key] for key in filtering["included_by_default"]}


def _planet_category(planet: str, categories: dict[str, list[str]]) -> str:
    for category_name, planets in categories.items():
        if planet in planets:
            return category_name
    return "unknown"


def _pair_category(planet_a: str, planet_b: str, categories: dict[str, list[str]]) -> str:
    """A pair's category is the slower-moving (more generational) of the two planets,
    so e.g. a Moon-Saturn aspect is labeled 'social', not 'personal'."""
    cat_a = _planet_category(planet_a, categories)
    cat_b = _planet_category(planet_b, categories)
    return min((cat_a, cat_b), key=_CATEGORY_PRIORITY.index)


def detect_threads(
    people_planet_longitudes: dict[str, dict[str, float]],
    include_categories: set[str] | None = None,
) -> list[Thread]:
    """people_planet_longitudes: {person_name: {planet_name: longitude}}.

    A thread is flagged when the same planet-pair + aspect-type combination appears
    in minimum_occurrences_to_flag (family_roles.json, currently 2) or more people's
    charts, independent of house placement.

    include_categories restricts which planets are considered at all (a planet is
    included only if it's in one of these categories: "personal", "social",
    "generational"); defaults to family_roles.json's planet_filtering.
    included_by_default ({"personal", "social"} -- excludes generational planets
    unless explicitly requested).
    """
    min_occurrences = get_aspect_orb_rules()["minimum_occurrences_to_flag"]
    categories = _planet_categories()
    if include_categories is None:
        include_categories = default_included_categories()

    included_planets = {
        planet
        for category_name, planets in categories.items()
        if category_name in include_categories
        for planet in planets
    }

    carriers: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for person, longitudes in people_planet_longitudes.items():
        filtered_longitudes = {
            planet: lon for planet, lon in longitudes.items() if planet in included_planets
        }
        for aspect in find_aspects(filtered_longitudes):
            key = (aspect.planet_a, aspect.planet_b, aspect.aspect_type)
            carriers[key].append(person)

    threads = [
        Thread(
            planet_a=planet_a,
            planet_b=planet_b,
            aspect_type=aspect_type,
            category=_pair_category(planet_a, planet_b, categories),
            people=people,
            occurrence_count=len(people),
        )
        for (planet_a, planet_b, aspect_type), people in carriers.items()
        if len(people) >= min_occurrences
    ]
    threads.sort(key=lambda t: (-t.occurrence_count, t.planet_a, t.planet_b, t.aspect_type))
    return threads
