# Family Astrology App — Project Brief

## Concept

An analytical app that reads and analyzes a *family* through astrology, not just an
individual. Instead of one birth chart, the app builds a family tree of charts and
surfaces patterns across generations: recurring placements, elemental balance,
ancestral themes, and generational cohorts.

Content framework draws on three astrological traditions of family analysis:

- **Erin Sullivan, *The Astrology of Family Dynamics*** — family as an organic whole;
  elemental family typing (Earth/Fire/Air/Water); the "water houses" (4th/8th/12th) as
  where ancestral and unconscious material lives; generational cohorts defined by
  outer-planet sign placements (Pluto/Neptune/Uranus).
- **Lynn Bell, *Planetary Threads*** — genogram-style family mapping (borrowed from
  family therapy) annotated with recurring planetary placements/aspects; the "planetary
  thread" concept (a planet-pair + aspect combination that recurs across family
  members); extends analysis to siblings and "found family" via the 3rd/11th houses;
  family timing/anniversary patterns (life events recurring at the same age across
  generations).
- **Traditional house/planet significators** (Western tropical + Vedic) — see
  `family_roles.json` for the full encoded ruleset. Western and Vedic systems disagree
  on father (10th vs 9th house) and sibling birth order (3rd vs 3rd+11th); MVP defaults
  to Western tropical with the schema built to support a system toggle later.

## Core Features (priority order for MVP)

1. **Individual birth chart generation** — planets, houses, aspects from birth
   date/time/location. Foundation for everything else.
2. **Family tree data model** — people + relationship edges (parent/child, sibling,
   spouse), each person linked to their chart.
3. **Planetary thread detector** (flagship feature) — pairwise comparison of aspects
   across all family members' charts; flags planet-pair + aspect combinations that
   recur in 2+ people. Rules in `family_roles.json` under `planetary_thread_rules`.
4. **Family element profile** — aggregate elemental (Fire/Earth/Air/Water) balance
   across the family tree; generates a family "archetype" summary.
5. **Ancestral pattern report** — pulls each person's 4th/8th/12th house placements and
   surfaces cross-generational themes.
6. **Genogram-style tree visualization** — family tree UI annotated with chart data and
   detected threads.
7. **Generational cohort lens** — compares grandparent/parent/child cohorts by
   outer-planet sign (these change slowly, so they cluster by generation rather than
   individual).
8. **Family timeline** — life events by age per person, flags cross-generational
   age/timing coincidences.

## Data Model (high level)

- `people`: id, name, birth_date, birth_time, birth_location (lat/lon), chart_id
- `charts`: id, person_id, planet positions (sign, degree, house), house cusps
  (via Swiss Ephemeris), aspects (computed from planet positions + orb rules)
- `relationships`: id, person_a_id, person_b_id, relationship_type (parent, sibling,
  spouse, etc.), generation_offset
- `family_roles` config (static, from `family_roles.json`): maps relationship type →
  houses/planets/rules per astrological system
- `threads`: computed table/view — planet_a, planet_b, aspect_type, list of person_ids
  who carry it, occurrence_count

## Tech Stack

**Backend**
- Ephemeris/chart calculation: Swiss Ephemeris (via `pyswisseph` if Python, or a Node
  binding) — do not hand-roll astronomical calculations.
- API: FastAPI (Python) or NestJS (Node). Python is a good fit if the thread-detection
  and pattern analysis logic grows more statistical (pandas/networkx).
- Database: PostgreSQL for relational data (people, relationships, charts).
  Family tree traversal is graph-like — either model it relationally with a
  `relationships` edge table (fine at small/medium scale) or use Neo4j if tree queries
  get complex.

**Frontend**
- Next.js (React) — ships as a web app first, PWA-capable, good for organic/SEO growth.
  React Native later if a native mobile app is needed, reusing the API layer.

**Content**
- Interpretive text (what a Moon-Pluto thread *means*, what a Water-dominant family
  looks like, etc.) is static/templated content keyed off the computed astrological
  facts — this is a content-writing task as much as an engineering one. Model it as a
  lookup table: `interpretation_key -> long-form text`, so writers can iterate without
  touching code.

## Open Decisions

- Western tropical vs. Vedic as default, or both via toggle (MVP: Western default,
  schema supports toggle).
- Whether children/spouses need their own charts in v1, or if MVP starts with a single
  three-generation family (grandparents/parents/self) to prove out the thread detector
  first.
- Platform priority (web vs. mobile vs. both) — recommended: web/PWA first.
