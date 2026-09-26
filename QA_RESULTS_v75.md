# Linguist-X v75 — Mobile-only QA and signoff record

**Recorded:** September 23, 2026. **Scope:** Passenger mobile preview and account-free integration test fixture; excludes fleet/support/commissioning. **Evidence level:** user-reported browser manual tests plus local deterministic adapter and HTTP tests. This is *not* production Wordly, AES67, native iOS/Android, independent penetration testing, or AV-ation written Final Acceptance.

## v74 user test results carried forward

| Test group | User reported result | v75 tracker treatment |
|---|---|---|
| 1. Healthy session | 5/5 checked, no findings | User-passed |
| 2. Language and flight changes | 5/5 checked, no findings | User-passed |
| 3. Connection recovery | 6/6 checked, no findings | User-passed |
| 4. Provider and session failures | 6/6 checked, no findings | User-passed |
| 5. Guest access and invitations | Revoked grant and invalid invitation still permitted ordinary navigation; cross-flight warning appeared but the journey continued | **Failed v74; v75 repaired programmatically; user re-test pending** |
| 6. Captions/accessibility/cleanup | 6/6 checked, no findings | User-passed |

The v74 Test 5 checkmarks did not prove authorization because the recorded observations contradicted their expected results. Test 5's *translation access* must be blocked; ordinary public flight pages are still navigable by design.

## Changes in v75

- The local fixture clears existing grants and denies future guest joins, state reads, and event reads while `revoke-guest` or `invalid-invite` is selected; joining resumes only after selecting Healthy fixture.
- The server checks both discovered flight and session ID against the resolved invitation, not merely a client-side flight mismatch warning.
- Failed replacement joins clear any previous server-side guest mapping and the HttpOnly cookie. An upstream guest-denied response evicts its local grant mapping.
- Live displays `ACCESS BLOCKED` and no fixture caption when access fails. It does not prevent using public app screens, and it never claims the fixture is live Wordly media.
- Six new gateway authorization tests and one end-to-end local HTTP test added. Existing tests unchanged.

## Automated checks

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests -v` | **18 tests passed** (including 7 new regression tests) |
| `python3 -m py_compile run.py start.py integration_bridge.py fixture_gateway.py sync_progress.py` | Passed |
| Node syntax checks for executable scripts in `index.html` and `passenger-only.html` | Passed |
| HTTP integration: guest join, invalid invite, revoke, flight mismatch, cookie deletion, recovery | Passed in subprocess test |
| Playwright live visual test | Could not execute: browser network navigation returned `ERR_BLOCKED_BY_ADMINISTRATOR` in this environment; **not counted as passed** |

## Checklist after v75

- Prototype: **10/10 done**, including UI-09 as previously user confirmed.
- Exhibit C: **1/32 done (MG-07, previous explicit user signoff); 15 partial; 16 pending**. No additional compound contractual item has enough real integration/physical evidence to mark verified.
- `requirements-progress.json` includes `testGroups`: 5 user-passed, 1 awaiting manual retest. The developer tracker displays this independently of the 32 contractual requirements.
- A03, A04, A06–A08, A11–A12, MG-01, MG-03–MG-07, MG-12 and M AC 02 evidence/notes were updated based on observed or tested behavior, **without incorrectly upgrading contractual completion**.

## Required next proof

Repeat **Test 5 only** from `TEST5_RETEST_v75.md` and share the actual outcomes, including any warnings/errors. Real invitations, production venue authorization, cross-tenant control, rate limits, live text/audio, iOS/Android and M AC acceptance remain outstanding.
