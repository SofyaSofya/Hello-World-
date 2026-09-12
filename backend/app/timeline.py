"""Family timeline (PROJECT_BRIEF.md Step 8): life events by age per person, and
cross-generational age-timing coincidences -- the same event_type occurring at the
same completed age for 2+ family members, per Lynn Bell's family timing/anniversary
method.

event_type is validated against family_roles.json's family_timeline_rules.
event_types rather than a hardcoded Python enum, so the taxonomy stays
config-driven like the rest of the astrological ruleset (planet lists, aspect
types, etc.).

Matching is exact-age only (no tolerance band) -- see family_roles.json's notes on
why a fuzzy version was deliberately left unbuilt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.config import load_family_roles


def _rules() -> dict:
    return load_family_roles()["family_timeline_rules"]


def get_life_event_types() -> list[str]:
    return _rules()["event_types"]


def compute_age_at_event(birth_date: date, event_date: date) -> int:
    """Completed years between birth_date and event_date (standard "age" convention:
    doesn't turn over until the birthday has passed in the event's year)."""
    age = event_date.year - birth_date.year
    if (event_date.month, event_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


@dataclass
class EventInput:
    person_name: str
    event_type: str
    age_at_event: int


@dataclass
class TimingPattern:
    event_type: str
    age_at_event: int
    people: list[str]
    occurrence_count: int


def detect_timing_patterns(events: list[EventInput]) -> list[TimingPattern]:
    min_occurrences = _rules()["minimum_occurrences_to_flag"]

    carriers: dict[tuple[str, int], list[str]] = defaultdict(list)
    for event in events:
        key = (event.event_type, event.age_at_event)
        if event.person_name not in carriers[key]:
            carriers[key].append(event.person_name)

    patterns = [
        TimingPattern(
            event_type=event_type,
            age_at_event=age,
            people=people,
            occurrence_count=len(people),
        )
        for (event_type, age), people in carriers.items()
        if len(people) >= min_occurrences
    ]
    patterns.sort(key=lambda p: (-p.occurrence_count, p.event_type, p.age_at_event))
    return patterns
