# Linguist-X Passenger v79 — Local provider key entry recovery

**Scope:** Restore private key setup disabled by the v78 launcher. No passenger-facing HTML/CSS/JS changed; approved Wordly splash unaffected.

## Root cause
`run.py` retained a hidden one-time optional provider-key entry path, but v78's `start.py` unconditionally set `LX_NO_SETUP=1`, so a fresh extracted folder silently lacked flight, weather, and voice keys. Provider-specific endpoints returned 503 before making upstream requests. The local `api_request_denied` audit entry does not reveal which endpoint failed or confirm a provider outage.

## Fix
`start.py` now invokes `local_service_setup.py` for missing keys, only in an interactive development Terminal. `python3 start.py --configure` explicitly replaces rotated keys. Entries are never echoed. `.env` is in the current package directory, Git ignored, atomically saved with owner-only permissions and never included in the archive. Other gateway settings are preserved; inherited environment keys are not copied to the file by the launcher. Direct `run.py` and production-style transport remain unaffected.

## Release checks
- [x] No live key or local `.env` included in package.
- [x] Unmodified v78 passenger-only and desktop HTML SHA-256.
- [x] v78 splash and broader regression suite passes.
- [x] Missing-key private setup, existing-key reuse, explicit rotation, env non-persistence, symlink refusal, non-TTY suppression, production prevention, 0600 file mode.
- [x] Current `/api/status` returns only configuration booleans; no secrets.
- [ ] Live provider connectivity with newly rotated customer keys: **not tested here**; requires the user's locally entered credentials, entitlement, quota and network conditions.
- [ ] Live Wordly media: still outside this fixture and not connected.

Use `python3 quality/verify_v79.py` for the packaging/visual regression invariants. Keep this release separate from contractual tracker signoff.
