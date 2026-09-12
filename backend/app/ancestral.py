"""Ancestral pattern report (PROJECT_BRIEF.md Step 5): surfaces cross-generational
themes from each person's water-house placements (4th/8th/12th by default -- see
family_roles.json's per-system ancestral_pattern_houses), per Erin Sullivan's framing
of these houses as where ancestral/unconscious family material lives.

Requires houses_reliable=True: a house-based report is meaningless off a
noon-default chart with unknown birth time, so such people are excluded and
reported as excluded, not silently dropped.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.config import load_family_roles


def get_ancestral_pattern_houses(system: str) -> list[int]:
    return load_family_roles()["systems"][system]["ancestral_pattern_houses"]


@dataclass
class PersonInput:
    name: str
    system: str
    planets: list[dict]  # each: {"name": ..., "house": ..., "sign": ..., ...}
    houses_reliable: bool


@dataclass
class PlanetPlacement:
    planet: str
    house: int
    sign: str


@dataclass
class RecurringTheme:
    planet: str
    houses_by_person: dict[str, int]
    occurrence_count: int


@dataclass
class AncestralPatternReport:
    per_person_placements: dict[str, list[PlanetPlacement]]
    excluded_people: list[str]
    house_emphasis: dict[int, int]
    recurring_themes: list[RecurringTheme]


def person_ancestral_placements(
    planets: list[dict], ancestral_houses: list[int]
) -> list[PlanetPlacement]:
    return [
        PlanetPlacement(planet=p["name"], house=p["house"], sign=p["sign"])
        for p in planets
        if p["house"] in ancestral_houses
    ]


def aggregate_ancestral_patterns(people: list[PersonInput]) -> AncestralPatternReport:
    per_person_placements: dict[str, list[PlanetPlacement]] = {}
    excluded_people: list[str] = []
    house_emphasis: dict[int, int] = defaultdict(int)
    planet_carriers: dict[str, dict[str, int]] = defaultdict(dict)

    for person in people:
        if not person.houses_reliable:
            excluded_people.append(person.name)
            continue

        ancestral_houses = get_ancestral_pattern_houses(person.system)
        placements = person_ancestral_placements(person.planets, ancestral_houses)
        per_person_placements[person.name] = placements

        for placement in placements:
            house_emphasis[placement.house] += 1
            planet_carriers[placement.planet][person.name] = placement.house

    recurring_themes = [
        RecurringTheme(planet=planet, houses_by_person=carriers, occurrence_count=len(carriers))
        for planet, carriers in planet_carriers.items()
        if len(carriers) >= 2
    ]
    recurring_themes.sort(key=lambda t: (-t.occurrence_count, t.planet))

    return AncestralPatternReport(
        per_person_placements=per_person_placements,
        excluded_people=excluded_people,
        house_emphasis=dict(house_emphasis),
        recurring_themes=recurring_themes,
    )
