# Linguist-X v78 · Mobile app delivery tracker

**Scope: passenger mobile app only.** The right-side developer panel contains precisely 32 Exhibit C items (A01–A12, 12 Gold mobile areas, M AC 01–08), plus 10 mobile prototype/test-harness tasks. Fleet, remote support, commissioning, appliance/cloud-only requirements, overall milestone gates, and general delivery obligations belong to separately maintained trackers. Exhibit C obligations that rely on those systems remain here as **mobile dependencies**, not as tasks to implement their admin/appliance interfaces in this app.

The tracker stays outside the phone and is hidden on mobile. The Demo / Integration toggle remains in the desktop developer panel. Do not publish `index.html` to passengers: use `passenger-only.html` for a panel-free preview.

Data source: `requirements-progress.json` (embedded into `index.html` at `lxrtData`). To update: edit the ledger, add dated evidence and update `release`; run `python3 sync_progress.py`; validate UI and tests, then ship.

For Exhibit C A01–A12 and MG-01–MG-12, record **independent dimensions**:
- `interface`: `built`, `partial`, `not-started`, `not-applicable` (the mobile UI only; not the complete contractual obligation).
- `connection`: `adapter`, `connected`, `not-connected`, `not-applicable` (adapter ≠ real Wordly or AES67 service).
- `status`: `done`, `partial`, `pending`. `done` for a contractual requirement means the entire requirement has been verified with actual tests/evidence; all present contractual items remain open.
- `verified` must agree with `status == done`. M AC 01–08 are evidence-only acceptance cases; they intentionally do not have app UI and connection chips.

Prototype `UI-*` has separate `done/partial/pending` status; completing it does not check a contractual requirement. UI-09 is marked complete on the user’s explicit report of passing the six scanning validations; independent device logs remain separate evidence. UI-10 (fleet, commissioning, support, management, evidence wireframes) was removed from this *mobile* ledger, not deleted from source files. UI-11 is an internal mobile test harness, not a passenger feature.

A contract `done` requires dated build ID, device/test method, actual observed result, evidence location and defect/waiver where applicable. A mock service, design preview or integration adapter is never sufficient by itself. The panel is not AV-ation's written Final Acceptance.

**Source limitation:** The agreement's Exhibit A also references `Linguist-X_Integrated_Requirements_Alpha_Beta_Gold_v0.2.docx`, not separately supplied. Reconcile that document before treating this ledger as an exhaustive signed-baseline mapping.

## v74 signoffs and evidence discipline
- UI-09 was checked off on the user’s explicit report of passing all six scanning tests. Physical device logs have not been supplied; label remains user-reported.
- MG-07 was checked off on explicit user approval of the mobile in-app notices; fixture regression tests exercise state and fault labels. External provider media telemetry is not yet verified and is tracked under A07 / MG-06.
- All other contractual requirements remain open pending their complete required evidence; simulation is not formal acceptance.
- Any next-version change to status must update `requirements-progress.json` and run `python3 sync_progress.py`.

## v75 review record
Historical v75 record: the first Test 5 run failed because revoked/invalid/mismatched invitation states did not stop protected-access attempts. v75 code and automated regressions repaired that boundary. The user subsequently confirmed the Test 5 retest passed, which v77 records as 6/6 local fixture groups user-passed. Production authorization evidence remains separate. UI-09 and MG-07 retain their previously recorded signoffs. Never mark A04/A11/MG-05/M AC 02 verified solely from the local fixture.


## v77 documentation record
- User reported the corrected v75 Test 5 retest passed; all six local fixture test groups are therefore recorded `user-passed`.
- This does **not** automatically change the status of composite Exhibit C requirements; fixture evidence remains local integration evidence only.
- The checklist footer now links to `/developer-documentation.html`, an internal engineering handoff page.
- `developer-documentation.html` and `DEVELOPER_HANDOFF.md` must be updated whenever architecture, routes, configuration, guest/session semantics, caching policy, or release workflow changes.
- `index.html` remains internal development chrome. The passenger-only surface contains no visible documentation link.

## v78 splash record

v78 adds one intentional launch-presentation change only: a centered `Powered By` + Wordly wordmark holds for 2 seconds and then morphs into the existing Home footer attribution. This does not change contractual requirement completion, translation integration status, guest authorization, flight/scanner behavior, or the six user-passed local fixture groups.
