# v78 Wordly Splash Morph

This release intentionally changes only the launch presentation. It does not redesign the Home screen or alter passenger navigation, scanning, flight selection, live translation state, Demo/Integration behavior, or the mobile requirements ledger.

The destination is not hard-coded. The browser measures the existing Home footer attribution at runtime and animates temporary visual layers into those exact coordinates. This keeps the approved footer as the single source of truth across viewport sizes.

## Implementation details

The feature is isolated in three named blocks in each mobile surface: `#lx-wordly-splash-styles`, `#lxWordlySplash`, and `#lx-wordly-splash-script`. The Home attribution remains the source of truth. At transition time the browser measures `#welcome .home-powered span` and `#welcome .home-powered img`, creates temporary fixed-position visual copies, and animates them into those live rectangles. The copies are removed and the original footer is revealed on completion.

The 2-second hold is not a loading gate and does not wait on external APIs. `prefers-reduced-motion` uses a short fade rather than spatial travel.

## Regression result

40/40 Python tests passed and the v78 release verifier passed. Chromium DOM/visual QA verified initial, in-flight, final, and reduced-motion states without page errors.
