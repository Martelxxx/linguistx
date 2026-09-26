# Linguist-X Passenger v77 — QA results

## Release intent

v77 is a developer-handoff/documentation release built on v76. It intentionally does not redesign the passenger experience or add a passenger-facing feature. The only visible addition is inside the desktop-only internal checklist: a link to the engineering documentation page.

## Automated results

- `python3 -m unittest discover -s tests -v` — **37 tests passed**.
- `python3 quality/verify_v77.py` — **all release invariants passed**.
- `python3 -m compileall -q .` — **passed**.
- Extracted executable JavaScript blocks from `index.html` and `passenger-only.html` and ran `node --check` — **passed**.
- Core runtime documentation coverage: **90/90 Python classes/functions/methods have docstrings** across `run.py`, `integration_bridge.py`, `fixture_gateway.py`, `passenger_asgi.py`, `runtime_security.py`, `shared_guest_store.py`, `start.py`, `start_asgi.py`, and `app_logging.py`.

## Passenger preservation proof

`quality/verify_v77.py` removes only comments explicitly marked `DEVNOTE` from `passenger-only.html` and verifies that the remaining bytes hash to the exact approved v75/v76 passenger-only baseline:

`40e90476dfb165aff5fa274badb9349cc287e2242ed654ce2194beb56485ffe7`

This is stronger than a visual spot-check for this release: the new comments do not alter the passenger HTML/CSS/JavaScript once removed.

## Documentation-route smoke test

A local `python3 start.py` run on port 8877 returned:

- `/` → HTTP 200, HTML
- `/developer-documentation.html` → HTTP 200, HTML
- `/api/dev/fixture` → enabled, Healthy fixture

The ASGI regression suite separately verifies that `/developer-documentation.html` returns 404 when the runtime is configured as production.

## Manual test ledger

The mobile checklist records all six local fixture groups as **user-passed**, including the v75 Test 5 retest confirmed by the user. This remains local fixture evidence and does not establish live provider, native-device, scale, or contractual Final Acceptance.

## Tooling note

`ruff` was not installed in the artifact execution container used for this release, so it was not executed locally in this packaging pass. The repository CI remains configured to install the quality extras and run Ruff, Bandit, pip-audit, the regression suite, and `quality/verify_v77.py`.
