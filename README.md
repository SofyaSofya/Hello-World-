# Family Astrology App

See [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) for the full concept and roadmap, and
[`family_roles.json`](family_roles.json) for the encoded astrological ruleset
(family role -> house/planet mapping per system, plus aspect orb rules).

## Current slice

The smallest working piece, per the brief's own build order: one API endpoint that
turns a birth date/time/location into a verified individual birth chart (planet
positions, houses, aspects). No family tree, thread detector, or frontend yet --
chart accuracy is the foundation everything else depends on.

- **Backend**: Python / FastAPI
- **Ephemeris**: [`pyswisseph`](https://pypi.org/project/pyswisseph/) (Swiss
  Ephemeris), Moshier semi-analytical model -- accurate to ~1 arcsecond and needs no
  external ephemeris data files.
- **House system**: Placidus.
- **Timezone handling**: birth date/time is taken as local civil time; the timezone
  is auto-resolved from latitude/longitude (via `timezonefinder` + `zoneinfo`,
  correctly handling historical offsets/DST rules) and the resolved timezone, UTC
  offset, and UTC datetime are returned in the response for confirmation -- callers
  never compute a UTC offset themselves.

See [`backend/README.md`](backend/README.md) for setup and how to run it.
