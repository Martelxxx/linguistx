# Linguist-X Passenger v86 — Gate Card Reference Correction

## Request implemented

- The top-right ↗ affordance is disabled on both gate states. A small text-only discovery cue remains on the closed card.
- The **existing gate card** expands in place; no duplicate floating gate panel or full-page scrim is introduced.
- The expanded tile contains the gate label, large gate number, a continuous frosted-glass surface, an integrated dividing hairline and an icon/Guide Me/chevron bottom action. Its original weather refraction is retained.
- Tapping the bottom Guide Me action enters the lens immediately. Any native OS permission prompt remains mandatory when required.
- The original flight details control remains available. Wordly splash, Home, orb, Live transcript and backend behaviors were not redesigned.
- Compass/geolocation behavior from v83 remains unchanged; Ashburn Metro remains a reference point only, not an indoor route.
- v84's owner-only persistent credential setup and private one-time handoff remain unchanged. The personalized ZIP is **secret-bearing** and must not be shared or committed.

## Verification performed

- Browser-rendered the actual Passenger document with the release stylesheet and script at 390 × 844. Closed card: 101 px wide, 88 px high, action hidden, no generated corner arrow. Expanded: 107 px wide, 128 px high, action visible, no corner arrow. One tap on Guide Me produced one lens without a second in-app confirmation. Zero page-script exceptions.
- Ran Node JavaScript syntax checks, pure bearing/compass checks, the launcher credential migration tests, and the full unittest regression suite.
- Public SHA-256 release manifest excludes personal provider keys and local `.env`; packaging checks separately confirm the one-time private handoff is present.

## Device acceptance still needed

Physical mobile testing for true-north compass heading, accuracy rejection, screen rotation, browser camera/geolocation permission behavior and safe route interpretation is still necessary. A browser visual test cannot certify physical sensors or provide indoor navigation.
