# Backend

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

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

Interactive docs at `http://127.0.0.1:8000/docs`.

## Test

```bash
cd backend
pytest -v
```

`tests/test_chart.py` runs the full pipeline against a real chart (Feb 21, 1987,
5:00 PM, Moscow) as an integration fixture. No independently-verified reference
output (e.g. from astro.com) was available for that exact chart when this was
written, so the test asserts facts that are verifiable without trusting this
codebase (Moscow's historical UTC offset, the Sun's zodiac sign for that date) plus
structural invariants (valid house/degree ranges, Ascendant/MC consistency). If you
have verified third-party output for that chart, drop the exact values into
`EXPECTED_*` constants there for an exact-match regression test.
