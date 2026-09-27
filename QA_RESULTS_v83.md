# Linguist-X Passenger v83 — verification

## Scope
Recovered original v80 → v81 → v82 Passenger application, with additive refinement of the
Gate/Guide Me assets only. Baseline passenger HTML is compared against the historical
approved source after removing the small gate hook and the stylesheet/script references.

## Automated evidence
- Legacy 69-test regression suite (including v83-specific contracts): pass.
- North/east/west/south, screen rotation, poor compass quality, and relative-yaw rejection
  are covered by pure sensor/geometry tests (12 assertions in the dedicated test).
- CSS and JavaScript are isolated in `wayfinder.css` and `wayfinder.js`.
- Service-worker cache is bumped to `linguist-x-v83-compass-rose`.
- The ZIP manifest includes hashes of all shipped source/assets, excluding .env and
  the manifest itself. The verifier checks integrity, JS syntax, and regression tests.

## Not verified here
Physical mobile magnetometer/GPS calibration, OS permission UX, and real camera
performance. Desktop automated tests cannot establish heading accuracy in a real terminal.
The lens is a straight-line reference bearing, not an airport indoor walking route.
