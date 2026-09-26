# Linguist-X Passenger — Developer Handoff Guide (v78)

This repository is the passenger/mobile application only. It intentionally does **not** contain the fleet dashboard, remote support center, commissioning application, management center, or evidence console.

## 1. Product invariants — do not casually change

The passenger experience is the result of 75+ iterative releases. Treat the current interaction and visual language as a locked product baseline unless a product owner explicitly approves a UX change.

Preserve:
- the six-language welcome → flight discovery → confirmation → Live journey;
- the centered Linguist-X identity, restrained neumorphic/glass visual language, living orb / bridge-X behavior, typography, spacing, animation timing, and reduced-motion behavior;
- account-free access;
- progressive flight search, boarding-pass scanning, manual fallback, Live captions, text-only mode, caption scaling, recent announcements, notifications, flight details, destination weather, and settings behavior;
- the distinction between public passenger navigation and protected translation-session access;
- explicit labeling of fixture content as **TEST DATA** and the rule that Integration mode must never silently fall back to simulated announcements;
- the desktop-only internal checklist and test controls remaining outside the passenger phone.

## 2. Fast orientation

Recommended local development start:

```bash
python3 start.py
```

Open `http://127.0.0.1:8765/` for the internal desktop preview or `/passenger-only.html` for the passenger surface without internal controls.

Production-style local transport:

```bash
python3 -m pip install -r requirements-production.txt
python3 start_asgi.py
```

Do not expose the local `run.py` server publicly. `passenger_asgi.py` is the supported production-style HTTP entry point, but real infrastructure, load testing, live provider contracts, and native-device acceptance remain separate release gates.

## 3. Source-of-truth files

| File | Responsibility | Change caution |
|---|---|---|
| `passenger-only.html` | Passenger-facing HTML/CSS/JS surface | Highest UX regression risk. Preserve visuals and interactions. |
| `index.html` | Same passenger experience plus desktop-only internal checklist/test controls | Never use as the public passenger build. |
| `run.py` | Local server, provider adapters, scanning/voice/weather APIs, static delivery | Development only; keep behavior aligned with ASGI routes. |
| `passenger_asgi.py` | Production-style ASGI HTTP boundary | Production transport, origin enforcement, headers, health/readiness. |
| `integration_bridge.py` | AV-ation guest-gateway contract and server-only guest handles | Authorization boundary. Fail closed. Never expose provider tokens. |
| `fixture_gateway.py` | Deterministic loopback integration fixture | Test-only. Must remain impossible to enable in production. |
| `shared_guest_store.py` | Optional Redis-backed cross-worker guest/discovery state | Required for configured production gateway multi-worker use. |
| `runtime_security.py` | Environment policy, secure cookie construction, baseline headers | Security-critical shared policy. |
| `app_logging.py` | Privacy-preserving structured audit logging | Do not add payload, URL, caption, token, invitation, or passenger data. |
| `sw.js` | Small same-origin shell cache | Never cache `/api/` responses or translated content. |
| `requirements-progress.json` | Mobile-only checklist ledger | Edit here, then run `python3 sync_progress.py`. |
| `sync_progress.py` | Validates and embeds checklist ledger into `index.html` | Does not approve requirements; only synchronizes reviewed evidence. |
| `developer-documentation.html` | Comprehensive internal engineering documentation | Internal-only route; keep aligned with architecture changes. |

## 4. Architectural boundaries

Browser code never receives `LX_GATEWAY_TOKEN`, provider service credentials, or upstream guest bearer tokens. The browser receives only an opaque HttpOnly `lx_guest` handle. The server maps that handle to a short-lived upstream guest token. In production, configured gateway state must be shared through Redis rather than per-process dictionaries.

The local fixture is intentionally explicit and deterministic. It simulates the **application contract**; it is not Wordly, AES67, or proof that live translated media exists.

`run.py` and `passenger_asgi.py` expose matching application-level APIs. When adding or changing a route, update both transports or intentionally document why a route is local-only.

## 5. Safe change workflow

1. Start from the latest tagged/released ZIP or repository commit.
2. Read `developer-documentation.html`, `INTEGRATION_CONTRACT.md`, and this guide before changing behavior.
3. Make the smallest possible change.
4. Do not refactor passenger markup/CSS while implementing unrelated backend work.
5. Update tests before changing security-sensitive behavior.
6. Run `python3 -m unittest discover -s tests -v`.
7. Run `python3 quality/verify_v78.py`.
8. For tracker changes, edit `requirements-progress.json`, then run `python3 sync_progress.py` and rerun verification.
9. Manually exercise the affected passenger path in both `index.html` and `passenger-only.html`.
10. Record the release change in a versioned QA/release note.

## 6. Security rules that must survive future work

- Production gateway URLs are HTTPS only; loopback HTTP exists solely for local fixtures.
- Never redirect credential-bearing gateway requests.
- Keep guest/session authorization server-side.
- Invalid, expired, revoked, or mismatched invitations must fail closed at the protected translation boundary.
- Public flight navigation is not the same thing as translation authorization.
- Test fixture endpoints are loopback-only and absent in production.
- No raw camera frames, raw barcodes, passenger names, reservation references, captions, guest tokens, gateway tokens, or provider keys belong in logs.
- Do not cache `/api/` responses or translated content in the service worker.
- Production JSON mutations require exact approved origin checks.
- Production guest cookies are HttpOnly, SameSite=Strict, path-scoped, and Secure.

## 7. Documentation discipline

A developer changing architecture, routes, environment variables, session semantics, service-worker caching, security policy, or the passenger state machine must update `developer-documentation.html` in the same change. A code change is incomplete if the documentation becomes false.

## v78 launch splash invariant

The launch experience now includes a deliberate Wordly shared-element transition. On each document load, a centered `Powered By` + large Wordly wordmark is held for 2,000 ms. The wordmark then travels to the **actual measured geometry** of `#welcome .home-powered img`, while the label cross-fades/reflows to the footer's existing `Translations powered by` text. The Home footer remains the source of truth; do not hard-code its destination coordinates.

The implementation is isolated in `#lx-wordly-splash-styles`, `#lxWordlySplash`, and `#lx-wordly-splash-script` in both `index.html` and `passenger-only.html`. It must run only once per document load, must never replay when navigating back Home, and must not mutate passenger application state. `prefers-reduced-motion: reduce` receives a short fade instead of spatial motion. Any future footer spacing/typography change must be regression-tested to ensure the splash still lands exactly on the live footer geometry.
