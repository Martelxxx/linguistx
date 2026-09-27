# Linguist-X Passenger v80 — Gate → Guide Me prototype

## Change and scope

Added an isolated, low-noise affordance to the existing Live **gate card**. The card's source DOM receives only an accessible button identity; its existing gate value and previous-gate action remain. A pointerless, one-time hint communicates tap-to-expand without changing layout. The tap expands a light-glass panel with Guide Me. Selecting it morphs the panel bounds into a full-screen lens with a center-screen translucent arrow, dark navy/cyan glass language, selected-language labels, reduced-motion fallback and keyboard/back close support. The v78 Wordly launch splash and all other passenger surfaces are untouched.

The lens points toward the **Ashburn Metro station, Virginia** reference coordinate (39.00497, −77.49120) only if it has permissioned, sufficiently accurate location and a fresh, supported absolute device orientation. It displays straight-line distance, not walking distance. Without suitable data it shows non-directional status and offers a separately labeled SIMULATED preview with ±45° virtual-heading controls. No QR code is used. This prototype **does not** recognize airport signs, infer an A1/A2 gate sequence, determine indoor floors, fetch Google Maps, calculate a pedestrian route, locate a gate, or claim AR spatial anchoring. The card's gate label is contextual; the actual lens target is Ashburn Metro.

## Technical checks

- Source baseline: subtract the three v80 passenger HTML additions and both documents reproduce the exact v79 SHA-256 baselines. The earlier v75/v78 Wordly-splash historical baseline also passes.
- Pure geometry: 7 cases (north/east/west, reverse direction, distance, ±180-degree wrap) pass in Node; no external provider involved.
- Browser JavaScript: `node --check` passes for `wayfinder.js` and the updated `sw.js`.
- Static service: both the local and ASGI allowlists serve the new CSS/JS with explicit content type. Same-origin sensor Permissions-Policy replaces v79's disabled geolocation policy.
- Privacy/lifecycle: code requires deliberate camera/position/orientation requests, stops media tracks and geowatches on exit, does not persist/transmit the lens's coordinates/frames, and suppresses the directional arrow for missing/inaccurate/stale readings.
- PWA: cache version bumped, both new assets included, v80 query-suffixed assets resolve from the cached pathname; `/api/` remains outside the shell cache.
- Existing flight/voice/weather and local-key-entry logic unchanged; no provider secrets committed or included in ZIP.
- Full prior regression suite and new v80 tests executed locally: **62 unittest cases passed** (including 9 v80 cases); v80 standalone pytest also passed 9 cases.

## Not established / real-device acceptance

- A managed Chromium browser policy (`URLBlocklist: ["*"]`) prevented this environment from opening local app URLs for interactive screenshot/camera/compass QA. Static HTML/CSS inspection, syntax and source-baseline tests do **not** replace visual user acceptance.
- Real iOS/Android GPS, magnetic heading, camera permissions, heading reliability and accessibility usability have **not** been physically tested. Camera and geolocation often need HTTPS or same-device loopback, not an insecure LAN preview.
- Test destination coordinates are a point near Ashburn Metro station, not a verified entrance, safe walkable route or Google Maps directions. Indoor navigation will require airport-authorized map/graph, localization, trustworthy gate feeds and route constraints.
- Wordly live translation media remains unconnected. No contractual acceptance is inferred: `requirements-progress.json` is unchanged.

## Local manual acceptance script

1. Run `python3 start.py`, complete normal Welcome → flight → Live without changing the prior screens or the two-second Wordly splash.
2. Observe one subtle gate-corner cue and a nonblocking, one-time localized hint. Tap the gate; verify the existing flight band does **not** expand and the gate panel does.
3. Select Guide Me. On an HTTPS real phone, grant requested permissions only if comfortable. Verify the camera backdrop and center arrow update while turning; compare compass sense against known cardinal directions **without walking or treating it as a route**.
4. Deny location and camera: the view should communicate uncertainty, not invent navigation. Select the SIMULATED preview and rotate the virtual heading.
5. Go back. Verify sensor indicators turn off, gate card/Live resume, previous-gate history and Flight details still work, and Guide Me never asks for Wordly account access.
6. Repeat with reduced-motion preference, keyboard escape/focus and each of the six UI languages.

Execute `python3 quality/verify_v80.py` for the manifest, Node syntax, existing regression suite and v80 tests. Historical `quality/verify_v78.py` and `verify_v79.py` target older release bytes and are not v80 release gates.
