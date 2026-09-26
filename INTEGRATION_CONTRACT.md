# Linguist-X v74 · Account-free mobile integration boundary

**Scope:** Local architectural test fixture, volatile-caption client and adapter for account-free passenger sessions. **Not** a complete Wordly/AES67/installed-iOS/Android integration and **not** supplier authorization. Never publish the internal requirements checklist or enable its mode endpoint in a public deployment.

## Running

1. `cd` into this extracted package and run `python3 run.py` (Python 3.10+).
2. Open `http://127.0.0.1:8765/` in a desktop browser. The *Translation source* control is **outside** the phone, above the agreement checklist, and defaults to **Demo** on each server start.
3. Demo: sample announcements, optionally independent Aviationstack flight lookup, optional TTS. No live Wordly claims.
4. Integration: stops sample announcement simulation, discovers sessions via the local server's AV-ation gateway adapter, and reports unavailable if not configured. Tap **Check gateway connection** for a probe. Switching does not require passenger login or registration.
5. For a configured contract test, copy `.env.example` to `.env` and supply an approved `LX_GATEWAY_URL` and `LX_GATEWAY_TOKEN` **on the local server only**, then restart `run.py`. Do not put keys into HTML or URLs. `.env` is ignored from ZIP construction and must be permissioned to the local owner.

**Important:** A Wordly API key is *not* itself an integrated audio service. AV-ation must first supply approved provider SDK/API rights and a gateway implementing this documented application contract, plus physical appliance/AES67 and native OS integration. The three existing keys serve different features; they do not enable Wordly translations. The current backend intentionally returns `media: "not connected"`. Neither actual spoken translation nor live translated text is wired into v72.

## AV-ation gateway contract (explicit adapter, not claimed Wordly endpoints)

All server-to-gateway requests use `Authorization: Bearer <LX_GATEWAY_TOKEN>` and are performed by `run.py`. The browser never sees the provider token. URL must be HTTPS except loopback for tests; no redirects or user-supplied URLs are followed. JSON bodies and responses are size-bounded.

| Operation | Method, route | Response required |
|---|---|---|
| Capability probe | `GET /v1/capabilities` | `{"ready":true,"sessions":true,"guestJoin":true,"deliveryStatus":true,"liveAudio":false,"liveText":false}` |
| Flight-scoped discovery | `GET /v1/sessions?flight=EK232` | `{"sessions":[{"id":"flight_EK232","title":"Gate A23","flightCode":"EK232","status":"active","languages":["en","fr"]}]}`. `status`: `active`, `paused`, or `ended`. Session IDs are opaque safe identifiers. Gateway must check site/tenant, flight and authorization. |
| Guest join | `POST /v1/guest/join` body `{"sessionId":"flight_EK232","language":"fr"}` | `{"guestToken":"opaque-expiring-scoped-grant","expiresIn":120}`. The gateway issues this as a limited guest grant **not** a Wordly credential or admin token; it must enforce session / venue / expiration / rate limit / revocation. |
| Delivery state | `GET /v1/guest/state` using `Authorization: Bearer <guestToken>` | `{"state":"connected"}` or `reconnecting`, `unavailable`, `ended`. State is a gateway report, not proof a passenger heard audio. |

A browser receives **only** an HttpOnly SameSite cookie pointing to an in-memory preview mapping. Scoped guest token is held on the server for at most the provider's expiration, capped to 1 hour. No account or password, and no translated content is stored by this adapter. The guest cookie is cleared upon leaving Live or switching to Demo. Rejected/missing gateway operations fail closed; no sample translations are substituted.

## Remaining integration and release work

- Implement real audio/text delivery via an AV-ation-controlled guest service and a media transport that can be consumed in native iOS and Android; verify Wordly grant and rights, AES67 routing, message/session/language correlation, call/lock screen behavior, and continuity.
- Bind authorized venue invites or QR codes, local/remote guest rate limiting, expiry/revocation, replay/CSRF protections, tenant/session isolation and independently measured delivery state to the gateway in a production architecture. Preview's loopback-only development control and process memory are **not** production authorization.
- Complete native builds, accessibility/security audits, PA emergency marker, telemetry, retention validation and all signed acceptance evidence. Agreement §§3,5–6 and Exhibits B–D govern; this adapter does not satisfy A03/A04/A07/A08/A11 or M AC cases on its own.
- Never run `LX_LAN=1` with this preview as a production service. Only browser requests originating from the host machine’s loopback address may change mode, including when LAN preview is enabled. Remote phones cannot change it. HTTPS is required in real deployment.

## Local tests

Run `python3 -m unittest discover -s tests -v`. Tests use a local mock of **this application contract**, not real Wordly. A passing contract test is evidence for the adapter implementation only, not contractual acceptance.


## v74: Explicit local integration fixture

Start with `python3 start.py` (or equivalently `LX_NO_SETUP=1 LX_ENABLE_FIXTURE=1 python3 run.py`) and visit `http://127.0.0.1:8765/`. Select **Integration** in the right-side desktop panel. A loopback-only fixture runs at `PORT+1` using a random, in-memory service token. It does not contact Wordly. Fixture mode is disabled by default, cannot run with `LX_LAN=1`, and must never be used in production.

Example fixture invitation: `http://127.0.0.1:8765/?lx_invite=DEMO-EK232`. The prototype requires selection of the matching flight and rejects a mismatching invitation. `DEMO-` codes are not production invitations. Actual invites must be issued by AV-ation with independently enforced venue, session, expiry, and revocation rules.

Additional *AV-ation application-contract* endpoints (not Wordly API endpoints):

| Operation | Route | Shape |
|---|---|---|
| Resolve invitation | `GET /v1/invites/resolve?code=...` | `{"flightCode":"EK232","sessionId":"fixture_EK232"}`; service-authenticated, reject bad/revoked grants. |
| Test text feed | `GET /v1/guest/events?after=0` | `{"source":"test-fixture","events":[{"sequence":1,"messageId":"...","sessionId":"...","language":"fr","kind":"text","text":"[TEST DATA] ..."}],"next":1}`; guest scoped and monotonic. |
| Status reason | Existing `GET /v1/guest/state` | Optional `reason` and `quality`, separately from the gateway `state`. Healthy gateway state does **not** prove delivered media. |

`/api/integration/events` returns **no translated text** when connected to a non-fixture gateway in v74. Live Wordly audio/text transport remains unimplemented. The fixture's `[TEST DATA]` caption is never presented as a real PA translation.

The mobile preview includes a six-message, in-memory-only caption buffer; adjustable caption scale; a text-only view; session/mode/expiry cleanup; bounded exponential retries; stale-content suppression; and textual failure states for network loss, Wordly loss, cloud loss, pause, ended session, expired license, unavailable language, call mute and grant revocation. Existing in-memory captions remain accessible during simulated call mute. No translated content is written into browser storage, a service worker, or local logs.

The **Test failure scenario** control lives outside the phone UI. It operates only on the opt-in fixture. Test evidence here concerns the adapter and client behavior, not production supplier integration. Real audio/text, AES67 routes, physical mobile build tests, background/call handling, cross-venue security, licensing and acceptance evidence remain open.

## Credentials and verification

For a real approved gateway, leave `LX_ENABLE_FIXTURE` unset and put `LX_GATEWAY_URL` (HTTPS) and `LX_GATEWAY_TOKEN` into the *server-local* `.env`. Never include provider keys in HTML/JS, a guest token or a QR link. A Wordly key alone is insufficient without approved SDK/API rights and an AV-ation gateway implementation.

Run `python3 -m unittest discover -s tests -v` to test the local application contract. The tracker records UI-09 as user-reported scan validation and MG-07 as user-approved in-app notifications; all other Exhibit C items remain open for their complete evidence.


## v75 correction — fail-closed fixture authorization

User-reported manual testing on 2026-09-23 passed groups 1–4 and 6 but **failed Test 5**: revoked/invalid/cross-flight warning states appeared while the passenger could navigate onward. In v75, negative fixture scenarios `invalid-invite` and `revoke-guest` clear existing fixture grants and reject **new joins, state reads and event reads** until the scenario returns to `healthy`. A supplied invitation must resolve to the same session **and** the originally discovered flight. Denied replacement joins clear the previous HttpOnly preview cookie. An upstream guest 403 evicts the local grant handle. The Live panel explicitly displays `ACCESS BLOCKED` and offers no fixture caption or live audio.

**Important authorization distinction:** Selecting flights, changing language, or navigating a public passenger page remains possible when the translation guest session is denied. It must never grant access to translated content. The healthy fixture continues to permit anonymous guest joining *without* an invitation because account-free venue discovery is a separate supported path. The `invalid-invite` scenario deliberately denies **all joins** (including no-invite attempts) so its negative test cannot accidentally succeed through that alternative path; this is development fixture behavior, not an assertion that production always requires invitations. Real venue scoping, issuer trust, rate limiting and security review remain unresolved.

After upgrading, run `python3 -m unittest discover -s tests -v`, start once with `python3 start.py`, and manually rerun **Test 5 only**. The five earlier user-passed fixture groups are recorded in `requirements-progress.json` and `QA_RESULTS_v75.md`. All actual media, native device and final acceptance work remains open.


## v77 developer handoff

The application contract above is unchanged by v77. The release adds maintainer notes throughout the core source and a comprehensive internal documentation page at `/developer-documentation.html`. The page is served by the local development server and by the ASGI runtime only when not in production; the production ASGI static route returns 404 for it. Any future change to `/api/integration/*`, `/v1/*`, guest-cookie semantics, invite binding, expiry/revocation, or event delivery must update this contract and the developer documentation in the same release.
