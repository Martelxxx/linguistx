# Linguist-X Passenger v91 — clean gate-card acceptance

## Scope

This is a rebuild from the v90 personalized package, not another overlay of versioned
CSS. `gate-card.css` is the single source for the two-section gate component. Its
contents are embedded unchanged into `index.html` and `passenger-only.html`,
so the card renders from the current HTML even when an older service worker
has cached earlier external wayfinder assets. The complete static card (label,
gate number, separator, circular navigation icon, Guide Me action, chevron)
is present in HTML before JavaScript executes. The v83–v90 gate overrides,
legacy gate expansion panel, dynamic action insertion and onboarding tooltip
have been removed from the active wayfinder assets.

The full-screen lens remains separately maintained in `wayfinder.css` and
`wayfinder.js`, also embedded unchanged in each Passenger HTML entrypoint.
The service-worker cache identifier is `linguist-x-v91-clean-gate-card`.

## Verification

- 63 current unit and integration tests: passed, with one explicitly skipped
  historical v75 byte-for-byte snapshot that cannot apply to the authorized
  v91 markup change. Older release-locked v78, v80, v81, v83, v86 and v87
  contracts are preserved in `quality/historical_release_contracts/` rather
  than falsely asserted against this new release.
- Offline Chromium browser checks passed at 320 × 640, 390 × 844,
  430 × 932 and 390 × 600 CSS pixels using the real Passenger HTML/CSS,
  with mocked camera, geolocation and orientation. In each viewport, the
  gate displays a separate action row, an explicit two-pixel separator,
  a circular icon, no upper-corner pseudo-arrow and no tooltip.
- One tap on Guide Me opens the lens, Back restores the gate, and synthetic
  compass-heading rotation of 90 degrees changes the target arrow by 90
  degrees. `quality/v91_previews/` contains the browser-rendered gate cards.
- The local HTTP app serves both updated Passenger entrypoints (HTTP 200).
- The private credential handoff, local persistence, API routes and settings
  scripts are byte-identical to v90. The launcher changes only its displayed
  version label from v88 to v91; credential behavior is unchanged. The ZIP is personalized and
  must be kept private; do not publish it or its bootstrap to source control.

## Limits

Physical iPhone and Android permission dialogs, compass calibration,
GPS reception and actual indoor positioning were not tested. As before,
Ashburn Metro is a geographic reference bearing, **not** a verified
walking route to an airport gate. The operating-system permission prompt
may still appear, but there is no additional in-app confirmation.
