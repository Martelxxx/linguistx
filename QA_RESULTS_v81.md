# Linguist-X Passenger v81 — Native Guide Me

## Build ancestry and visual scope

Restored source: exact v80 Gate Wayfinder Lens ZIP from the Linguist-X Library. This build edits **that archive** directly, preserving its v79 service-recovery changes and v80 permissioned wayfinder logic. The only Passenger HTML changes are its two isolated `wayfinder.css`/`wayfinder.js` cache-version references; the original Home/Live/Wordly document remains otherwise unchanged. `start.py`, release docs, tests and the PWA cache name are versioned.

The upper-right `↗` gate indicator has been removed. A quiet lower-edge `GUIDE ME ›` caption and time-limited localized discovery hint are the only persistent/new gate affordances. Tapping expands the same glass material into a small contextual panel; its Guide Me row takes the user into the new light, atmospheric lens. The lens samples the exact weather background used by the flight band, rather than introducing a visually unrelated dark takeover. The existing v80 camera/GPS/compass lifecycle, stale/accuracy checks and optional SIMULATED preview are retained.

## Acceptance boundaries

The destination is Ashburn Metro station, Virginia, as a demonstration reference. Navigation is a **straight-line bearing** given sufficiently accurate location and a trustworthy compass reading. It is not an indoor airport walking route, safe path, flight gate direction, or camera-based recognition. The lens does not transmit sensor readings or persist position. Real iOS/Android camera and heading accuracy must still be confirmed on an HTTPS deployment or allowed secure context. Translation fixture is not live Wordly media.

## Tests

- v80 geometry, historical passenger-source hashes, local service recovery, guest security and ASGI behavior: preserved in suite.
- v81 adds source-isolation, existing flight-weather inheritance, accessible gate affordance, sensor-boundary preservation and cache/syntax contracts.
- Browser visual regression (Chromium via isolated HTML injection, no network): inspected narrow/tall phone and desktop mock-phone layouts, collapsed gate, expanded gate, unavailable-sensor lens, and simulated compass lens. Browser console showed no page errors. Simulated navigation remains explicitly labeled.
- Full regression suite: 67 tests passed. An isolated Chromium interaction test additionally verified Gate B34 → expanded Guide Me → mocked location + absolute heading → **Target ahead**, 1.1 km → Escape and location-watch cleanup, with no JavaScript errors.
- Manifest must pass `python3 quality/verify_v81.py` before distribution.
