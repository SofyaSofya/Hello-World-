"""Family element profile (PROJECT_BRIEF.md Step 4): aggregate elemental
(Fire/Earth/Air/Water) balance across a family's charts, per Erin Sullivan's family
element typing. First feature built against the persisted data model -- reads
planets/ascendant straight from stored Chart rows rather than raw birth data.

Weighting (Sun/Moon/Ascendant count double) is a documented design decision in
family_roles.json's family_element_profile_rules, not an astrological standard --
see that file's notes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import load_family_roles
from app.ephemeris import SIGNS

ELEMENTS = ["Fire", "Earth", "Air", "Water"]

ARCHETYPE_SUMMARY = {
    "Fire": (
        "A Fire-dominant family: animated by action, initiative, and shared "
        "enthusiasm -- momentum comes easily, follow-through sometimes less so."
    ),
    "Earth": (
        "An Earth-dominant family: grounded in stability, tradition, and material "
        "security -- practical and enduring, sometimes resistant to change."
    ),
    "Air": (
        "An Air-dominant family: oriented around ideas, communication, and social "
        "connection -- intellectually engaged, sometimes more comfortable "
        "discussing feelings than sitting with them."
    ),
    "Water": (
        "A Water-dominant family: emotionally attuned and bonded through feeling "
        "-- deeply connected, sometimes prone to enmeshment or blurred boundaries."
    ),
}


def element_of_sign(sign: str) -> str:
    return ELEMENTS[SIGNS.index(sign) % 4]


def _rules() -> dict:
    return load_family_roles()["family_element_profile_rules"]


def person_element_weights(
    planets: list[dict], ascendant_sign: str, houses_reliable: bool
) -> dict[str, float]:
    """planets: list of {"name": ..., "sign": ..., ...} dicts (as stored on Chart)."""
    rules = _rules()
    personal_points = set(rules["personal_points"])
    personal_weight = rules["personal_point_weight"]
    default_weight = rules["default_weight"]

    weights = {element: 0.0 for element in ELEMENTS}
    for planet in planets:
        weight = personal_weight if planet["name"] in personal_points else default_weight
        weights[element_of_sign(planet["sign"])] += weight

    if houses_reliable and "Ascendant" in personal_points:
        weights[element_of_sign(ascendant_sign)] += personal_weight

    return weights


def weights_to_percentages(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total == 0:
        return {element: 0.0 for element in ELEMENTS}
    return {element: round(weight / total * 100, 2) for element, weight in weights.items()}


def dominant_element(weights: dict[str, float]) -> str:
    """On a tie, resolves to whichever element comes first in ELEMENTS
    (Fire > Earth > Air > Water) -- arbitrary but deterministic. Ties aren't rare:
    a two-person family easily lands exactly on one, so this isn't an edge case to
    ignore."""
    return max(weights, key=weights.get)


@dataclass
class PersonInput:
    name: str
    planets: list[dict]
    ascendant_sign: str
    houses_reliable: bool


@dataclass
class FamilyElementProfile:
    family_percentages: dict[str, float]
    dominant_element: str
    archetype_summary: str
    per_person_percentages: dict[str, dict[str, float]]


def aggregate_family_elements(people: list[PersonInput]) -> FamilyElementProfile:
    family_weights = {element: 0.0 for element in ELEMENTS}
    per_person_percentages: dict[str, dict[str, float]] = {}

    for person in people:
        weights = person_element_weights(
            person.planets, person.ascendant_sign, person.houses_reliable
        )
        for element in ELEMENTS:
            family_weights[element] += weights[element]
        per_person_percentages[person.name] = weights_to_percentages(weights)

    dominant = dominant_element(family_weights)

    return FamilyElementProfile(
        family_percentages=weights_to_percentages(family_weights),
        dominant_element=dominant,
        archetype_summary=ARCHETYPE_SUMMARY[dominant],
        per_person_percentages=per_person_percentages,
    )
