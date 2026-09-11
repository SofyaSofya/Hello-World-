# First prompt to give Claude Code

Copy/paste something like this into Claude Code once you've put `PROJECT_BRIEF.md` and
`family_roles.json` in your repo root. This reflects decisions already made — don't
re-litigate them, just build:

---

I'm building the app described in PROJECT_BRIEF.md, using family_roles.json as the
astrological ruleset. Decisions already made, treat these as fixed:

- Backend: Python/FastAPI + Postgres (Postgres comes later — see step 2 below).
- Chart calculation: pyswisseph (Swiss Ephemeris).
- House system: Placidus by default, auto-fallback to Whole Sign above ~66° latitude
  where Placidus is mathematically undefined. Vedic mode always uses Whole Sign.
- Timezone handling: auto-resolve lat/lon + date to a UTC timestamp (timezonefinder +
  zoneinfo/tzdata for historical offsets, including DST). Store the resolved UTC
  timestamp as canonical. Surface the resolved local-time/offset back to the caller for
  confirmation. Support an optional manual UTC-offset override for edge cases pre-1970s
  data or disputed regions.
- Unknown birth time: support a documented fallback (noon chart with houses flagged
  unreliable) rather than blocking chart creation.

Build in this order — smallest useful slice each time, not the whole app:

**Step 1 (done/in progress): Chart calculation endpoint.**
Given birth date, time, lat/lon, return planet positions (sign, degree, house) and
aspects between planets, using the orb rules in family_roles.json's
`planetary_thread_rules`. Test against a known birth chart to verify ephemeris
accuracy before building anything on top of it.

**Step 2 (done): In-memory thread detector — no database.**
Pure functions (`calculate_aspects`, `find_threads`), tested against 3 fixture charts
(deliberate exact match, near-miss outside orb, no-overlap negative control). Validated
— the detector produces non-noisy, interesting output.

**Planet filtering (decided, apply this now if not already applied):** the thread
detector should default to `personal_planets` + `social_planets` from
family_roles.json's `planetary_thread_rules.planet_filtering` (Sun through Saturn),
excluding `generational_planets` (Uranus, Neptune, Pluto) by default. Their orbits are
slow enough (84-248 years) that shared placements across family members are mostly a
function of birth-year proximity, not a real family-specific pattern — that signal
belongs to the generational cohort lens feature (step 5) instead. Expose inclusion of
generational planets as an opt-in flag, and label any such results as "generational"
rather than "personal" threads if a caller opts in.

**Step 3 (current): Family tree data model + Postgres.**
`people`, `relationships`, `charts` tables per PROJECT_BRIEF.md's data model section.
Wire the existing chart-calculation and thread-detector logic to read from persisted
people/charts instead of in-memory lists, without changing their internal logic.

**Step 4 (next): Family element profile.**
First feature built against the persisted data model — query all people in a family,
aggregate elemental (Fire/Earth/Air/Water) balance across their charts, and return a
family-level summary. This is a good smoke test that the data model from step 3
supports real multi-person queries before building anything more complex on top of it.

Ask me clarifying questions about anything ambiguous before writing code, and stop
after each step so we can review before moving to the next.

---

Why this order: step 1 proved the ephemeris math is correct. Step 2 proves the
flagship feature (the thing that makes this app different from a single-person
astrology app) is actually interesting, using pure functions that are fast to test and
cheap to throw away if the logic needs rework. Step 3 — the database and family tree —
is comparatively low-risk, well-understood CRUD work, so it's saved for last, once the
riskier assumption is validated.
