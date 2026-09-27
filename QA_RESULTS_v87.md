# Linguist-X Passenger v87 — Reference Gate Acceptance

**Release scope:** One visual change, isolated to the gate area in the existing Live flight band. The approved reference is the two-tier glass tile with a large gate number and a full-width Guide Me row. The upper-right arrow is absent. Existing Wordly splash, weather, flight data, orb, inbox, and credential handling remain in the application.

## Rendered browser checks (not mockups)

The production passenger HTML, full inline application logic, wayfinder stylesheet and JavaScript were rendered in Chromium using the released files. Cloudy weather was supplied as a local image fixture to avoid contacting live providers. The Wordly splash was bypassed solely for capture. On each viewport the gate card was inspected in its default Live state.

| Viewport | Gate size | Guide Me row | Gate identifier | Overlap with flight data |
| --- | --- | --- | --- | --- |
| 390 × 844 | 150 × 168 px | 149 × 56 px | C9 | None |
| 410 × 900 | 150 × 168 px | 149 × 56 px | B34 | None |
| 320 × 600 | 127 × 148 px | 126 × 48 px | B34 | None |

**Interaction check:** On the actual rendered app, a single click on the visible Guide Me button opened `#lxGuideLens` immediately. Back closed the lens and restored the same expanded two-tier gate tile. There was no second app confirmation. No browser JavaScript errors were observed in those checks.

**Design structure:** A single refractive card with an upper gate label/number area, a full-width horizontal glass divider, and a separate lower action row. The row retains a circular directional glyph and a small *right* chevron. There is no glyph or disclosure arrow in the upper-right corner. Long gate identifiers use size-aware typography. Gate status and history behavior are still delegated to the existing flight data logic.

**Coverage:** The unit suite and integrity verifier cover HTML preservation, the service worker cache bump, long-identifier handling, navigation geometry, service/local credential behavior, and backend/API security. The simulator cannot establish physical compass accuracy; live GPS/orientation/camera still require on-device permission and field acceptance. The lens reports only the straight-line bearing to Ashburn Metro, not an indoor walking route.

**Credential handling:** The private one-time provider key bootstrap is carried forward from v84 and is deliberately excluded from Git and the public checksum manifest. The personalized ZIP is secret-bearing and must be kept private. No keys are printed in this report.
