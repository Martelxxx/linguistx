# v76 QA — execution and limitations

Source: v75 Guest Access Fix ZIP. All six manual test groups were user-reported
passed after the v75 Test 5 correction. Tests were not independently repeated
on physical devices for this release.

Run `python3 -m pytest -q`, `python3 -m unittest discover -s tests -v`,
`python3 quality/verify_v76.py`, and `python3 -m compileall -q .`.

Tests include v75's 18 original cases and v76's new config/TLS/cookie/preservation,
ASGI static/API, origin/size, revocation and a deterministic cross-instance Redis adapter test. No real Wordly or provider
media was delivered. SCA/SAST, strict CSP, distributed session tests, full
browser E2E and production-scale load tests are open gates.

## Verified in this build

- `python3 -m pytest -q`: **33 passed, 29 subtests passed**.
- The earlier 29-test suite was repeated three additional times successfully.
  The final 33-test suite also passed after adding cross-instance Redis tests.
- `python3 -m compileall -q .`: passed.
- `python3 quality/verify_v76.py`: exact v75 executable passenger shell
  preservation, no Aviationstack plaintext fallback, and fixture/production
  separation passed.
- Direct HTTP through a running Uvicorn ASGI process: fixture `200`, health
  `200`, passenger-only HTML `200`, mode `200`, discovery `200`, join `201`,
  labeled test caption delivered, revocation `200`, subsequent events `403`,
  subsequent join `403`.
- Deterministic two-instance Redis-protocol test: join on B after discovery on
  A, access on A, revocation visible on both; passed. This is a fake-client
  contract test, **not** a live Redis or load test.
- Automated Chromium screenshot comparison was attempted but the test browser
  blocked loopback navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`; **no visual
  screenshot-diff pass is claimed**. Unchanged source bytes outside the tracker
  are verified independently.
