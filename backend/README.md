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

Known open issue: outer planets (Uranus/Neptune/Pluto) move slowly enough that any
two people from the same astrological generation will share several "threads"
regardless of family -- not yet filtered or distinguished from personal-planet
threads. See PROJECT_BRIEF.md's generational cohort lens (feature 7); this needs a
decision before the thread list is meaningful for real families.

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
