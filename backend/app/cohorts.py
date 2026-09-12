"""Generational cohort lens (PROJECT_BRIEF.md Step 7): groups persisted family
members by outer-planet (Uranus/Neptune/Pluto) sign. These planets move slowly
enough (84-248yr orbits) that people from the same genealogical generation
typically land in the same sign, so grouping by sign IS grouping by generation, per
Sullivan's framework -- no genealogical generation number needs deriving from the
relationships graph.

Reuses family_roles.json's planetary_thread_rules.planet_filtering.
generational_planets -- the exact three planets excluded from the thread detector
as generational noise are the signal this lens exists to surface instead.

Unlike the thread detector, a cohort of one person is still meaningful output (the
point is comparing cohorts across generations, not flagging recurrence within one),
so there's no minimum-occurrence filtering here.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.config import get_aspect_orb_rules


def generational_planets() -> list[str]:
    return get_aspect_orb_rules()["planet_filtering"]["generational_planets"]


@dataclass
class PersonInput:
    name: str
    planets: list[dict]  # each: {"name": ..., "sign": ..., ...}


@dataclass
class Cohort:
    sign: str
    people: list[str]


@dataclass
class PlanetCohorts:
    planet: str
    cohorts: list[Cohort]

    @property
    def distinct_cohort_count(self) -> int:
        return len(self.cohorts)


@dataclass
class GenerationalCohortReport:
    cohorts_by_planet: list[PlanetCohorts]


def aggregate_generational_cohorts(people: list[PersonInput]) -> GenerationalCohortReport:
    cohorts_by_planet: list[PlanetCohorts] = []

    for planet in generational_planets():
        sign_to_people: dict[str, list[str]] = defaultdict(list)
        for person in people:
            placement = next((p for p in person.planets if p["name"] == planet), None)
            if placement is not None:
                sign_to_people[placement["sign"]].append(person.name)

        cohorts = [Cohort(sign=sign, people=names) for sign, names in sign_to_people.items()]
        cohorts.sort(key=lambda c: (-len(c.people), c.sign))
        cohorts_by_planet.append(PlanetCohorts(planet=planet, cohorts=cohorts))

    return GenerationalCohortReport(cohorts_by_planet=cohorts_by_planet)
