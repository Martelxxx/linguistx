# Linguist-X Passenger v95 — Dynamic Gate Typography

- Baseline: complete v94 Passenger release, including local credential bootstrap and Guide Me lens.
- Gate heading and Guide Me action retain the existing font size unless their **rendered glyph width** exceeds their available space.
- The heading maintains approximately 12 px of additional breathing room on each side at compact widths. If necessary, it scales down modestly; normal-size text is restored when a shorter translation appears.
- Recomputed for translated text changes, action text changes, gate-card resizing, screen resizing, and completion of web-font loading.
- No change to the gate-card dimensions, glass styling, Guide Me separator, passenger flows, or provider credentials.
- Browser-verified at viewport widths 320, 375, 390, 440, and 740 px: French shrinks as needed; English restores to its original size; all six supported translations fit at 320 px.
- Guide Me opens the in-app lens on the first tap. Native browser motion/location/camera permission prompts remain browser-controlled.
- Regression suite: 78 tests passed; 1 skipped. Physical iPhone compass and production provider connections not retested in this typography-only release.
