# Linguist-X v74 — Local QA record

**Release:** v74 · September 23, 2026  
**Scope:** Passenger app integration foundation and mobile-only internal checklist.  
**These tests are not actual Wordly, AES67 or installed iOS/Android acceptance tests.**

| Check | Method | Result |
|---|---|---|
| Gateway contract and deterministic failure matrix | `python3 -m unittest discover -s tests -v` | 11 tests passed (4 existing + 7 new). |
| Local application HTTP endpoints | Local `run.py` plus fixture; session, invite, join, feed, state, revoke, demo cleanup, assets | Passed. |
| JavaScript syntax | Node syntax check on executable inline scripts, excluding embedded JSON | Passed. |
| Desktop internal tracker | Chromium static render with mocked fetch, 1440px | Shows 10/10 prototype; 1/32 contractual verified. |
| Mobile-only appearance | Chromium static render with mocked fetch, 390px | Internal panel hidden. |
| Integration fixture UI | Chromium with mocked gateway responses | Test caption displayed, injected Wordly outage cleared caption and displayed failure; no JS exceptions. |
| PWA update | New v74 service-worker cache version | Source inspected; full installed-PWA upgrade not independently tested. |

**User-provided verification:** UI-09 scanning marked done based on the user’s explicit confirmation of all six earlier checklist tests. Device logs and independent retest were not supplied. MG-07 in-app notifications marked done on explicit user approval; fixture tests cover the new status/failure mapping. This internal signoff is not AV-ation’s Final Acceptance.

**Open validation:** production Wordly entitlement and gateway, live audio/text, AES67 path, secure venue invitation issuer, connected media telemetry, native TestFlight/Google Play builds, real Wi-Fi/cellular transitions, lock-screen and call behavior, VoiceOver/TalkBack, and full Exhibit C M AC 01–08 evidence.
