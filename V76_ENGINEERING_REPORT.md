# Linguist-X v76 — passenger-code hardening report

**Scope:** Only the account-free passenger mobile application, local integration
fixture, API and test harness. Not fleet, remote support or other product tracks.

**Baseline:** exact v75 Guest Access Fix ZIP. The user explicitly reported that
v75 Test 5 passed on retest. The six test groups are `user-passed` in the mobile
ledger. This is *not* formal Exhibit C acceptance.

## What changed in this release

1. Removed Aviationstack HTTPS-to-HTTP credential-bearing fallback. An
   HTTP-only Aviationstack plan now gives an honest sanitized provider error
   instead of leaking the key over plaintext transport.
2. Removed automatic searching of old Linguist-X folders / ZIP archives for
   credentials. Optional service keys can still be specified in the current
   `.env` or process environment. Production reads secrets only from its
   process environment and never writes them to `.env`.
3. Introduced `runtime_security.py`: typed environment/port policy, rejection
   of local fixtures in production/LAN, HTTPS public-origin requirement,
   centralized guest cookies with Secure in production, and response headers.
4. Added separate Starlette/ASGI HTTP entry point `passenger_asgi.py`, retaining
   the existing API routes, response shapes and user-visible assets. Blocking
   upstream calls run in a bounded threadpool instead of blocking the event
   loop. The original `start.py` local launcher remains available, with no
   external dependencies needed for that path. `run.py` itself is local-only.
5. ASGI includes bounded streaming JSON bodies, same-origin POST checks,
   sanitized errors, request IDs, metadata-only negative-request audit records,
   loopback-only developer endpoints and health/readiness responses.
   The optional `start_asgi.py` disables URL-bearing Uvicorn access logs;
   the Dockerfile candidate also uses `--no-access-log`.
6. Redis-backed server-side guest grants and discovery have an optional
   production adapter; a deterministic two-instance test verifies joining via
   one instance, event access through the other, and shared revocation. Real
   Redis TLS, quotas and load testing remain outstanding.
7. Local fixture now uses an OS-allocated loopback port rather than port+1.
   The one-command Demo / Integration toggle works as before.
8. Added Python dependency manifest, explicit runtime pins, `.gitignore`,
   CI starter, optional ASGI container candidate, tests, and this limitations
   register. Dependency hashes, historical secret scans, legal rights and
   scans requiring network or the real Git repository remain open.
9. Updated the mobile-only ledger to reflect all six user-reported test groups
   passing; formal completion remains **1/32**, prototype **10/10**.
10. Rotated the service-worker cache name so a v75 offline shell does not remain
   after the v76 update. Offline shell content is otherwise unchanged.

## Preservation evidence

- `passenger-only.html` is byte-for-byte identical to the input v75 package.
- `index.html` is byte-for-byte identical **outside** the embedded JSON
  checklist `#lxrtData`, which was synchronized from the v76 ledger.
- No passenger CSS, executable passenger JavaScript, markup outside the tracker,
  artwork, navigation, translations, animations, or scanner logic was edited.
- `quality/verify_v76.py` and `tests/test_v76_engineering.py` compare the exact
  v75 SHA-256 baseline after normalizing only the ledger JSON region.
- New transport contract tests exercise guest joins, revocation, wrong-flight
  invitations, cookie cleanup, body-size limits, same-origin handling, and
  static asset bytes.
- **Physical iOS/Android rendering and scanning were not rerun in this release.**
  The byte comparison is stronger than an incidental static screenshot for
  unchanged CSS/JS but does not prove every browser/runtime combination.

## Run locally

```bash
python3 start.py
# Open http://127.0.0.1:8765/ ; toggle Demo / Integration in the right panel.
```

The local one-command launcher remains `http.server` deliberately and is not
appropriate for production. To test the separate ASGI transport after installing
its dependencies:

```bash
python3 -m pip install -r requirements-production.txt
python3 start_asgi.py
```

This ASGI test fixture is strictly loopback-only. Stop the existing server first
so the same port is not occupied. The fixture is not Wordly.

For a future HTTPS environment, set `LX_ENV=production`, `LX_NO_SETUP=1` and
`LX_PUBLIC_URL=https://your-approved-origin.example`. A real guest gateway must
be configured and production Redis must be provided using `LX_REDIS_URL`
(`rediss://...`) and `LX_REDIS_PREFIX` (deployment-unique). The Redis adapter
is implemented but actual multi-replica scale is not yet verified. The example Dockerfile is a
**candidate**, not a certified production image.

## Known open engineering gates (do not mark done)

| Priority | Item | Definition of done |
|---|---|---|
| P0 | Shared guest grants and quotas | Redis-backed grant/discovery adapter is implemented; verify TLS Redis deployment, multi-worker/replica integration tests and shared rate/guest quotas at defined capacity. Production fails closed without shared Redis when a gateway is configured. |
| P0 | Browser dependency reproducibility | Lock and vendor/bundle ZXing and Tesseract incl worker data; no runtime CDN package load; scanner/OCR parity tests on devices. |
| P1 | Frontend modularization | Extract/normalize duplicated CSS and JS into shared audited modules, add JS unit/coverage gates and E2E visual + interaction diff against v75. Done only after parity. |
| P1 | Enforceable strict CSP | Resolve inline styles/inline handlers and third-party runtime sources, test camera/worker/wasm/image under CSP; current headers are partial and do not claim a strict CSP. |
| P1 | Production logging/metrics/limits | Request metrics, redacted security events, rate limiting across replicas, request cancellation and provider circuit breaking. Current audit is deliberately minimal. |
| P1 | Deterministic dependency and CI security gates | Transitive lock/hashes, actual Python/JS SCA, SAST run, historical secret scan, immutable third-party CI action SHAs and SBOM. CI starter is unverified until installed on actual repository. |
| P1 | Full backend module refactor | Separate the existing ~1k-line `run.py` provider functions from local HTTP, split domain services and add application factory. ASGI presently reuses those functions intentionally. |
| P1 | Deployment and capacity evidence | Real HTTPS edge/proxy, secret manager, persisted assets/cache strategy, staging load/fault tests, rollback, non-root image scan. |
| P2 | Brand and license approval | Rights register for app, airline marks, Wordly, fonts, icons and bundled dependencies. |
| P2 | Live service and physical device evidence | Contract tests against approved AV-ation gateway, actual Wordly/AES67 entitlement, iOS/Android QA and formal Exhibit C review; excluded from current engineering score. |

These are **not** cosmetic work: the current source cannot truthfully be called
fully production-ready or proven to scale merely because ASGI and a Redis adapter are available.
The present v76 release is a production-hardening increment while preserving
v75's approved passenger experience, not a claim that all P0/P1 gates closed.
