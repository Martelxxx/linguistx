# Linguist-X Passenger — v95 source

This repository contains the complete Passenger application and release history
through v95: Home/Live journey, flight data, dynamic multilingual gate card,
Guide Me prototype, local backend, integration fixture, tests, and assets.

Run `python3 start.py` to launch the local preview. Service credentials are
stored outside this repository in `~/.linguist-x/provider_keys.env` and are
reused by future extracted versions. The personalized one-time file
`private_provider_keys.py` is **intentionally not committed**; it is excluded
by `.gitignore` and `.dockerignore`. On a new computer without saved keys,
`start.py` can prompt privately once. To rotate them, run
`python3 start.py --configure`. Never commit provider credentials.

Run `python3 -m pytest -q tests` and `python3 quality/verify_repository.py`
for the current source checks. Earlier version notes and historical release
contracts below describe their original releases, not the v95 behavior.

---

# Linguist-X Passenger v91 — Clean Gate Card

The Gate card was rebuilt as a single static two-section glass component.
The separate Guide Me row and compass icon are present before any JavaScript
loads; no tooltip and no in-app confirmation are used. The v83–v90 gate CSS
stack is no longer active. Source-of-truth styling is in `gate-card.css`;
`wayfinder.css` now holds only the navigation lens. Both are embedded into
`index.html` and `passenger-only.html` to avoid stale cached external assets.

**Start:** extract this personalized ZIP and run `python3 start.py`.
Your private provider handoff and durable local credential store are preserved.
Keep the ZIP private and do not commit `private_provider_keys.py`.

See `QA_RESULTS_v91.md` for acceptance evidence and limitations.

---

# Linguist-X Passenger · v81 — Native Guide Me

This release is built directly on the recovered v80 Gate Wayfinder package. Only the Gate → Guide Me experience has been visually revised. The existing Home, Live, Wordly splash, flight data, translation fixture, privacy boundaries, credentials, and service infrastructure are carried forward.

- Gate tile: removes the corner arrow and shows one understated bottom-edge “Guide Me ›” cue, plus a brief one-time discovery hint. Existing flight-card dimensions and gate-value layout remain unchanged.
- Expanded tile: retains the same translucent, weather-refractive material and reveals a calm Guide Me row.
- Guide Me lens: reuses the flight's actual weather-background asset, pale glass, slate/navy type, native circular controls, and a restrained shared-element transition. It no longer opens a visually unrelated dark blue takeover.
- Navigation behavior: preserves v80's explicit permissions, GPS/geodesic bearing, supported absolute orientation, camera lifecycle, confidence threshold, stale-heading suppression, and clearly labeled simulation mode. Ashburn Metro remains the prototype reference, **not a verified indoor route**.

Start with `python3 start.py` (then open `http://127.0.0.1:8765/`). For test evidence, see `QA_RESULTS_v81.md`; run `python3 quality/verify_v81.py`. The previous release notes follow.

---

# Linguist-X Passenger · v80

The passenger/mobile Linguist-X application with its established Wordly splash, Home → flight → Live journey, local service setup, and a **new, visually isolated Gate → Guide Me lens prototype**. The original Home, Live, and passenger flow is preserved. The Wordly/AES67 translated-media integration is **not connected**; fixture captions are test data.

**Start locally:** Run `python3 start.py` from this folder, then open `http://127.0.0.1:8765/` on **the same device**. On first start, private Terminal prompts recover Aviationstack, WeatherAPI and OpenAI optional keys, which are stored only in an untracked `.env`. To rotate keys locally, use `python3 start.py --configure`. Never commit keys or paste them into code.

**Try Guide Me:** In the Live page, tap the gate card with the subtle ↗ cue. Its expanded card contains the Guide Me action. The new lens asks permission for camera, location and device orientation, and aims its center arrow toward **Ashburn Metro station in Virginia** as a reference destination. The arrow is a straight-line bearing only, **not an airport route, walking instruction, optical/AI localization or turn-by-turn navigation**. If a reliable heading/location is unavailable, choose the clearly marked simulated design preview. No QR scan is needed. Compass/camera APIs require a secure browser context and supported phone sensors. A desktop browser may show only the simulated preview. All device data stays local to the browser lens; camera tracks and watches are stopped when it closes.

**Engineering/test:** See `DEVELOPER_HANDOFF.md`, internal `/developer-documentation.html`, `QA_RESULTS_v80.md`, and `INTEGRATION_CONTRACT.md`. Execute `python3 -m unittest discover -s tests -q` and `python3 quality/verify_v80.py`. Historical version verifiers intentionally target their original release bytes. Formal requirement acceptance remains unchanged.

Do **not** expose the local `run.py` preview publicly. Test remote phones using a reviewed HTTPS ASGI deployment, not insecure LAN development mode.
