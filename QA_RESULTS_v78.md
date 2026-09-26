# Linguist-X Passenger v78 — QA Results

## Scope
Intentional Wordly launch splash/shared-element transition only. The Home screen layout and established passenger workflows remain unchanged after launch.

## Automated checks
- Full Python regression suite: **40/40 passed**.
- `python3 quality/verify_v78.py`: **passed**.
- JavaScript syntax validation: **passed** for `index.html` and `passenger-only.html`.

## Chromium no-network visual/DOM QA
A 390 × 844 mobile viewport was exercised using the actual v78 `passenger-only.html` source with only the local Wordly asset inlined by the test harness. No application code was changed for this check.

Observed:
- At 350 ms: splash visible with `Powered By` and the large Wordly wordmark.
- At ~2.2 s: shared-element transition active; three temporary visual layers present (continuous logo plus outgoing/incoming label layers).
- At ~3.2 s: splash and temporary layers removed; existing Home footer visible and authoritative.
- Browser console/page errors: **none**.
- Near animation completion, the temporary Wordly logo was within approximately **0.4 CSS px** of the real footer logo rectangle; the final `Translations powered by` label was within approximately **0.4 CSS px** vertically and exactly aligned horizontally/width-wise in the captured measurement.
- `prefers-reduced-motion: reduce`: 2-second hold followed by a short fade, no spatial ghosts; footer becomes visible normally.

## Visual contract
- Centered `Powered By` + large Wordly wordmark.
- Hold: 2,000 ms before transition begins.
- Wordly mark moves continuously down and shrinks to the live Home footer logo geometry.
- Label transitions to the existing `Translations powered by` footer text while moving into the footer geometry.
- Home reveals underneath during the movement.
- The transition runs once per document load and does not replay when navigating back Home.
- Destination coordinates are measured at runtime; they are not hard-coded for one device size.
