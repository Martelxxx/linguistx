# v92 gate-card acceptance

- Replaced viewport-driven gate text dimensions with container-width scaling.
- Maintained the original two-zone glass card and stronger separator.
- Reduced card height to a fixed width-to-height ratio of 0.88.
- No gate tips or top-right arrow; Guide Me opens the lens directly.
- Browser-rendered widths 320, 375, 390, 740, 824, 1100; six gate-label lengths.
- Preserved the weather scene, other Passenger views, and private credential bootstrap.
- No physical-device sensor result is claimed.

Run `python3 quality/verify_v92.py` for source tests and manifest verification.
