# Linguist-X Passenger v94 — Compact Flight Card / Full-Bleed Guide Me

## Scope

The v93 Gate / Guide Me UI was refined without changing flight lookups, weather retrieval, translation, the navigation lens, or the persistent provider-key handoff.

- Removed the previous viewport-driven minimum height of the entire flight card. Its height follows the flight content and gate card instead.
- Kept the gate card compact while retaining two glass sections and a full-size gate value.
- Eliminated the inherited `justify-content: center` grid-track shrinkage by explicitly declaring a full-width `minmax(0, 1fr)` column. The Guide Me background and divider now span the card's entire inside width.
- Centered CURRENT GATE at the top of the upper panel and tightened number-to-divider space through the shorter card geometry.
- Preserved the single Guide Me action. The in-app lens opens on that action's first click and Back returns directly to Live. Platform camera, location, and motion permissions remain subject to browser/device controls.
- Advanced the service-worker shell cache version to `linguist-x-v94-gate-sizing-and-divider`.

## Verification

- 35 Chromium-rendered geometry cases (7 viewports x 5 gate lengths): heading center error ≤1.5 CSS px; row left and right inset = 1 CSS px (the card's border); content does not overflow; Guide Me label does not overlap the compass icon or chevron; distinct divider exists; no onboarding popup.
- In each of seven viewport configurations, clicked Guide Me once to verify the lens opens and Back closes it without expanding Flight Details.
- Browser screenshot created at a 390 px CSS viewport with device scale factor 2.
- 72 automated Python tests passed; one historical test skipped. The latest active gate tests assert the corrected layout rules.
- Both HTML entrypoints embed identical copies of the canonical `gate-card.css`, `wayfinder.css`, and `wayfinder.js`.
- The personalized credential bootstrap is kept byte-for-byte unchanged and excluded from the public release manifest. The `.env` file is not packaged.

## Still requires a real device

Sensor permission and compass heading behavior have not been verified on physical iOS or Android hardware in this release. The existing implementation retains its permission and accuracy limitations.
