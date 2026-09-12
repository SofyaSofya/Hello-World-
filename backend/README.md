# Backend

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Database (Postgres)

Requires a running Postgres instance -- if installed locally but not started
(e.g. after a fresh container/session), start the cluster first:

```bash
pg_ctlcluster 16 main start   # version may differ; pg_lsclusters shows what's installed
```

First-time setup:

```bash
sudo pg_ctlcluster <version> main start   # or however your install starts it
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE astro_dev;"
sudo -u postgres psql -c "CREATE DATABASE astro_test;"  # used by the test suite
```

The app reads `DATABASE_URL` (see `backend/.env.example`); it defaults to
`postgresql+psycopg://postgres:postgres@localhost:5432/astro_dev`. Point it at a
hosted instance (RDS, Supabase, etc.) later by just changing this env var -- no
code changes needed.

Apply migrations (from `backend/`):

```bash
alembic upgrade head
```

New model changes: `alembic revision --autogenerate -m "..."` then `alembic upgrade head`.

## Run

```bash
cd backend
uvicorn app.main:app --reload
```

Then `POST /chart`:

```bash
curl -X POST http://127.0.0.1:8000/chart \
  -H "Content-Type: application/json" \
  -d '{
    "birth_date": "1987-02-21",
    "birth_time": "17:00:00",
    "latitude": 55.7558,
    "longitude": 37.6173
  }'
```

Or `POST /family/threads` with 2+ people to detect recurring planet-pair + aspect
combinations across their charts (the "planetary thread" flagship feature -- kept
in-memory/stateless for now, no persistence yet):

```bash
curl -X POST http://127.0.0.1:8000/family/threads \
  -H "Content-Type: application/json" \
  -d '{
    "people": [
      {"name": "Grandparent", "birth_date": "1955-06-10", "birth_time": "08:30:00", "latitude": 55.7558, "longitude": 37.6173},
      {"name": "Parent", "birth_date": "1987-02-21", "birth_time": "17:00:00", "latitude": 55.7558, "longitude": 37.6173}
    ]
  }'
```

Generational planets (Uranus/Neptune/Pluto) are excluded from thread detection by
default, per family_roles.json's `planetary_thread_rules.planet_filtering` -- their
slow orbits make shared placements a function of birth-year proximity, not a
family-specific pattern. Set `"include_generational_planets": true` in the request
to opt in; such threads are returned with `"category": "generational"`.

### Chart options

`POST /chart` and each person in `POST /family/threads` accept:

- `birth_time` (optional) -- if omitted, the chart falls back to a noon convention
  and `houses_reliable: false` is returned (planets get `house: 0`), since house
  placement depends on exact time. Useful when an older relative's exact birth time
  is unknown.
- `system` (`"western_tropical"` default, or `"vedic"`) -- Western tropical uses
  Placidus houses, auto-falling back to Whole Sign above ~66 degrees latitude
  (Placidus is undefined near the poles; `house_system_fallback_reason` explains
  why when this happens). Vedic mode always uses Whole Sign.
- `utc_offset_override` (optional hours) -- bypasses timezone auto-resolution, for
  edge cases like pre-1970s dates outside tzdata's coverage or disputed regions.
  When used, `resolved_time.resolved_timezone` is `null` in the response.

### Persisted family tree (Step 3)

`POST /people` creates a person, computes their chart via the same pipeline as
`POST /chart`, and stores both:

```bash
curl -X POST http://127.0.0.1:8000/people \
  -H "Content-Type: application/json" \
  -d '{"name": "Parent", "birth_date": "1987-02-21", "birth_time": "17:00:00", "latitude": 55.7558, "longitude": 37.6173}'
```

`GET /people`, `GET /people/{id}` read persisted people + their stored chart.
`POST /relationships` links two people (`relationship_type`: `parent` | `sibling` |
`spouse`; `generation_offset` defaults by type -- 1 for parent, 0 for sibling/spouse
-- if omitted). `GET /relationships` lists them.

`POST /threads` runs the same `detect_threads()` function as `POST /family/threads`,
but reads planet longitudes from every persisted person's stored chart instead of
recomputing from raw birth data each time -- "the family" is currently just "all
persisted people" (there's no separate family-grouping entity yet; see
PROJECT_BRIEF.md's Open Decisions on single vs. multi-family scope).

### Family element profile (Step 4)

`GET /family/elements` aggregates elemental (Fire/Earth/Air/Water) balance across
all persisted people -- the first feature queried against the Step 3 data model
rather than computed in-memory. Weighting (Sun/Moon/Ascendant count double vs. the
other 8 planets; Ascendant excluded when `houses_reliable` is false) is a documented
design decision in `family_roles.json`'s `family_element_profile_rules`, not an
established astrological standard -- revisit there if output feels off. Ties in
`dominant_element` resolve to Fire > Earth > Air > Water by list order, not randomly,
but arbitrarily -- worth knowing since a 2-3 person family hits ties often.

```bash
curl http://127.0.0.1:8000/family/elements
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Test

```bash
cd backend
pytest -v
```

Tests run against the real `astro_test` Postgres database (not SQLite/mocks) --
each test runs inside a transaction that's rolled back afterward, so they don't see
each other's data. Schema is created directly from the SQLAlchemy models rather
than via Alembic (equivalent for testing purposes; Alembic is for tracking real
schema evolution).

`tests/test_chart.py` runs the full pipeline against a real chart (Feb 21, 1987,
5:00 PM, Moscow) as an integration fixture. No independently-verified reference
output (e.g. from astro.com) was available for that exact chart when this was
written, so the test asserts facts that are verifiable without trusting this
codebase (Moscow's historical UTC offset, the Sun's zodiac sign for that date) plus
structural invariants (valid house/degree ranges, Ascendant/MC consistency). If you
have verified third-party output for that chart, drop the exact values into
`EXPECTED_*` constants there for an exact-match regression test.
